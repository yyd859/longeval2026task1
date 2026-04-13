"""Run one LongEval-Sci baseline config, optionally in snapshot-1 train mode."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import build_required_indices, clone_for_train_eval, run_baseline
from longeval_sci.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one LongEval-Sci baseline.")
    parser.add_argument("--config", required=True, help="Path to the baseline YAML config.")
    parser.add_argument("--train-snapshot1", action="store_true", help="Switch to snapshot-1 train evaluation mode.")
    parser.add_argument("--qrels-variant", default="dctr", choices=["dctr", "raw"], help="Qrels variant for train mode.")
    parser.add_argument("--build-indices-only", action="store_true", help="Only build required canonical indices.")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.train_snapshot1:
        config = clone_for_train_eval(config, qrels_variant=args.qrels_variant)

    if args.build_indices_only:
        build_required_indices(config)
        return

    result = run_baseline(config)
    for snapshot in result.snapshots:
        print(snapshot.snapshot_id, snapshot.run_path, snapshot.metrics_path, snapshot.metrics)


if __name__ == "__main__":
    main()
