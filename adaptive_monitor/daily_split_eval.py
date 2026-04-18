"""Daily-granularity evaluation for custom_lexical_fulltext on snapshot-1-train.

Reuses existing run.txt and qrels — no retrieval re-run needed.
Produces nDCG@10, MAP, Recall@100, Recall@1000 for each cumulative daily window.

Usage:
    python adaptive_monitor/daily_split_eval.py \
        --run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt \
        --step-days 7
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval
from longeval_sci.config import load_config
from longeval_sci.evaluation.pytrec_eval_wrapper import evaluate_run_dict
from longeval_sci.io.dataset import load_dataset_bundle
from longeval_sci.io.trec import read_trec_run

METRICS = ["ndcg_cut_10", "ndcg_cut_1000", "map", "recall_100", "recall_1000"]
CONFIG_PATH = ROOT / "configs" / "custom_lexical_fulltext.yaml"
SNAPSHOT_ID = "snapshot-1"
DATE_FIELD = "publishedDate"

# snapshot-1 training window (march–may 2025)
WINDOW_START = datetime(2025, 3, 1, tzinfo=UTC)
WINDOW_END = datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)


def _parse_dt(value: object) -> datetime | None:
    """
    Parse a value into a timezone-aware UTC datetime if it represents an ISO-format timestamp.
    
    Parameters:
        value (object): A value representing a date/time (commonly an ISO-formatted string or datetime). Falsy values return None.
    
    Returns:
        datetime | None: A `datetime` object with UTC tzinfo when parsing succeeds, or `None` if `value` is falsy or not a valid ISO datetime.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _doc_ids_up_to(bundle, cutoff: datetime, date_field: str) -> set[str]:
    """
    Collects document IDs from the bundle whose specified metadata date is on or before the cutoff.
    
    Parameters:
        bundle: An object with a `documents` iterable; each document must expose `metadata` (a mapping) and `doc_id`.
        cutoff (datetime): Cutoff datetime; documents with parsed metadata datetime less than or equal to this are included.
        date_field (str): Metadata key containing the date string to parse (passed to `_parse_dt`).
    
    Returns:
        set[str]: Set of document IDs whose parsed `date_field` value is less than or equal to `cutoff`.
    """
    allowed: set[str] = set()
    for doc in bundle.documents:
        dt = _parse_dt(doc.metadata.get(date_field))
        if dt is not None and dt <= cutoff:
            allowed.add(doc.doc_id)
    return allowed


def _filter_qrels(qrels, allowed_doc_ids: set[str], min_qrels: int = 1):
    """
    Filter qrels to only include judgments for documents present in `allowed_doc_ids` and drop queries with fewer than `min_qrels` remaining.
    
    Parameters:
        qrels (dict): Mapping from query id to a dict of document id -> relevance judgment.
        allowed_doc_ids (set[str]): Set of document ids that are permitted to remain in the qrels.
        min_qrels (int): Minimum number of judgments required for a query to be kept.
    
    Returns:
        dict: A filtered qrels mapping where each query maps to a dict of kept document id -> relevance, and only queries with at least `min_qrels` judgments are included.
    """
    filtered = {}
    for qid, docrels in qrels.items():
        kept = {d: r for d, r in docrels.items() if d in allowed_doc_ids}
        if len(kept) >= min_qrels:
            filtered[qid] = kept
    return filtered


def _filter_run(run, allowed_doc_ids: set[str], allowed_qids: set[str]):
    """
    Return a new run dictionary restricted to the provided query IDs and document IDs.
    
    Parameters:
        run (dict): Mapping from query id to a mapping of doc id -> score.
        allowed_doc_ids (set[str]): Document IDs permitted in the filtered run.
        allowed_qids (set[str]): Query IDs to retain in the filtered run.
    
    Returns:
        dict: Filtered run where each returned query id is in `allowed_qids` and its document map contains only doc ids present in `allowed_doc_ids`. Queries in `allowed_qids` with no remaining documents are included with an empty mapping.
    """
    filtered = {}
    for qid, docs in run.items():
        if qid not in allowed_qids:
            continue
        filtered[qid] = {d: s for d, s in docs.items() if d in allowed_doc_ids}
    return filtered


