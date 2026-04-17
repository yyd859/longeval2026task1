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
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _doc_ids_up_to(bundle, cutoff: datetime, date_field: str) -> set[str]:
    allowed: set[str] = set()
    for doc in bundle.documents:
        dt = _parse_dt(doc.metadata.get(date_field))
        if dt is not None and dt <= cutoff:
            allowed.add(doc.doc_id)
    return allowed


def _filter_qrels(qrels, allowed_doc_ids: set[str], min_qrels: int = 1):
    filtered = {}
    for qid, docrels in qrels.items():
        kept = {d: r for d, r in docrels.items() if d in allowed_doc_ids}
        if len(kept) >= min_qrels:
            filtered[qid] = kept
    return filtered


def _filter_run(run, allowed_doc_ids: set[str], allowed_qids: set[str]):
    filtered = {}
    for qid, docs in run.items():
        if qid not in allowed_qids:
            continue
        filtered[qid] = {d: s for d, s in docs.items() if d in allowed_doc_ids}
    return filtered


def evaluate_daily_splits(run_path: Path, step_days: int = 7) -> list[dict]:
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
