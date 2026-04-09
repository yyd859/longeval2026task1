"""Run all five LongEval-Sci baselines across all three snapshots and write consolidated reports."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.reporting.suite import run_baseline_suite


if __name__ == "__main__":
    configs = [
        "configs/official_pyterrier.yaml",
        "configs/official_pyterrier_dense.yaml",
        "configs/custom_lexical_fulltext.yaml",
        "configs/custom_dense_rerank.yaml",
        "configs/custom_hybrid_union_rerank.yaml",
    ]
    _results, artifacts = run_baseline_suite(configs, "outputs/reports/long_eval_2026_task1")
    for key, value in artifacts.items():
        print(f"{key}: {value}")
