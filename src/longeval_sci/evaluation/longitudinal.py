"""Longitudinal evaluation across LongEval snapshots."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from longeval_sci.config import DEFAULT_SNAPSHOTS, DatasetConfig
from longeval_sci.evaluation.run_eval import evaluate_run


DEFAULT_METRICS = ["ndcg_cut_10", "map", "recall_100", "recall_1000"]


def _percent_delta(new: float, old: float) -> float | None:
    if old == 0:
        return None
    return ((new - old) / old) * 100.0


def evaluate_longitudinal_runs(
    runs_dir: str,
    dataset_prefix: str = "longeval-sci-2026",
    qrels_variant: str = "dctr",
    metrics: list[str] | None = None,
) -> dict[str, object]:
    """Evaluate run files across snapshot-1/2/3 and compute deltas."""
    metric_names = metrics or DEFAULT_METRICS
    runs_root = Path(runs_dir)
    snapshots: list[dict[str, object]] = []

    for snapshot_id in DEFAULT_SNAPSHOTS:
        run_candidates = [runs_root / snapshot_id / "run.txt", runs_root / snapshot_id / "run.txt.gz"]
        run_path = next((path for path in run_candidates if path.exists()), None)
        dataset_config = DatasetConfig(
            backend="ir_datasets_longeval",
            dataset_name=f"{dataset_prefix}/{snapshot_id}",
            snapshot_id=snapshot_id,
            qrels_variant=qrels_variant,
        )

        row: dict[str, object] = {"snapshot": snapshot_id, "run_path": str(run_path) if run_path else "", "status": "ok"}
        if run_path is None:
            row["status"] = "missing_run"
            snapshots.append(row)
            continue

        try:
            aggregate = evaluate_run(dataset_config=dataset_config, run_path=str(run_path), metrics=metric_names)
            row.update(aggregate)
        except Exception as exc:
            row["status"] = f"skipped: {exc}"
        snapshots.append(row)

    deltas: list[dict[str, object]] = []
    valid_rows = {row["snapshot"]: row for row in snapshots if row.get("status") == "ok"}
    comparisons = [("delta_2_vs_1", "snapshot-2", "snapshot-1"), ("delta_3_vs_2", "snapshot-3", "snapshot-2"), ("delta_3_vs_1", "snapshot-3", "snapshot-1")]
    for label, newer, older in comparisons:
        row: dict[str, object] = {"snapshot": label}
        newer_row = valid_rows.get(newer)
        older_row = valid_rows.get(older)
        if not newer_row or not older_row:
            row["status"] = "skipped"
            deltas.append(row)
            continue
        row["status"] = "ok"
        for metric in metric_names:
            new_value = float(newer_row[metric])
            old_value = float(older_row[metric])
            row[f"{metric}_abs"] = new_value - old_value
            row[f"{metric}_pct"] = _percent_delta(new_value, old_value)
        deltas.append(row)

    payload = {"snapshots": snapshots, "deltas": deltas, "metrics": metric_names, "qrels_variant": qrels_variant}
    return payload


def write_longitudinal_reports(payload: dict[str, object], json_path: str, csv_path: str) -> None:
    """Persist the longitudinal summary as JSON and CSV."""
    json_output = Path(json_path)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    with json_output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)

    rows = [*payload["snapshots"], *payload["deltas"]]  # type: ignore[index]
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    csv_output = Path(csv_path)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
