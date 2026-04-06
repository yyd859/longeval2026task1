"""Inspect a LongEval dataset backend."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.config import DatasetConfig
from longeval_sci.io.dataset import load_dataset_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a LongEval-Sci dataset")
    parser.add_argument("--dataset", required=True, help="Dataset id such as longeval-sci-2026/snapshot-1")
    parser.add_argument("--snapshot-id", default=None)
    parser.add_argument("--qrels-variant", default="dctr", choices=["raw", "dctr"])
    args = parser.parse_args()

    try:
        bundle = load_dataset_bundle(
            DatasetConfig(
                backend="ir_datasets_longeval",
                dataset_name=args.dataset,
                snapshot_id=args.snapshot_id,
                qrels_variant=args.qrels_variant,
            )
        )
    except Exception as exc:
        print(f"dataset inspection failed: {exc}")
        raise SystemExit(1) from exc

    print(f"dataset_name: {bundle.metadata.dataset_name}")
    print(f"snapshot_id: {bundle.metadata.snapshot_id}")
    print(f"documents: {len(bundle.documents)}")
    print(f"queries: {len(bundle.queries)}")
    print(f"has_qrels: {bundle.metadata.has_qrels}")
    print(f"qrels_variant: {bundle.metadata.qrels_variant}")
    print(f"timestamp: {bundle.metadata.timestamp}")
    print(f"prior_datasets: {bundle.metadata.prior_dataset_names}")


if __name__ == "__main__":
    main()
