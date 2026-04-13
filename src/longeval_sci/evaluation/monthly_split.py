"""Month-based filtered evaluation for snapshot-1 development."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from longeval_sci.config import DatasetConfig
from longeval_sci.evaluation.pytrec_eval_wrapper import evaluate_run_dict
from longeval_sci.io.dataset import load_dataset_bundle
from longeval_sci.io.trec import read_trec_run


@dataclass(slots=True)
class MonthSplitResult:
    split_name: str
    date_field: str
    months: list[int]
    query_count: int
    doc_count: int
    metrics: dict[str, float]


def _parse_month(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).month
    except ValueError:
        return None


def _allowed_doc_ids(
    dataset_config: DatasetConfig,
    snapshot_id: str,
    date_field: str,
    months: list[int],
) -> set[str]:
    bundle = load_dataset_bundle(dataset_config, snapshot_id)
    allowed: set[str] = set()
    for document in bundle.documents:
        month = _parse_month(str(document.metadata.get(date_field, "")))
        if month in months:
            allowed.add(document.doc_id)
    return allowed


def _filter_qrels(
    qrels: dict[str, dict[str, int]],
    allowed_doc_ids: set[str],
    minimum_qrels_per_query: int = 1,
) -> dict[str, dict[str, int]]:
    filtered: dict[str, dict[str, int]] = {}
    for query_id, docrels in qrels.items():
        kept = {doc_id: rel for doc_id, rel in docrels.items() if doc_id in allowed_doc_ids}
        if len(kept) >= minimum_qrels_per_query:
            filtered[query_id] = kept
    return filtered


def _filter_run(
    run: dict[str, dict[str, float]],
    allowed_doc_ids: set[str],
    allowed_query_ids: set[str],
) -> dict[str, dict[str, float]]:
    filtered: dict[str, dict[str, float]] = {}
    for query_id, docs in run.items():
        if query_id not in allowed_query_ids:
            continue
        kept = {doc_id: score for doc_id, score in docs.items() if doc_id in allowed_doc_ids}
        filtered[query_id] = kept
    return filtered


def evaluate_month_split(
    dataset_config: DatasetConfig,
    snapshot_id: str,
    run_path: str | Path,
    metrics: list[str],
    date_field: str,
    months: list[int],
    split_name: str,
    minimum_qrels_per_query: int = 1,
) -> tuple[MonthSplitResult, list[dict[str, str | float]]]:
    """Evaluate a run against a month-filtered view of snapshot qrels."""
    bundle = load_dataset_bundle(dataset_config, snapshot_id)
    if bundle.qrels is None:
        raise ValueError(f"No qrels available for month split evaluation on {snapshot_id}")

    allowed_doc_ids = _allowed_doc_ids(dataset_config, snapshot_id, date_field, months)
    filtered_qrels = _filter_qrels(bundle.qrels, allowed_doc_ids, minimum_qrels_per_query)
    filtered_run = _filter_run(read_trec_run(run_path), allowed_doc_ids, set(filtered_qrels.keys()))
    aggregate, per_query_rows = evaluate_run_dict(filtered_qrels, filtered_run, metrics)
    result = MonthSplitResult(
        split_name=split_name,
        date_field=date_field,
        months=months,
        query_count=len(filtered_qrels),
        doc_count=len(allowed_doc_ids),
        metrics=aggregate,
    )
    return result, per_query_rows


def write_month_split_outputs(
    results: list[MonthSplitResult],
    per_query_by_split: dict[str, list[dict[str, str | float]]],
    output_dir: str | Path,
) -> dict[str, str]:
    """Write CSV, JSON, and Markdown reports for month split evaluation."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    rows = []
    for result in results:
        row: dict[str, object] = {
            "split_name": result.split_name,
            "date_field": result.date_field,
            "months": ",".join(str(month) for month in result.months),
            "query_count": result.query_count,
            "doc_count": result.doc_count,
        }
        row.update(result.metrics)
        rows.append(row)

    csv_path = root / "monthly_split_metrics.csv"
    json_path = root / "monthly_split_metrics.json"
    md_path = root / "monthly_split_summary.md"

    fieldnames = [
        "split_name",
        "date_field",
        "months",
        "query_count",
        "doc_count",
        "ndcg_cut_10",
        "ndcg_cut_1000",
        "map",
        "recall_100",
        "recall_1000",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")

    md_lines = [
        "# Snapshot-1 Month Split Evaluation",
        "",
        "| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        md_lines.append(
            "| {split_name} | {date_field} | {months} | {query_count} | {doc_count} | "
            "{ndcg_cut_10:.4f} | {ndcg_cut_1000:.4f} | {map:.4f} | {recall_100:.4f} | {recall_1000:.4f} |".format(
                **{
                    **row,
                    "ndcg_cut_10": float(row.get("ndcg_cut_10", 0.0)),
                    "ndcg_cut_1000": float(row.get("ndcg_cut_1000", 0.0)),
                    "map": float(row.get("map", 0.0)),
                    "recall_100": float(row.get("recall_100", 0.0)),
                    "recall_1000": float(row.get("recall_1000", 0.0)),
                }
            )
        )
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    for split_name, per_query_rows in per_query_by_split.items():
        if not per_query_rows:
            continue
        per_query_path = root / f"{split_name}_per_query.csv"
        with per_query_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(per_query_rows[0].keys()))
            writer.writeheader()
            writer.writerows(per_query_rows)

    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "markdown": str(md_path),
    }
