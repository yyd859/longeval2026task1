"""Run the canonical LongEval-Sci baseline suite and write consolidated reports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.reporting.suite import run_baseline_suite


def _load_plan(path: str) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load the all-snapshots reporting plan")
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the canonical LongEval-Sci baseline suite.")
    parser.add_argument("--plan", default="configs/all_snapshots_reporting.yaml", help="Reporting plan YAML.")
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    configs = list(plan.get("baseline_configs", []))
    report_dir = str(plan.get("report_dir", "outputs/reports/long_eval_2026_task1"))
    _results, artifacts = run_baseline_suite(configs, report_dir)
    for key, value in artifacts.items():
        print(f"{key}: {value}")
