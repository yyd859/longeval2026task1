"""Adaptive reindex pipeline entry point.

The pipeline reads trigger decisions, writes a reproducible manifest, and can
build a shadow index for the configured retrieval branch. Promotion is explicit
and disabled by default.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive_monitor.trigger_decision import (  # noqa: E402
    DEFAULT_ANALYTICS_DIR,
    DEFAULT_OUTPUT_DIR,
    TriggerDecision,
    TriggerThresholds,
    compute_trigger_decisions,
    latest_actionable_decision,
    write_trigger_decisions,
)
from adaptive_monitor.incremental_reindex import (  # noqa: E402
    build_incremental_lexical_shadow_index,
    week_end,
)
from longeval_sci.baselines.runner import build_required_indices, clone_for_train_eval  # noqa: E402
from longeval_sci.config import (  # noqa: E402
    canonical_dense_index_dir,
    canonical_lexical_index_dir,
    load_config,
)


DEFAULT_CONFIG = ROOT / "configs" / "custom_lexical_fulltext.yaml"


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def _config_for_build(config_path: Path, *, train_snapshot1: bool, qrels_variant: str):
    config = load_config(config_path)
    if train_snapshot1:
        config = clone_for_train_eval(config, qrels_variant=qrels_variant)
    return config


def _required_live_index_paths(config) -> list[Path]:
    paths: list[Path] = []
    for snapshot_id in config.dataset.snapshot_ids:
        pipeline = config.pipeline
        if pipeline in {"official_pyterrier", "custom_title_abstract_rm3", "custom_title_abstract_rerank"}:
            index_dir = canonical_lexical_index_dir(config, snapshot_id, "title_abstract")
            if index_dir is not None:
                paths.append(index_dir)
        elif pipeline in {"custom_lexical_fulltext", "custom_lexical_fulltext_rm3"}:
            index_dir = canonical_lexical_index_dir(config, snapshot_id, "full_text")
            if index_dir is not None:
                paths.append(index_dir)
        elif pipeline == "official_pyterrier_dense":
            index_dir = canonical_dense_index_dir(
                config,
                snapshot_id,
                config.retrieval.text_mode,
                config.retrieval.model_name,
                backend_label="official_dense",
            )
            if index_dir is not None:
                paths.append(index_dir)
    return paths


def _lexical_text_mode_for_pipeline(config) -> str | None:
    if config.pipeline in {"official_pyterrier", "custom_title_abstract_rm3", "custom_title_abstract_rerank"}:
        return "title_abstract"
    if config.pipeline in {"custom_lexical_fulltext", "custom_lexical_fulltext_rm3"}:
        return "full_text"
    return None


def _shadow_config(config, shadow_index_root: Path):
    shadow = deepcopy(config)
    shadow.retrieval.index_root = str(shadow_index_root)
    return shadow


def _promote_shadow_indexes(shadow_config, live_config) -> list[dict[str, str]]:
    promoted = []
    for shadow_path, live_path in zip(_required_live_index_paths(shadow_config), _required_live_index_paths(live_config)):
        if not shadow_path.exists():
            raise FileNotFoundError(f"Shadow index path does not exist: {shadow_path}")
        if live_path.exists():
            backup_path = live_path.with_name(f"{live_path.name}.backup-{_timestamp()}")
            shutil.move(str(live_path), str(backup_path))
        else:
            backup_path = None
        live_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(shadow_path), str(live_path))
        promoted.append(
            {
                "shadow_path": str(shadow_path),
                "live_path": str(live_path),
                "backup_path": str(backup_path) if backup_path else "",
            }
        )
    return promoted


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_incremental_shadow(live_config, shadow_config, selected: TriggerDecision, args: argparse.Namespace, run_dir: Path) -> list[dict]:
    text_mode = _lexical_text_mode_for_pipeline(live_config)
    if text_mode is None:
        raise ValueError(f"Incremental reindex is only implemented for lexical PyTerrier pipelines, got {live_config.pipeline}")
    if not args.last_reindex_week:
        raise ValueError("Incremental reindex requires --last-reindex-week so the delta document window is explicit.")

    results = []
    start_after = week_end(args.last_reindex_week)
    end_at = week_end(selected.week_start)
    for snapshot_id in live_config.dataset.snapshot_ids:
        live_index_dir = canonical_lexical_index_dir(live_config, snapshot_id, text_mode)
        shadow_index_dir = canonical_lexical_index_dir(shadow_config, snapshot_id, text_mode)
        if live_index_dir is None or shadow_index_dir is None:
            raise ValueError("Lexical incremental reindex requires configured index roots.")
        delta_index_dir = run_dir / "delta_indexes" / snapshot_id / text_mode / "lexical_pyterrier"
        result = build_incremental_lexical_shadow_index(
            dataset_config=live_config.dataset,
            snapshot_id=snapshot_id,
            text_mode=text_mode,
            live_index_dir=live_index_dir,
            shadow_index_dir=shadow_index_dir,
            delta_index_dir=delta_index_dir,
            date_field=args.date_field,
            start_after=start_after,
            end_at=end_at,
            memory_limit_mb=live_config.runtime.pyterrier_memory_mb,
            manifest_path=run_dir / "incremental" / f"{snapshot_id}_{text_mode}.json",
        )
        results.append(asdict(result))
    return results


def run_pipeline(args: argparse.Namespace) -> int:
    thresholds = TriggerThresholds(
        staleness_rate=args.staleness_rate,
        coverage_gap=args.coverage_gap,
        temporal_gap_growth_days=args.temporal_gap_growth_days,
        velocity_multiplier=args.velocity_multiplier,
        baseline_weeks=args.baseline_weeks,
    )
    output_dir = Path(args.output_dir)
    decisions = compute_trigger_decisions(
        Path(args.analytics_dir),
        thresholds=thresholds,
        last_reindex_week=args.last_reindex_week,
        rank_stability_path=Path(args.rank_stability) if args.rank_stability else None,
    )
    decision_csv, decision_json = write_trigger_decisions(decisions, output_dir)
    selected = latest_actionable_decision(decisions)

    run_id = args.run_id or _timestamp()
    run_dir = output_dir / "runs" / run_id
    config_path = Path(args.config)
    live_config = _config_for_build(config_path, train_snapshot1=args.train_snapshot1, qrels_variant=args.qrels_variant)
    shadow_index_root = run_dir / "shadow_indexes"
    shadow_config = _shadow_config(live_config, shadow_index_root)

    manifest = {
        "run_id": run_id,
        "created_at": _timestamp(),
        "mode": args.mode,
        "config": str(config_path),
        "train_snapshot1": args.train_snapshot1,
        "qrels_variant": args.qrels_variant,
        "analytics_dir": str(Path(args.analytics_dir)),
        "decision_csv": str(decision_csv),
        "decision_json": str(decision_json),
        "thresholds": asdict(thresholds),
        "date_field": args.date_field,
        "selected_decision": asdict(selected) if selected else None,
        "live_index_paths": [str(path) for path in _required_live_index_paths(live_config)],
        "shadow_index_root": str(shadow_index_root),
        "shadow_index_paths": [str(path) for path in _required_live_index_paths(shadow_config)],
        "status": "planned",
        "promotion": [],
        "incremental_reindex": [],
    }

    if selected is None:
        manifest["status"] = "no_action"
        _write_manifest(run_dir / "manifest.json", manifest)
        print("No trigger exceeded thresholds. No reindex action planned.")
        print(f"Manifest: {run_dir / 'manifest.json'}")
        return 0

    if args.mode == "plan":
        _write_manifest(run_dir / "manifest.json", manifest)
        print(
            f"Planned reindex action: level={selected.trigger_level} action={selected.action} "
            f"week={selected.week_start}"
        )
        print(f"Reason: {selected.reason}")
        print(f"Manifest: {run_dir / 'manifest.json'}")
        return 0

    if selected.trigger_level == 1 and not args.force_build:
        manifest["status"] = "soft_alert_only"
        _write_manifest(run_dir / "manifest.json", manifest)
        print("Latest decision is Level 1 soft alert. Use --force-build to build anyway.")
        print(f"Manifest: {run_dir / 'manifest.json'}")
        return 0

    if live_config.pipeline == "official_pyterrier_dense" and selected.trigger_level < 3 and not args.force_build:
        manifest["status"] = "dense_build_skipped_level_below_3"
        _write_manifest(run_dir / "manifest.json", manifest)
        print("Dense Qwen index rebuild is Level 3 only. Use --force-build to override.")
        print(f"Manifest: {run_dir / 'manifest.json'}")
        return 0

    use_incremental = selected.action == "incremental_reindex" and not args.full_rebuild
    manifest["status"] = "building_incremental_shadow" if use_incremental else "building_shadow"
    _write_manifest(run_dir / "manifest.json", manifest)
    if use_incremental:
        print(f"Building incremental shadow index under {shadow_index_root}")
        manifest["incremental_reindex"] = _build_incremental_shadow(live_config, shadow_config, selected, args, run_dir)
        manifest["status"] = "incremental_shadow_built"
    else:
        print(f"Building shadow index under {shadow_index_root}")
        build_required_indices(shadow_config)
        manifest["status"] = "shadow_built"

    if args.promote:
        print("Promoting shadow index to live canonical index paths")
        manifest["promotion"] = _promote_shadow_indexes(shadow_config, live_config)
        manifest["status"] = "promoted"

    _write_manifest(run_dir / "manifest.json", manifest)
    print(f"Pipeline complete: {manifest['status']}")
    print(f"Manifest: {run_dir / 'manifest.json'}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive reindex pipeline.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--analytics-dir", default=str(DEFAULT_ANALYTICS_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--mode", choices=["plan", "build"], default="plan")
    parser.add_argument("--train-snapshot1", action="store_true", default=True)
    parser.add_argument("--qrels-variant", default="dctr", choices=["dctr", "raw"])
    parser.add_argument("--last-reindex-week", default=None)
    parser.add_argument("--rank-stability", default=None)
    parser.add_argument("--staleness-rate", type=float, default=0.15)
    parser.add_argument("--coverage-gap", type=float, default=0.05)
    parser.add_argument("--temporal-gap-growth-days", type=int, default=30)
    parser.add_argument("--velocity-multiplier", type=float, default=2.0)
    parser.add_argument("--baseline-weeks", type=int, default=4)
    parser.add_argument("--date-field", default="publishedDate")
    parser.add_argument("--full-rebuild", action="store_true", help="Use full shadow rebuild even for Level 2 triggers.")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run_pipeline(args))


if __name__ == "__main__":
    main()
