"""Fuse existing run files with Reciprocal Rank Fusion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval
from longeval_sci.config import load_config, snapshot_metrics_path, snapshot_output_name, snapshot_per_query_metrics_path, snapshot_run_path
from longeval_sci.evaluation.run_eval import evaluate_run
from longeval_sci.fusion.rrf import rrf_fuse
from longeval_sci.io.dataset import load_dataset_bundle
from longeval_sci.io.trec import read_trec_results, write_trec_run
from longeval_sci.utils.logging import configure_logging
from longeval_sci.utils.paths import ensure_parent


def _write_progress(output_dir: Path, stage: str, completed: int, total: int, note: str) -> None:
    progress_path = output_dir / "progress.json"
    ensure_parent(progress_path)
    payload = {
        "stage": stage,
        "completed_runs": completed,
        "total_runs": total,
        "note": note,
    }
    progress_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_metrics_status(metrics_path: Path, per_query_path: Path, dataset_name: str, snapshot_id: str) -> None:
    ensure_parent(metrics_path)
    metrics_path.write_text(
        json.dumps(
            {
                "dataset_name": dataset_name,
                "snapshot_id": snapshot_id,
                "metrics": None,
                "status": "skipped",
                "reason": "qrels_unavailable",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    ensure_parent(per_query_path)
    per_query_path.write_text("query_id,status,reason\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuse existing run files with Reciprocal Rank Fusion.")
    parser.add_argument("--run-name", required=True, help="Name for the fused run and output folder.")
    parser.add_argument("--input-run", action="append", required=True, help="Input run file. Repeat for multiple runs.")
    parser.add_argument("--config", default="configs/official_pyterrier.yaml", help="Config used for dataset/evaluation context.")
    parser.add_argument("--snapshot-id", default="snapshot-1", help="Snapshot id to associate with this fused run.")
    parser.add_argument("--train-snapshot1", action="store_true", help="Evaluate against snapshot-1 train qrels.")
    parser.add_argument("--qrels-variant", default="dctr", choices=["dctr", "raw"], help="Qrels variant for train mode.")
    parser.add_argument("--k", type=int, default=60, help="RRF constant.")
    parser.add_argument("--top-k", type=int, default=1000, help="Top depth to keep after fusion.")
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    if args.train_snapshot1:
        config = clone_for_train_eval(config, qrels_variant=args.qrels_variant)
    config.run_name = args.run_name
    config.dataset.snapshot_ids = [args.snapshot_id]

    output_dir = snapshot_run_path(config, args.snapshot_id).parent
    _write_progress(output_dir, "loading_runs", 0, len(args.input_run), "Starting to load input runs.")

    loaded_runs = []
    for index, run_path_text in enumerate(args.input_run, start=1):
        run_path = (ROOT / run_path_text).resolve() if not Path(run_path_text).is_absolute() else Path(run_path_text)
        loaded_runs.append(read_trec_results(run_path))
        _write_progress(output_dir, "loading_runs", index, len(args.input_run), f"Loaded {run_path.name}.")

    _write_progress(output_dir, "fusing", len(args.input_run), len(args.input_run), "Computing reciprocal rank fusion.")
    fused_results = rrf_fuse(loaded_runs, k=args.k, top_k=args.top_k, run_name=args.run_name)
    run_path = snapshot_run_path(config, args.snapshot_id)
    ensure_parent(run_path)
    write_trec_run(fused_results, run_path)

    metrics_path = snapshot_metrics_path(config, args.snapshot_id)
    per_query_path = snapshot_per_query_metrics_path(config, args.snapshot_id)
    bundle = load_dataset_bundle(config.dataset, args.snapshot_id)
    if bundle.metadata.has_qrels:
        _write_progress(output_dir, "evaluating", len(args.input_run), len(args.input_run), "Evaluating fused run.")
        evaluate_run(
            dataset_config=config.dataset,
            snapshot_id=args.snapshot_id,
            run_path=str(run_path),
            metrics=config.metrics,
            metrics_path=str(metrics_path),
            per_query_metrics_path=str(per_query_path),
        )
    else:
        _write_metrics_status(metrics_path, per_query_path, bundle.metadata.dataset_name, args.snapshot_id)

    _write_progress(output_dir, "complete", len(args.input_run), len(args.input_run), "Fused run complete.")
    print(run_path)
    print(metrics_path)


if __name__ == "__main__":
    main()
