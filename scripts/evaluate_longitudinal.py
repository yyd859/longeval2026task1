"""Evaluate runs across LongEval snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.evaluation.longitudinal import evaluate_longitudinal_runs, write_longitudinal_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate longitudinal LongEval-Sci runs")
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--dataset-prefix", default="longeval-sci-2026")
    parser.add_argument("--qrels-variant", default="dctr", choices=["raw", "dctr"])
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--csv-out", default=None)
    args = parser.parse_args()

    payload = evaluate_longitudinal_runs(
        runs_dir=args.runs_dir,
        dataset_prefix=args.dataset_prefix,
        qrels_variant=args.qrels_variant,
    )

    json_out = args.json_out or str(Path(args.runs_dir) / "longitudinal_summary.json")
    csv_out = args.csv_out or str(Path(args.runs_dir) / "longitudinal_summary.csv")
    write_longitudinal_reports(payload, json_out, csv_out)
    print(f"Wrote {json_out}")
    print(f"Wrote {csv_out}")


if __name__ == "__main__":
    main()
