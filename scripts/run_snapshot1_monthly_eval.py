"""Evaluate a snapshot-1 train run on month-filtered qrel views without rebuilding indices."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval, run_baseline
from longeval_sci.config import load_config, snapshot_run_path
from longeval_sci.evaluation.monthly_split import evaluate_month_split, write_month_split_outputs


def _deep_merge(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    merged = dict(parent)
    for key, value in child.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_monthly_plan(path: str | Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML is required for the monthly split plan")
    plan_path = Path(path)
    with plan_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    extends = raw.pop("extends", None)
    if extends:
        parent = _load_monthly_plan((plan_path.parent / extends).resolve())
        raw = _deep_merge(parent, raw)
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or reuse snapshot-1 train baseline results and evaluate month splits.")
    parser.add_argument("--config", required=True, help="Path to baseline config.")
    parser.add_argument("--plan", default="configs/snapshot1_monthly_eval.yaml", help="Month-split plan YAML.")
    parser.add_argument("--qrels-variant", default="dctr", choices=["dctr", "raw"], help="Train qrels variant.")
    parser.add_argument("--reuse-existing-run", action="store_true", help="Reuse an existing snapshot-1-train run if present.")
    parser.add_argument("--run-path", help="Optional explicit run file to evaluate instead of the config-derived output path.")
    args = parser.parse_args()

    config = clone_for_train_eval(load_config(args.config), qrels_variant=args.qrels_variant)
    run_path = Path(args.run_path).resolve() if args.run_path else snapshot_run_path(config, "snapshot-1")
    if not args.reuse_existing_run or not run_path.exists():
        run_baseline(config)

    plan = _load_monthly_plan(args.plan)
    monthly_cfg = plan.get("monthly_split", {})
    split_specs = plan.get(
        "splits",
        [
            {"name": "train_months", "months": monthly_cfg.get("train_months", [3, 4])},
            {"name": "validation_months", "months": monthly_cfg.get("validation_months", [5])},
        ],
    )

    results = []
    per_query_by_split = {}
    for split in split_specs:
        result, per_query_rows = evaluate_month_split(
            dataset_config=config.dataset,
            snapshot_id="snapshot-1",
            run_path=run_path,
            metrics=config.metrics,
            date_field=monthly_cfg.get("date_field", "publishedDate"),
            months=list(split["months"]),
            split_name=str(split["name"]),
            minimum_qrels_per_query=int(monthly_cfg.get("minimum_qrels_per_query", 1)),
        )
        results.append(result)
        per_query_by_split[result.split_name] = per_query_rows

    output_root = Path(
        plan.get(
            "output_dir",
            "outputs/reports/monthly_split",
        )
    )
    output_dir = output_root / f"{config.run_name}_{args.qrels_variant}"
    artifacts = write_month_split_outputs(results, per_query_by_split, output_dir)
    for key, value in artifacts.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
