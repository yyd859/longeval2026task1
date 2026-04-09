"""Baseline suite orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from longeval_sci.baselines.runner import BaselineRunResult, run_baseline
from longeval_sci.config import ExperimentConfig, load_config
from longeval_sci.evaluation.longitudinal import write_longitudinal_outputs


@dataclass(slots=True)
class BaselineSpec:
    config_path: str
    config: ExperimentConfig


def load_baseline_specs(config_paths: list[str]) -> list[BaselineSpec]:
    """Load baseline configs from disk."""
    return [BaselineSpec(config_path=path, config=load_config(path)) for path in config_paths]


def run_baseline_suite(config_paths: list[str], report_dir: str) -> tuple[list[BaselineRunResult], dict[str, str]]:
    """Run all baselines across their configured snapshots and write consolidated reports."""
    specs = load_baseline_specs(config_paths)
    results = [run_baseline(spec.config) for spec in specs]
    artifacts = write_longitudinal_outputs(results, report_dir)
    return results, artifacts