def evaluate_daily_splits(run_path: Path, step_days: int = 7) -> list[dict]:
    """
    Evaluate retrieval metrics over cumulative daily time windows for a TREC run.
    
    For each cutoff date between the configured WINDOW_START and WINDOW_END (stepping by
    `step_days`), this function restricts documents and qrels to those with `publishedDate`
    on or before the cutoff, filters the provided TREC run accordingly, and computes the
    aggregated metrics defined by `METRICS`.
    
    Parameters:
        run_path (Path): Path to the TREC-format run file to evaluate.
        step_days (int): Number of days between consecutive cutoff windows (default: 7).
    
    Returns:
        list[dict]: A list of per-window result records. Each record contains:
            - cutoff_date (str): Cutoff date as YYYY-MM-DD.
            - days_since_start (int): Days from WINDOW_START to the cutoff, inclusive.
            - doc_count (int): Number of documents allowed up to the cutoff.
            - query_count (int): Number of queries remaining after qrel filtering.
            - nDCG@10, nDCG@1000, MAP, Recall@100, Recall@1000 (float): Aggregated metrics
              rounded to 4 decimal places (names correspond to entries in `METRICS`).
    
    Raises:
        RuntimeError: If the dataset bundle contains no qrels for the configured snapshot.
    """
    config = clone_for_train_eval(load_config(str(CONFIG_PATH)))
    bundle = load_dataset_bundle(config.dataset, SNAPSHOT_ID)

    if bundle.qrels is None:
        raise RuntimeError("No qrels found for snapshot-1-train.")

    run = read_trec_run(run_path)

    results = []
    cutoff = WINDOW_START + timedelta(days=step_days - 1)
    while cutoff <= WINDOW_END:
        allowed_docs = _doc_ids_up_to(bundle, cutoff, DATE_FIELD)
        filtered_qrels = _filter_qrels(bundle.qrels, allowed_docs)
        filtered_run = _filter_run(run, allowed_docs, set(filtered_qrels.keys()))

        if filtered_qrels:
            aggregate, _ = evaluate_run_dict(filtered_qrels, filtered_run, METRICS)
        else:
            aggregate = {m: 0.0 for m in METRICS}

        results.append({
            "cutoff_date": cutoff.strftime("%Y-%m-%d"),
            "days_since_start": (cutoff - WINDOW_START).days + 1,
            "doc_count": len(allowed_docs),
            "query_count": len(filtered_qrels),
            **{m: round(aggregate.get(m, 0.0), 4) for m in METRICS},
        })
        cutoff += timedelta(days=step_days)

    return results


def write_outputs(results: list[dict], output_dir: Path) -> None:
    """
    Write per-cutoff evaluation results to CSV, JSON, and a Markdown summary in the given output directory.
    
    Creates the files daily_split_metrics.csv, daily_split_metrics.json, and daily_split_summary.md inside output_dir (directory is created if missing). The CSV contains one row per entry in results using the keys of the first result as columns. The JSON is a pretty-printed serialization of results. The Markdown file contains a human-readable table with columns: Cutoff Date, Days, Docs, Queries, nDCG@10, nDCG@1000, MAP, Recall@100, Recall@1000. Prints the output directory and filenames after writing.
    
    Parameters:
        results (list[dict]): Sequence of per-window result dictionaries. Each dict is expected to include at least the keys: 'cutoff_date', 'days_since_start', 'doc_count', 'query_count', 'ndcg_cut_10', 'ndcg_cut_1000', 'map', 'recall_100', and 'recall_1000'.
        output_dir (Path): Destination directory for the generated files; will be created if it does not exist.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "daily_split_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    json_path = output_dir / "daily_split_metrics.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    md_lines = [
        "# BM25 Fulltext — Daily Cumulative Split Metrics",
        "",
        "Model: `custom_lexical_fulltext` | Snapshot: `snapshot-1-train` | Date field: `publishedDate`",
        "",
        "| Cutoff Date | Days | Docs | Queries | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        md_lines.append(
            f"| {row['cutoff_date']} | {row['days_since_start']} "
            f"| {row['doc_count']:,} | {row['query_count']} "
            f"| {row['ndcg_cut_10']:.4f} | {row['ndcg_cut_1000']:.4f} "
            f"| {row['map']:.4f} | {row['recall_100']:.4f} | {row['recall_1000']:.4f} |"
        )
    (output_dir / "daily_split_summary.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Outputs written to {output_dir}")
    print(f"  {csv_path.name}")
    print(f"  {json_path.name}")
    print(f"  daily_split_summary.md")


def main() -> None:
    """
    Run the daily cumulative split evaluation from the command line.
    
    Parses CLI arguments for a TREC run file, step size, and output directory; validates the run file exists (exits with status 1 if missing); computes per-cutoff evaluation results via evaluate_daily_splits; prints a compact tabular preview to stdout; and writes CSV, JSON, and Markdown outputs to the specified output directory.
    """
    parser = argparse.ArgumentParser(description="Daily cumulative split evaluation for BM25 fulltext.")
    parser.add_argument(
        "--run",
        default=str(ROOT / "outputs" / "custom_lexical_fulltext" / "snapshot-1-train" / "run.txt"),
        help="Path to the TREC run file.",
    )
    parser.add_argument("--step-days", type=int, default=7, help="Step size in days (default: 7).")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "adaptive_monitor" / "outputs" / "daily_splits"),
        help="Output directory.",
    )
    args = parser.parse_args()

    run_path = Path(args.run)
    if not run_path.exists():
        print(f"ERROR: run file not found at {run_path}")
        print("Re-run BM25 retrieval first:")
        print("  python scripts/run_baseline.py --config configs/custom_lexical_fulltext.yaml --snapshot-id snapshot-1-train --train-snapshot1")
        sys.exit(1)

    print(f"Evaluating {run_path} with step={args.step_days} days ...")
    results = evaluate_daily_splits(run_path, step_days=args.step_days)

    print(f"\n{'Cutoff':12} {'Docs':>8} {'Queries':>8} {'nDCG@10':>9} {'MAP':>7} {'R@1000':>8}")
    print("-" * 60)
    for row in results:
        print(
            f"{row['cutoff_date']:12} {row['doc_count']:>8,} {row['query_count']:>8} "
            f"{row['ndcg_cut_10']:>9.4f} {row['map']:>7.4f} {row['recall_1000']:>8.4f}"
        )

    write_outputs(results, Path(args.output_dir))


if __name__ == "__main__":
    main()
