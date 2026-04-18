"""Collection-level temporal analytics for snapshot-1-train.

Computes monitoring metrics from document metadata only — no run.txt needed.

Outputs:
  - daily new doc count and cumulative doc count
  - new doc velocity (7-day rolling average)
  - doc date distribution by week
  - estimated Temporal Gap (query time - mean doc publishedDate)

Usage:
    python adaptive_monitor/collection_analytics.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval
from longeval_sci.config import load_config
from longeval_sci.io.dataset import load_dataset_bundle

CONFIG_PATH = ROOT / "configs" / "custom_lexical_fulltext.yaml"
SNAPSHOT_ID = "snapshot-1"
DATE_FIELD = "publishedDate"
SNAPSHOT_CUTOFF = datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)
OUTPUT_DIR = ROOT / "adaptive_monitor" / "outputs" / "collection_analytics"


def _parse_dt(value: object) -> datetime | None:
    """
    Parse a value into a timezone-aware UTC datetime if possible.
    
    Parameters:
        value (object): An ISO-8601 datetime string (the function accepts values convertible to string, including strings that end with 'Z') or any object whose string form is an ISO datetime.
    
    Returns:
        datetime | None: A `datetime` normalized to UTC if parsing succeeds; `None` if `value` is falsy or cannot be parsed. Timezone-naive datetimes are treated as UTC.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _week_label(dt: datetime) -> str:
    """
    Return the date string for the Monday (week start) of the week containing the given datetime.
    
    Parameters:
        dt (datetime): Input datetime used to determine the week.
    
    Returns:
        week_start (str): Monday of dt's week formatted as "YYYY-MM-DD".
    """
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def run_analytics() -> None:
    """
    Compute collection-level temporal monitoring metrics from document metadata and write analytics files to OUTPUT_DIR.
    
    Processes the configured dataset snapshot by parsing each document's published date (DATE_FIELD), aggregating counts by day and by ISO-week-start Monday, and producing the following output files in OUTPUT_DIR:
    - daily_doc_counts.csv: per-day rows with `date`, `new_docs`, `cumulative_docs`, and `velocity_7d_avg` (7-day rolling average).
    - weekly_doc_counts.csv: per-week rows with `week_start`, `new_docs`, and `cumulative_docs`.
    - staleness_rate.csv: per-week staleness at the week cutoff (`week_start` + 6 days) with `cutoff_date`, `total_docs`, `stale_docs`, and `staleness_rate` (fraction older than 90 days).
    - temporal_gap.csv: per-week temporal gap rows with `mean_doc_date` and `temporal_gap_days` computed as (SNAPSHOT_CUTOFF - mean_doc_date).
    - summary.json: overall statistics including earliest/latest/mean dates, document counts with/without dates, date span, mean temporal gap, staleness threshold, and final staleness rate.
    
    Documents with missing or unparseable dates are counted and skipped; a brief human-readable summary and a per-week table are printed to stdout.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading dataset bundle ...")
    config = clone_for_train_eval(load_config(str(CONFIG_PATH)))
    bundle = load_dataset_bundle(config.dataset, SNAPSHOT_ID)
    print(f"  Total documents: {len(bundle.documents):,}")

    # --- collect per-document date info ---
    daily_counts: dict[str, int] = defaultdict(int)
    weekly_counts: dict[str, int] = defaultdict(int)
    no_date_count = 0
    all_dates: list[datetime] = []

    for doc in bundle.documents:
        dt = _parse_dt(doc.metadata.get(DATE_FIELD))
        if dt is None:
            no_date_count += 1
            continue
        day_key = dt.strftime("%Y-%m-%d")
        daily_counts[day_key] += 1
        weekly_counts[_week_label(dt)] += 1
        all_dates.append(dt)

    print(f"  Documents with {DATE_FIELD}: {len(all_dates):,}")
    print(f"  Documents without date: {no_date_count:,}")

    if not all_dates:
        print("No date information found — cannot proceed.")
        return

    # --- daily & cumulative doc counts ---
    sorted_days = sorted(daily_counts.keys())
    cumulative = 0
    daily_rows = []
    for day in sorted_days:
        cumulative += daily_counts[day]
        daily_rows.append({
            "date": day,
            "new_docs": daily_counts[day],
            "cumulative_docs": cumulative,
        })

    # 7-day rolling velocity
    window = 7
    for i, row in enumerate(daily_rows):
        window_new = sum(daily_rows[j]["new_docs"] for j in range(max(0, i - window + 1), i + 1))
        row["velocity_7d_avg"] = round(window_new / min(i + 1, window), 1)

    _write_csv(daily_rows, OUTPUT_DIR / "daily_doc_counts.csv")
    print(f"  Written: daily_doc_counts.csv ({len(daily_rows)} days)")

    # --- weekly summary ---
    sorted_weeks = sorted(weekly_counts.keys())
    weekly_rows = []
    cumulative = 0
    for week in sorted_weeks:
        cumulative += weekly_counts[week]
        weekly_rows.append({
            "week_start": week,
            "new_docs": weekly_counts[week],
            "cumulative_docs": cumulative,
        })
    _write_csv(weekly_rows, OUTPUT_DIR / "weekly_doc_counts.csv")
    print(f"  Written: weekly_doc_counts.csv ({len(weekly_rows)} weeks)")

    # --- staleness rate at each weekly cutoff ---
    # Doc Staleness Rate = fraction of docs older than 90 days at each cutoff
    staleness_threshold_days = 90
    staleness_rows = []
    for week_row in weekly_rows:
        cutoff = datetime.fromisoformat(week_row["week_start"]).replace(tzinfo=UTC) + timedelta(days=6)
        docs_in_window = [dt for dt in all_dates if dt <= cutoff]
        if not docs_in_window:
            continue
        stale = sum(1 for dt in docs_in_window if (cutoff - dt).days > staleness_threshold_days)
        staleness_rows.append({
            "week_start": week_row["week_start"],
            "cutoff_date": cutoff.strftime("%Y-%m-%d"),
            "total_docs": len(docs_in_window),
            "stale_docs": stale,
            "staleness_rate": round(stale / len(docs_in_window), 4),
        })
    _write_csv(staleness_rows, OUTPUT_DIR / "staleness_rate.csv")
    print(f"  Written: staleness_rate.csv")

    # --- temporal gap: snapshot cutoff - mean doc date ---
    gap_rows = []
    for week_row in weekly_rows:
        cutoff = datetime.fromisoformat(week_row["week_start"]).replace(tzinfo=UTC) + timedelta(days=6)
        docs_in_window = [dt for dt in all_dates if dt <= cutoff]
        if not docs_in_window:
            continue
        mean_doc_ts = sum(dt.timestamp() for dt in docs_in_window) / len(docs_in_window)
        mean_doc_dt = datetime.fromtimestamp(mean_doc_ts, tz=UTC)
        gap_days = (SNAPSHOT_CUTOFF - mean_doc_dt).days
        gap_rows.append({
            "week_start": week_row["week_start"],
            "cutoff_date": cutoff.strftime("%Y-%m-%d"),
            "mean_doc_date": mean_doc_dt.strftime("%Y-%m-%d"),
            "temporal_gap_days": gap_days,
        })
    _write_csv(gap_rows, OUTPUT_DIR / "temporal_gap.csv")
    print(f"  Written: temporal_gap.csv")

    # --- summary stats ---
    min_date = min(all_dates)
    max_date = max(all_dates)
    mean_ts = sum(dt.timestamp() for dt in all_dates) / len(all_dates)
    mean_date = datetime.fromtimestamp(mean_ts, tz=UTC)

    summary = {
        "total_documents": len(bundle.documents),
        "documents_with_date": len(all_dates),
        "documents_without_date": no_date_count,
        "earliest_date": min_date.strftime("%Y-%m-%d"),
        "latest_date": max_date.strftime("%Y-%m-%d"),
        "mean_date": mean_date.strftime("%Y-%m-%d"),
        "date_span_days": (max_date - min_date).days,
        "snapshot_cutoff": SNAPSHOT_CUTOFF.strftime("%Y-%m-%d"),
        "mean_temporal_gap_days": (SNAPSHOT_CUTOFF - mean_date).days,
        "staleness_threshold_days": staleness_threshold_days,
        "final_staleness_rate": staleness_rows[-1]["staleness_rate"] if staleness_rows else None,
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # --- print summary table ---
    print("\n=== Collection Analytics Summary ===")
    print(f"  Date range:       {summary['earliest_date']}  to  {summary['latest_date']}")
    print(f"  Mean doc date:    {summary['mean_date']}")
    print(f"  Temporal gap:     {summary['mean_temporal_gap_days']} days (snapshot cutoff vs mean doc date)")
    print(f"  Final staleness:  {summary['final_staleness_rate']:.1%} of docs older than {staleness_threshold_days} days at cutoff")
    print()
    print(f"{'Week':12} {'New Docs':>10} {'Cumulative':>12} {'Velocity 7d':>12} {'Staleness':>10}")
    print("-" * 62)
    for wrow, srow, drow_7d in _zip_rows(weekly_rows, staleness_rows, daily_rows, window=7):
        print(
            f"{wrow['week_start']:12} {wrow['new_docs']:>10,} {wrow['cumulative_docs']:>12,} "
            f"{drow_7d:>12.1f} {srow['staleness_rate']:>10.1%}"
        )


def _zip_rows(weekly_rows, staleness_rows, daily_rows, window):
    """
    Align weekly analytics rows with their corresponding staleness rows and compute a per-week average daily velocity from daily counts.
    
    Parameters:
        weekly_rows (Iterable[dict]): Weekly summary rows containing at least a `"week_start"` key with ISO date string for the week's Monday.
        staleness_rows (Iterable[dict]): Staleness summary rows containing at least `"week_start"` and `"staleness_rate"`.
        daily_rows (Iterable[dict]): Daily summary rows containing at least `"date"` (YYYY-MM-DD) and `"new_docs"`.
        window (int): Unused by this implementation; velocity is computed as the average `new_docs` per day across the 7 days of the week.
    
    Returns:
        Iterator[tuple[dict, dict, float]]: Yields tuples of `(weekly_row, staleness_row, velocity)` where `velocity` is the average number of new documents per day for that week (float).
    """
    staleness_by_week = {r["week_start"]: r for r in staleness_rows}
    # compute weekly velocity from daily data
    daily_by_date = {r["date"]: r for r in daily_rows}
    for wrow in weekly_rows:
        srow = staleness_by_week.get(wrow["week_start"], {"staleness_rate": 0.0})
        week_start = datetime.fromisoformat(wrow["week_start"])
        week_days = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        week_new = sum(daily_by_date.get(d, {}).get("new_docs", 0) for d in week_days)
        yield wrow, srow, week_new / 7


def _write_csv(rows: list[dict], path: Path) -> None:
    """
    Write a list of dictionary rows to a CSV file when rows are present.
    
    If `rows` is empty the function does nothing. The CSV header and column order are taken from the key order of the first row. The file is written using UTF-8 encoding and standard newline handling.
    
    Parameters:
        rows (list[dict]): Sequence of rows where each row is a mapping of column name to value. All rows should share the same keys.
        path (Path): Destination filesystem path for the CSV file.
    """
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run_analytics()
