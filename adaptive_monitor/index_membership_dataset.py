"""Build document-to-index membership tables for BM25 fulltext reindex simulations.

The table answers: for a chosen reindex schedule, when does each document first
become searchable, and which logical index version contains it?

Default schedule:
    - March baseline index: publishedDate <= 2025-03-31
    - Weekly adaptive reindex cutoffs from trigger_decisions.csv during Apr-May

Usage:
    python adaptive_monitor/index_membership_dataset.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval  # noqa: E402
from longeval_sci.config import load_config  # noqa: E402
from longeval_sci.io.dataset import load_dataset_bundle  # noqa: E402


CONFIG_PATH = ROOT / "configs" / "custom_lexical_fulltext.yaml"
SNAPSHOT_ID = "snapshot-1"
DATE_FIELD = "publishedDate"
MARCH_CUTOFF = datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC)
WINDOW_END = datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)
DEFAULT_TRIGGER_DECISIONS = ROOT / "adaptive_monitor" / "outputs" / "reindex_pipeline" / "trigger_decisions.csv"
DEFAULT_OUTPUT_DIR = ROOT / "adaptive_monitor" / "outputs" / "index_membership"


@dataclass(slots=True)
class IndexVersion:
    index_id: str
    index_kind: str
    cutoff_date: str
    previous_cutoff_date: str
    action: str
    trigger_level: int
    reason: str


def _parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_cutoff_date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return parsed.replace(hour=23, minute=59, second=59)


def _read_trigger_decisions(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Trigger decisions not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_index_versions(
    trigger_decisions_path: Path,
    *,
    baseline_cutoff: datetime,
    window_end: datetime,
    include_soft_alerts: bool,
    include_next_after_window: bool,
) -> list[IndexVersion]:
    versions = [
        IndexVersion(
            index_id=f"idx_{baseline_cutoff:%Y%m%d}_march_baseline",
            index_kind="baseline",
            cutoff_date=baseline_cutoff.date().isoformat(),
            previous_cutoff_date="",
            action="march_baseline",
            trigger_level=0,
            reason="publishedDate <= March cutoff",
        )
    ]

    previous_cutoff = baseline_cutoff
    added_after_window = False
    for row in _read_trigger_decisions(trigger_decisions_path):
        cutoff_text = row.get("cutoff_date") or ""
        if not cutoff_text:
            continue
        cutoff = _parse_cutoff_date(cutoff_text)
        if cutoff <= baseline_cutoff:
            continue
        trigger_level = int(float(row.get("trigger_level") or 0))
        action = row.get("action") or "none"
        if trigger_level < 2 and not (include_soft_alerts and trigger_level == 1):
            continue
        if cutoff > window_end:
            if not include_next_after_window or added_after_window:
                continue
            added_after_window = True
        versions.append(
            IndexVersion(
                index_id=f"idx_{cutoff:%Y%m%d}_{action}",
                index_kind="incremental" if action == "incremental_reindex" else "full",
                cutoff_date=cutoff.date().isoformat(),
                previous_cutoff_date=previous_cutoff.date().isoformat(),
                action=action,
                trigger_level=trigger_level,
                reason=row.get("reason") or "",
            )
        )
        previous_cutoff = cutoff
        if added_after_window:
            break
    return versions


def _document_rows(versions: list[IndexVersion], *, window_end: datetime) -> list[dict[str, object]]:
    config = clone_for_train_eval(load_config(str(CONFIG_PATH)))
    bundle = load_dataset_bundle(config.dataset, SNAPSHOT_ID)
    cutoffs = [(_parse_cutoff_date(version.cutoff_date), version) for version in versions]

    rows: list[dict[str, object]] = []
    for doc in bundle.documents:
        published_at = _parse_dt(doc.metadata.get(DATE_FIELD))
        if published_at is None or published_at > window_end:
            continue

        first_version = None
        for cutoff, version in cutoffs:
            if published_at <= cutoff:
                first_version = version
                break
        if first_version is None:
            continue

        rows.append(
            {
                "doc_id": doc.doc_id,
                "publishedDate": published_at.isoformat(),
                "first_index_id": first_version.index_id,
                "first_index_cutoff_date": first_version.cutoff_date,
                "first_index_kind": first_version.index_kind,
                "first_index_action": first_version.action,
                "is_in_march_baseline": published_at <= MARCH_CUTOFF,
                "days_after_march_cutoff": max((published_at.date() - MARCH_CUTOFF.date()).days, 0),
            }
        )
    rows.sort(key=lambda row: (str(row["publishedDate"]), str(row["doc_id"])))
    return rows


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build doc-to-index membership tables.")
    parser.add_argument("--trigger-decisions", default=str(DEFAULT_TRIGGER_DECISIONS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--include-soft-alerts", action="store_true")
    parser.add_argument(
        "--no-next-after-window",
        action="store_true",
        help="Do not include the first reindex cutoff after --window-end.",
    )
    parser.add_argument("--window-end", default=WINDOW_END.date().isoformat())
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    window_end = _parse_cutoff_date(args.window_end)
    versions = build_index_versions(
        Path(args.trigger_decisions),
        baseline_cutoff=MARCH_CUTOFF,
        window_end=window_end,
        include_soft_alerts=args.include_soft_alerts,
        include_next_after_window=not args.no_next_after_window,
    )
    doc_rows = _document_rows(versions, window_end=window_end)

    version_rows = [asdict(version) for version in versions]
    _write_csv(version_rows, output_dir / "index_versions.csv")
    _write_csv(doc_rows, output_dir / "doc_index_membership.csv")
    (output_dir / "index_versions.json").write_text(json.dumps(version_rows, indent=2), encoding="utf-8")

    print(f"Wrote {len(version_rows):,} index versions")
    print(f"Wrote {len(doc_rows):,} document membership rows")
    print(f"  {output_dir / 'index_versions.csv'}")
    print(f"  {output_dir / 'doc_index_membership.csv'}")


if __name__ == "__main__":
    main()
