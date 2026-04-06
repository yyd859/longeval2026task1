"""Evaluate one configured LongEval-Sci run."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.config import load_config, metrics_path_for_snapshot, per_query_metrics_path_for_snapshot, run_path_for_snapshot
from longeval_sci.evaluation.run_eval import evaluate_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a configured LongEval-Sci run")
    parser.add_argument("--config", required=True)
    parser.add_argument("--metrics", nargs="*", default=["ndcg_cut_10", "map", "recall_100", "recall_1000"])
    args = parser.parse_args()

    config = load_config(args.config)
    metrics = evaluate_run(
        dataset_config=config.dataset,
        run_path=str(run_path_for_snapshot(config)),
        metrics=args.metrics,
        metrics_path=str(metrics_path_for_snapshot(config)),
        per_query_metrics_path=str(per_query_metrics_path_for_snapshot(config)),
    )
    print(metrics)


if __name__ == "__main__":
    main()
