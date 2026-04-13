"""Run rerank depth/model sweeps on snapshot-1 train and write a compact report."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval, run_baseline
from longeval_sci.config import load_config
from longeval_sci.reporting.sweeps import SweepDescriptor, write_rerank_sweep_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rerank sweeps on snapshot-1 train.")
    parser.add_argument("--config", required=True, help="Base config path, e.g. configs/custom_dense_rerank.yaml")
    parser.add_argument("--qrels-variant", default="dctr", choices=["dctr", "raw"], help="Train qrels variant.")
    parser.add_argument(
        "--candidate-k",
        nargs="+",
        type=int,
        default=[100, 200, 500, 1000],
        help="Candidate depths to test.",
    )
    parser.add_argument(
        "--rerank-model",
        nargs="+",
        default=["cross-encoder/ms-marco-MiniLM-L-12-v2"],
        help="Reranker model names to test.",
    )
    parser.add_argument(
        "--report-dir",
        default="outputs/reports/rerank_sweeps/train_snapshot1",
        help="Directory for sweep reports.",
    )
    args = parser.parse_args()

    base_config = clone_for_train_eval(load_config(args.config), qrels_variant=args.qrels_variant)
    results = []
    descriptors: list[SweepDescriptor] = []

    for rerank_model in args.rerank_model:
        for candidate_k in args.candidate_k:
            config = deepcopy(base_config)
            safe_model_name = rerank_model.split("/")[-1].replace(".", "_")
            config.run_name = f"{base_config.run_name}__{safe_model_name}__k{candidate_k}"
            config.rerank.model_name = rerank_model
            config.rerank.candidate_k = candidate_k
            config.rerank.top_k = candidate_k
            config.retrieval.top_k = max(config.retrieval.top_k, candidate_k)
            results.append(run_baseline(config))
            descriptors.append(
                SweepDescriptor(
                    run_name=config.run_name,
                    pipeline=config.pipeline,
                    rerank_model=rerank_model,
                    candidate_k=candidate_k,
                    top_k=config.rerank.top_k,
                )
            )

    artifacts = write_rerank_sweep_outputs(results, descriptors, args.report_dir)
    for key, value in artifacts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
