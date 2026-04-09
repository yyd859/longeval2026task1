"""Longitudinal reporting across snapshots and methods."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from longeval_sci.baselines.runner import BaselineRunResult
from longeval_sci.config import DEFAULT_METRICS, DEFAULT_SNAPSHOTS, baseline_reports_dir


def _pct_delta(new: float, old: float) -> float | None:
    if old == 0.0:
        return None
    return ((new - old) / old) * 100.0


def summarize_baseline(result: BaselineRunResult) -> dict[str, object]:
    """Summarize one baseline across snapshots with deltas."""
    payload: dict[str, object] = {
        "run_name": result.config.run_name,
        "pipeline": result.config.pipeline,
        "snapshots": [],
        "deltas": [],
    }
    snapshots_payload: list[dict[str, object]] = []
    snapshot_lookup: dict[str, dict[str, object]] = {}
    for snapshot in result.snapshots:
        row: dict[str, object] = {
            "snapshot_id": snapshot.snapshot_id,
            "dataset_name": snapshot.dataset_name,
            "execution_backend": snapshot.execution_backend,
            "run_path": str(snapshot.run_path),
            "metrics_path": str(snapshot.metrics_path),
        }
        if snapshot.metrics:
            row.update(snapshot.metrics)
        snapshots_payload.append(row)
        snapshot_lookup[snapshot.snapshot_id] = row

    comparisons = [("snapshot-2", "snapshot-1"), ("snapshot-3", "snapshot-2"), ("snapshot-3", "snapshot-1")]
    delta_rows: list[dict[str, object]] = []
    for newer, older in comparisons:
        if newer not in snapshot_lookup or older not in snapshot_lookup:
            continue
        delta_row: dict[str, object] = {"comparison": f"{newer}_vs_{older}"}
        for metric in DEFAULT_METRICS:
            if metric in snapshot_lookup[newer] and metric in snapshot_lookup[older]:
                new_value = float(snapshot_lookup[newer][metric])
                old_value = float(snapshot_lookup[older][metric])
                delta_row[f"{metric}_abs"] = new_value - old_value
                delta_row[f"{metric}_pct"] = _pct_delta(new_value, old_value)
        delta_rows.append(delta_row)

    payload["snapshots"] = snapshots_payload
    payload["deltas"] = delta_rows
    return payload


def build_method_snapshot_rows(results: list[BaselineRunResult]) -> list[dict[str, object]]:
    """Flatten baseline results into one row per method and snapshot."""
    rows: list[dict[str, object]] = []
    for result in results:
        for snapshot in result.snapshots:
            row: dict[str, object] = {
                "method": result.config.run_name,
                "pipeline": result.config.pipeline,
                "snapshot": snapshot.snapshot_id,
                "execution_backend": snapshot.execution_backend,
            }
            if snapshot.metrics:
                row.update(snapshot.metrics)
            rows.append(row)
    return rows


def write_longitudinal_outputs(results: list[BaselineRunResult], output_dir: str | Path) -> dict[str, str]:
    """Write JSON, CSV, Markdown, and HTML outputs for all methods across snapshots."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    baseline_payloads = [summarize_baseline(result) for result in results]
    rows = build_method_snapshot_rows(results)

    json_path = root / "longitudinal_report.json"
    csv_path = root / "method_snapshot_metrics.csv"
    md_path = root / "comparison_table.md"
    html_path = root / "comparison_table.html"

    json_path.write_text(json.dumps({"baselines": baseline_payloads, "rows": rows}, indent=2), encoding="utf-8")

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    metric_order = list(DEFAULT_METRICS)
    methods = [result.config.run_name for result in results]
    lookup: dict[tuple[str, str], dict[str, object]] = {(row["method"], row["snapshot"]): row for row in rows}

    md_lines = [
        "# LongEval-Sci Baseline Comparison",
        "",
        "| Method | Backend | nDCG@10 S1 | nDCG@10 S2 | nDCG@10 S3 | nDCG@1000 S1 | nDCG@1000 S2 | nDCG@1000 S3 | MAP S1 | MAP S2 | MAP S3 | Recall@100 S1 | Recall@100 S2 | Recall@100 S3 | Recall@1000 S1 | Recall@1000 S2 | Recall@1000 S3 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method in methods:
        backend = next((lookup[(method, snapshot)]["execution_backend"] for snapshot in DEFAULT_SNAPSHOTS if (method, snapshot) in lookup), "")
        values: list[str] = []
        for metric in metric_order:
            for snapshot in DEFAULT_SNAPSHOTS:
                row = lookup.get((method, snapshot), {})
                value = row.get(metric, "")
                values.append(f"{float(value):.4f}" if isinstance(value, (int, float)) else "")
        md_lines.append(f"| {method} | {backend} | " + " | ".join(values) + " |")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    html_lines = [
        "<html><head><meta charset='utf-8'><style>",
        "body { font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { border: 1px solid #d1d5db; padding: 8px 10px; text-align: center; }",
        "thead th { background: #eff6ff; }",
        "tbody tr:nth-child(even) { background: #f9fafb; }",
        ".method { text-align: left; font-weight: 600; }",
        "</style></head><body>",
        "<h1>LongEval-Sci Baseline Comparison</h1>",
        "<table>",
        "<thead>",
        "<tr><th rowspan='2'>Method</th><th rowspan='2'>Backend</th>",
    ]
    for metric in metric_order:
        label = metric.replace("ndcg_cut_", "nDCG@").replace("recall_", "Recall@").upper().replace("MAP", "MAP")
        if metric.startswith("ndcg_cut_"):
            label = metric.replace("ndcg_cut_", "nDCG@")
        elif metric.startswith("recall_"):
            label = metric.replace("recall_", "Recall@")
        html_lines.append(f"<th colspan='3'>{label}</th>")
    html_lines.append("</tr><tr>")
    for _metric in metric_order:
        for snapshot in DEFAULT_SNAPSHOTS:
            html_lines.append(f"<th>{snapshot}</th>")
    html_lines.append("</tr></thead><tbody>")
    for method in methods:
        backend = next((lookup[(method, snapshot)]["execution_backend"] for snapshot in DEFAULT_SNAPSHOTS if (method, snapshot) in lookup), "")
        html_lines.append(f"<tr><td class='method'>{method}</td><td>{backend}</td>")
        for metric in metric_order:
            for snapshot in DEFAULT_SNAPSHOTS:
                row = lookup.get((method, snapshot), {})
                value = row.get(metric, "")
                html_lines.append(f"<td>{float(value):.4f}</td>" if isinstance(value, (int, float)) else "<td></td>")
        html_lines.append("</tr>")
    html_lines.append("</tbody></table></body></html>")
    html_path.write_text("".join(html_lines), encoding="utf-8")

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "markdown": str(md_path),
        "html": str(html_path),
    }
