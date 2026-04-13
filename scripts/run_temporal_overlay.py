"""Apply the temporal rerank overlay to an existing run file."""

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
from longeval_sci.config import load_config, snapshot_metrics_path, snapshot_per_query_metrics_path, snapshot_run_path
from longeval_sci.evaluation.run_eval import evaluate_run
from longeval_sci.io.dataset import load_dataset_bundle
from longeval_sci.io.trec import read_trec_results, write_trec_run
from longeval_sci.temporal.rerank import temporal_rerank_results
from longeval_sci.utils.logging import configure_logging
from longeval_sci.utils.paths import ensure_parent


def _write_progress(output_dir: Path, stage: str, completed: int, total: int, note: str) -> None:
    progress_path = output_dir / "progress.json"
    ensure_parent(progress_path)
    payload = {
        "stage": stage,
        "completed_queries": completed,
        "total_queries": total,
        "note": note,
    }
    progress_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply temporal reranking to an existing run file.")
    parser.add_argument("--config", required=True, help="Temporal config to use.")
    parser.add_argument("--input-run", required=True, help="Existing run file to rerank.")
    parser.add_argument("--snapshot-id", default="snapshot-1", help="Snapshot id for dataset loading.")
    parser.add_argument("--train-snapshot1", action="store_true", help="Use snapshot-1 train queries/qrels.")
    parser.add_argument("--qrels-variant", default="dctr", choices=["dctr", "raw"], help="Qrels variant for train mode.")
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    if args.train_snapshot1:
        config = clone_for_train_eval(config, qrels_variant=args.qrels_variant)
    if not config.temporal.enabled:
        raise SystemExit("The provided config does not enable the temporal overlay.")

    bundle = load_dataset_bundle(config.dataset, args.snapshot_id)
    input_run = ROOT / args.input_run if not Path(args.input_run).is_absolute() else Path(args.input_run)
    if not input_run.exists():
        raise FileNotFoundError(f"Input run does not exist: {input_run}")

    output_dir = snapshot_run_path(config, args.snapshot_id).parent
    _write_progress(output_dir, "loading_run", 0, len(bundle.queries), f"Loading existing run from {input_run}.")
    results = read_trec_results(input_run)
    reranked = temporal_rerank_results(
        results=results,
        bundle=bundle,
        config=config,
        progress_callback=lambda stage, completed, total, note: _write_progress(output_dir, stage, completed, total, note),
    )

    run_path = snapshot_run_path(config, args.snapshot_id)
    ensure_parent(run_path)
    write_trec_run(reranked, run_path)
    metrics_path = snapshot_metrics_path(config, args.snapshot_id)
    per_query_path = snapshot_per_query_metrics_path(config, args.snapshot_id)
    if bundle.metadata.has_qrels:
        evaluate_run(
            dataset_config=config.dataset,
            snapshot_id=args.snapshot_id,
            run_path=str(run_path),
            metrics=config.metrics,
            metrics_path=str(metrics_path),
            per_query_metrics_path=str(per_query_path),
        )
    _write_progress(output_dir, "complete", len(bundle.queries), len(bundle.queries), "Temporal overlay complete.")
    print(run_path)
    print(metrics_path)


if __name__ == "__main__":
    main()
