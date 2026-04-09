"""Public evaluation APIs."""

from __future__ import annotations

import json
from pathlib import Path

from longeval_sci.config import DatasetConfig, snapshot_dataset_name
from longeval_sci.evaluation.pytrec_eval_wrapper import evaluate_run_dict
from longeval_sci.io.dataset import load_qrels
from longeval_sci.io.trec import read_trec_run, write_per_query_csv


def evaluate_run(
    dataset_config: DatasetConfig,
    snapshot_id: str,
    run_path: str,
    metrics: list[str],
    metrics_path: str | None = None,
    per_query_metrics_path: str | None = None,
) -> dict[str, float]:
    """Evaluate a TREC run file against qrels for one snapshot."""
    qrels = load_qrels(dataset_config, snapshot_id)
    run = read_trec_run(run_path)
    aggregate, per_query_rows = evaluate_run_dict(qrels, run, metrics)

    if metrics_path:
        output_path = Path(metrics_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset_name": snapshot_dataset_name(dataset_config, snapshot_id),
            "snapshot_id": snapshot_id,
            "metrics": aggregate,
        }
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    if per_query_metrics_path:
        write_per_query_csv(per_query_rows, per_query_metrics_path)

    return aggregate
