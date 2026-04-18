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
    """
    Parse an ISO 8601 timestamp into a timezone-aware UTC datetime.
    
    Parameters:
        value (object): The input to parse (typically an ISO 8601 string). Falsy values return `None`.
    
    Returns:
        datetime | None: A `datetime` object normalized to UTC if parsing succeeds, `None` if the input is falsy or cannot be parsed.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_cutoff_date(value: str) -> datetime:
    """
    Parse an ISO 8601 date string, normalize it to UTC, and return the timestamp at the end of that day (23:59:59).
    
    Parameters:
        value (str): ISO 8601 date or datetime string (e.g., "2025-03-31" or "2025-03-31T12:34:56Z").
    
    Returns:
        datetime: The parsed datetime in UTC with time set to 23:59:59.
    
    Raises:
        ValueError: If `value` is not a valid ISO 8601 datetime string.
    """
    parsed = datetime.fromisoformat(value)
    parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    return parsed.replace(hour=23, minute=59, second=59)


def _read_trigger_decisions(path: Path) -> list[dict[str, str]]:
    """
    Load trigger decision rows from a CSV file.
    
    Parameters:
        path (Path): Path to a CSV file containing trigger decision records.
    
    Returns:
        list[dict[str, str]]: A list of rows where each row is a dictionary mapping CSV column names to string values.
    
    Raises:
        FileNotFoundError: If the provided path does not exist.
    """
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
    """
    Builds an ordered list of IndexVersion records from a trigger-decisions CSV and a baseline cutoff.
    
    Parses trigger decision rows from the provided CSV and produces a sequence that always starts with the baseline "March" index and then includes subsequent index versions whose cutoffs pass the configured filters. Cutoff rows are included only if they occur after `baseline_cutoff`, meet the configured trigger-level filtering (optionally including soft alerts), and respect the `window_end` rules (optionally including at most the first cutoff after the window). Each returned IndexVersion carries its cutoff date and the previous included cutoff date to allow constructing membership ranges.
    
    Parameters:
        trigger_decisions_path (Path): Path to the CSV file containing trigger decision rows.
        baseline_cutoff (datetime): Baseline cutoff datetime used to create the initial "march_baseline" version.
        window_end (datetime): Inclusive window end; cutoffs after this are only included according to `include_next_after_window`.
        include_soft_alerts (bool): If true, include trigger rows with trigger_level == 1 in addition to level >= 2.
        include_next_after_window (bool): If true, allow including the first cutoff that occurs after `window_end`; otherwise exclude all after-window cutoffs.
    
    Returns:
        list[IndexVersion]: Ordered list of IndexVersion objects starting with the baseline and followed by selected cutoffs in chronological order.
    """
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
    """
    Builds document-to-index membership rows for documents with published dates on or before window_end.
    
    Parameters:
        versions (list[IndexVersion]): Ordered index versions whose `cutoff_date` values are used to determine the first index that would contain a document.
        window_end (datetime): Inclusive upper bound for document `publishedDate`; documents with `publishedDate` after this are ignored.
    
    Returns:
        list[dict[str, object]]: Sorted list of rows where each row contains:
            - "doc_id": document identifier (str)
            - "publishedDate": document published timestamp in ISO 8601 (str)
            - "first_index_id": id of the first index version that includes the document (str)
            - "first_index_cutoff_date": cutoff date of that index version (str)
            - "first_index_kind": index kind, e.g., "baseline", "incremental", or "full" (str)
            - "first_index_action": action associated with that index version (str)
            - "is_in_march_baseline": `true` if `publishedDate` is on or before the March baseline cutoff, `false` otherwise (bool)
            - "days_after_march_cutoff": non-negative integer days between `publishedDate` and the March baseline cutoff (int)
    """
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
    """
    Write a list of mapping rows to a CSV file at the given path, creating parent directories as needed.
    
    Parameters:
        rows (list[dict[str, object]]): Sequence of dictionaries representing CSV rows. Column order and header are taken from the keys of the first dictionary in the list.
        path (Path): Filesystem path to write the CSV file. Parent directories will be created if they do not exist.
    
    Behavior:
        - If `rows` is empty, creates an empty UTF-8 file at `path`.
        - Otherwise writes a UTF-8 CSV using the keys of `rows[0]` as the header and writes all rows in order.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """
    Builds index-version and document-to-index membership tables from trigger decisions and dataset snapshot, writes CSV/JSON outputs to the specified directory, and prints summary counts and output paths.
    
    This command-line entrypoint parses arguments (--trigger-decisions, --output-dir, --include-soft-alerts, --no-next-after-window, --window-end), constructs ordered index versions using the provided trigger decisions and baseline March cutoff, assigns each dataset document to the first index whose cutoff is on or after the document's publishedDate (excluding documents after the window end), and emits three files into the output directory: index_versions.csv, doc_index_membership.csv, and index_versions.json. It prints the number of index versions and document membership rows written and the paths of the CSV outputs.
    """
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
