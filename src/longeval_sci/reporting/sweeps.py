"""Reporting helpers for rerank sweep experiments."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from longeval_sci.baselines.runner import BaselineRunResult


@dataclass(slots=True)
class SweepDescriptor:
    run_name: str
    pipeline: str
    rerank_model: str
    candidate_k: int
    top_k: int


def _extract_metrics(result: BaselineRunResult) -> dict[str, float]:
    if not result.snapshots or result.snapshots[0].metrics is None:
        return {}
    return {key: float(value) for key, value in result.snapshots[0].metrics.items()}


def write_rerank_sweep_outputs(
    results: list[BaselineRunResult],
    descriptors: list[SweepDescriptor],
    output_dir: str | Path,
) -> dict[str, str]:
    """Write CSV, JSON, and Markdown summaries for rerank sweep runs."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    descriptor_lookup = {descriptor.run_name: descriptor for descriptor in descriptors}
    for result in results:
        descriptor = descriptor_lookup[result.config.run_name]
        row: dict[str, object] = {
            "run_name": descriptor.run_name,
            "pipeline": descriptor.pipeline,
            "rerank_model": descriptor.rerank_model,
            "candidate_k": descriptor.candidate_k,
            "top_k": descriptor.top_k,
        }
        row.update(_extract_metrics(result))
        rows.append(row)

    csv_path = root / "rerank_sweep.csv"
    json_path = root / "rerank_sweep.json"
    md_path = root / "rerank_sweep.md"

    fieldnames = [
        "run_name",
        "pipeline",
        "rerank_model",
        "candidate_k",
        "top_k",
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
        "# Rerank Sweep",
        "",
        "| Run | Pipeline | Rerank Model | Candidate K | Top K | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        md_lines.append(
            "| {run_name} | {pipeline} | {rerank_model} | {candidate_k} | {top_k} | "
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

    return {
        "csv": str(csv_path),
        "json": str(json_path),
        "markdown": str(md_path),
    }
