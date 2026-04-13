"""Aggregate monthly split outputs across models into one comparison report."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)


def _write_markdown(rows: list[dict[str, object]], path: Path) -> None:
    lines = [
        "# Monthly Split Comparison",
        "",
        "| Model | Split | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {model} | {split_name} | {months} | {query_count} | {doc_count} | "
            "{ndcg_cut_10:.4f} | {ndcg_cut_1000:.4f} | {map:.4f} | {recall_100:.4f} | {recall_1000:.4f} |".format(
                **{
                    **row,
                    "ndcg_cut_10": float(row.get("ndcg_cut_10", 0.0)),
                    "ndcg_cut_1000": float(row.get("ndcg_cut_1000", 0.0)),
                    "map": float(row.get("map", 0.0)),
                    "recall_100": float(row.get("recall_100", 0.0)),
                    "recall_1000": float(row.get("recall_1000", 0.0)),
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a cross-model monthly split comparison report.")
    parser.add_argument(
        "--input-root",
        default="outputs/reports/monthly_split",
        help="Root directory containing per-model monthly split outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/reports/monthly_split/_summary",
        help="Directory for the aggregated monthly comparison outputs.",
    )
    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_dir = Path(args.output_dir)
    rows: list[dict[str, object]] = []

    for model_dir in sorted(path for path in input_root.iterdir() if path.is_dir() and not path.name.startswith("_")):
        metrics_path = model_dir / "monthly_split_metrics.csv"
        if not metrics_path.exists():
            continue
        for row in _read_csv(metrics_path):
            rows.append(
                {
                    "model": model_dir.name,
                    "split_name": row["split_name"],
                    "date_field": row["date_field"],
                    "months": row["months"],
                    "query_count": int(row["query_count"]),
                    "doc_count": int(row["doc_count"]),
                    "ndcg_cut_10": float(row["ndcg_cut_10"]),
                    "ndcg_cut_1000": float(row["ndcg_cut_1000"]),
                    "map": float(row["map"]),
                    "recall_100": float(row["recall_100"]),
                    "recall_1000": float(row["recall_1000"]),
                }
            )

    if not rows:
        raise SystemExit("No monthly split outputs found to summarize.")

    rows.sort(key=lambda row: (str(row["split_name"]), -float(row["ndcg_cut_10"]), str(row["model"])))
    _write_csv(rows, output_dir / "monthly_comparison.csv")
    _write_json(rows, output_dir / "monthly_comparison.json")
    _write_markdown(rows, output_dir / "monthly_comparison.md")

    print(f"csv: {output_dir / 'monthly_comparison.csv'}")
    print(f"json: {output_dir / 'monthly_comparison.json'}")
    print(f"markdown: {output_dir / 'monthly_comparison.md'}")


if __name__ == "__main__":
    main()
