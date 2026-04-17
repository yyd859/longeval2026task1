"""Trigger decisions for adaptive reindexing.

Reads collection analytics outputs and converts proxy monitoring signals into
weekly reindex trigger decisions. This module does not build or modify indexes.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYTICS_DIR = ROOT / "adaptive_monitor" / "outputs" / "collection_analytics"
DEFAULT_OUTPUT_DIR = ROOT / "adaptive_monitor" / "outputs" / "reindex_pipeline"


@dataclass(slots=True)
class TriggerThresholds:
    staleness_rate: float = 0.15
    coverage_gap: float = 0.05
    temporal_gap_growth_days: int = 30
    velocity_multiplier: float = 2.0
    rank_stability_drop: float = 0.20
    rank_stability_periods: int = 3
    baseline_weeks: int = 4


@dataclass(slots=True)
class TriggerDecision:
    week_start: str
    cutoff_date: str
    trigger_level: int
    action: str
    reason: str
    new_docs_since_reindex: int
    indexed_docs_at_reindex: int
    index_coverage_gap: float
    weekly_new_docs: int
    velocity_per_day: float
    baseline_velocity_per_day: float
    staleness_rate: float
    temporal_gap_days: int
    temporal_gap_growth_days: int
    rank_stability_drop: float | None = None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required analytics file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _rank_stability_by_week(path: Path | None) -> dict[str, float]:
    if path is None or not path.exists():
        return {}
    rows = _read_csv(path)
    values = {}
    for row in rows:
        week = row.get("week_start") or row.get("cutoff_date")
        if not week:
            continue
        values[week] = _as_float(row.get("rank_stability_drop"))
    return values


def compute_trigger_decisions(
    analytics_dir: Path = DEFAULT_ANALYTICS_DIR,
    *,
    thresholds: TriggerThresholds | None = None,
    last_reindex_week: str | None = None,
    rank_stability_path: Path | None = None,
) -> list[TriggerDecision]:
    thresholds = thresholds or TriggerThresholds()
    weekly_rows = _read_csv(analytics_dir / "weekly_doc_counts.csv")
    staleness_rows = _read_csv(analytics_dir / "staleness_rate.csv")
    gap_rows = _read_csv(analytics_dir / "temporal_gap.csv")

    if not weekly_rows:
        return []

    staleness_by_week = {row["week_start"]: row for row in staleness_rows}
    gap_by_week = {row["week_start"]: row for row in gap_rows}
    rank_drop_by_week = _rank_stability_by_week(rank_stability_path)

    reindex_row = None
    if last_reindex_week:
        reindex_row = next((row for row in weekly_rows if row["week_start"] <= last_reindex_week), None)
    if reindex_row is None:
        reindex_row = weekly_rows[0]

    indexed_docs_at_reindex = max(_as_int(reindex_row.get("cumulative_docs")), 1)
    base_gap_row = gap_by_week.get(reindex_row["week_start"], {})
    baseline_temporal_gap = _as_int(base_gap_row.get("temporal_gap_days"))

    baseline_window = weekly_rows[: max(thresholds.baseline_weeks, 1)]
    baseline_velocity = sum(_as_int(row.get("new_docs")) / 7.0 for row in baseline_window) / len(baseline_window)

    recent_rank_drops: list[bool] = []
    decisions: list[TriggerDecision] = []
    for row in weekly_rows:
        week = row["week_start"]
        weekly_new_docs = _as_int(row.get("new_docs"))
        cumulative_docs = _as_int(row.get("cumulative_docs"))
        new_docs_since_reindex = max(cumulative_docs - indexed_docs_at_reindex, 0)
        coverage_gap = new_docs_since_reindex / indexed_docs_at_reindex
        velocity = weekly_new_docs / 7.0

        staleness = _as_float(staleness_by_week.get(week, {}).get("staleness_rate"))
        gap_row = gap_by_week.get(week, {})
        temporal_gap = _as_int(gap_row.get("temporal_gap_days"))
        temporal_gap_growth = temporal_gap - baseline_temporal_gap
        cutoff_date = gap_row.get("cutoff_date") or staleness_by_week.get(week, {}).get("cutoff_date") or week

        rank_drop = rank_drop_by_week.get(week)
        if rank_drop is not None:
            recent_rank_drops.append(rank_drop > thresholds.rank_stability_drop)
            recent_rank_drops = recent_rank_drops[-thresholds.rank_stability_periods :]
        sustained_rank_drop = (
            len(recent_rank_drops) == thresholds.rank_stability_periods and all(recent_rank_drops)
        )

        reasons = []
        trigger_level = 0
        action = "none"

        if staleness > thresholds.staleness_rate and coverage_gap > thresholds.coverage_gap:
            trigger_level = 1
            action = "soft_alert"
            reasons.append(
                f"staleness_rate={staleness:.4f}>{thresholds.staleness_rate:.4f} "
                f"and coverage_gap={coverage_gap:.4f}>{thresholds.coverage_gap:.4f}"
            )

        if temporal_gap_growth > thresholds.temporal_gap_growth_days:
            trigger_level = max(trigger_level, 2)
            action = "incremental_reindex"
            reasons.append(
                f"temporal_gap_growth_days={temporal_gap_growth}>{thresholds.temporal_gap_growth_days}"
            )
        if baseline_velocity > 0 and velocity > thresholds.velocity_multiplier * baseline_velocity:
            trigger_level = max(trigger_level, 2)
            action = "incremental_reindex"
            reasons.append(
                f"velocity_per_day={velocity:.2f}>{thresholds.velocity_multiplier:.2f}x "
                f"baseline={baseline_velocity:.2f}"
            )

        if sustained_rank_drop:
            trigger_level = 3
            action = "full_rebuild"
            reasons.append(
                f"rank_stability_drop>{thresholds.rank_stability_drop:.4f} for "
                f"{thresholds.rank_stability_periods} periods"
            )

        decisions.append(
            TriggerDecision(
                week_start=week,
                cutoff_date=str(cutoff_date),
                trigger_level=trigger_level,
                action=action,
                reason="; ".join(reasons) if reasons else "within_thresholds",
                new_docs_since_reindex=new_docs_since_reindex,
                indexed_docs_at_reindex=indexed_docs_at_reindex,
                index_coverage_gap=round(coverage_gap, 6),
                weekly_new_docs=weekly_new_docs,
                velocity_per_day=round(velocity, 3),
                baseline_velocity_per_day=round(baseline_velocity, 3),
                staleness_rate=round(staleness, 6),
                temporal_gap_days=temporal_gap,
                temporal_gap_growth_days=temporal_gap_growth,
                rank_stability_drop=rank_drop,
            )
        )

    return decisions


def write_trigger_decisions(decisions: list[TriggerDecision], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(decision) for decision in decisions]
    csv_path = output_dir / "trigger_decisions.csv"
    json_path = output_dir / "trigger_decisions.json"
    _write_csv(rows, csv_path)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return csv_path, json_path


def latest_actionable_decision(decisions: list[TriggerDecision]) -> TriggerDecision | None:
    actionable = [decision for decision in decisions if decision.trigger_level > 0]
    return actionable[-1] if actionable else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute adaptive reindex trigger decisions.")
    parser.add_argument("--analytics-dir", default=str(DEFAULT_ANALYTICS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--last-reindex-week", default=None)
    parser.add_argument("--rank-stability", default=None, help="Optional CSV with week_start,rank_stability_drop.")
    parser.add_argument("--staleness-rate", type=float, default=0.15)
    parser.add_argument("--coverage-gap", type=float, default=0.05)
    parser.add_argument("--temporal-gap-growth-days", type=int, default=30)
    parser.add_argument("--velocity-multiplier", type=float, default=2.0)
    parser.add_argument("--baseline-weeks", type=int, default=4)
    args = parser.parse_args()

    thresholds = TriggerThresholds(
        staleness_rate=args.staleness_rate,
        coverage_gap=args.coverage_gap,
        temporal_gap_growth_days=args.temporal_gap_growth_days,
        velocity_multiplier=args.velocity_multiplier,
        baseline_weeks=args.baseline_weeks,
    )
    decisions = compute_trigger_decisions(
        Path(args.analytics_dir),
        thresholds=thresholds,
        last_reindex_week=args.last_reindex_week,
        rank_stability_path=Path(args.rank_stability) if args.rank_stability else None,
    )
    csv_path, json_path = write_trigger_decisions(decisions, Path(args.output_dir))
    print(f"Wrote {len(decisions)} trigger decisions")
    print(f"  {csv_path}")
    print(f"  {json_path}")
    latest = latest_actionable_decision(decisions)
    if latest is None:
        print("Latest actionable decision: none")
    else:
        print(
            f"Latest actionable decision: level={latest.trigger_level} "
            f"action={latest.action} week={latest.week_start} reason={latest.reason}"
        )


if __name__ == "__main__":
    main()
