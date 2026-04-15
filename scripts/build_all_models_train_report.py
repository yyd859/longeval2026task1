"""Build a snapshot-1 train comparison report across all current models."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval
from longeval_sci.config import DEFAULT_METRICS, load_config
from longeval_sci.evaluation.pytrec_eval_wrapper import evaluate_run_dict
from longeval_sci.io.dataset import load_qrels
from longeval_sci.io.trec import read_trec_run


METHODS = [
    ("official_pyterrier", "base", "outputs/official_pyterrier/snapshot-1-train/run.txt", "configs/official_pyterrier.yaml"),
    ("official_pyterrier_dense", "base", "outputs/official_pyterrier_dense/snapshot-1-train/run.txt", "configs/official_pyterrier_dense.yaml"),
    ("custom_lexical_fulltext", "base", "outputs/custom_lexical_fulltext/snapshot-1-train/run.txt", "configs/custom_lexical_fulltext.yaml"),
    ("custom_title_abstract_rm3", "base", "outputs/custom_title_abstract_rm3/snapshot-1-train/run.txt", "configs/custom_title_abstract_rm3.yaml"),
    ("custom_title_abstract_rerank", "base", "outputs/custom_title_abstract_rerank/snapshot-1-train/run.txt", "configs/custom_title_abstract_rerank.yaml"),
    ("official_pyterrier_temporal", "temporal", "outputs/official_pyterrier_temporal/snapshot-1-train/run.txt", "configs/official_pyterrier_temporal.yaml"),
    ("official_pyterrier_dense_temporal", "temporal", "outputs/official_pyterrier_dense_temporal/snapshot-1-train/run.txt", "configs/official_pyterrier_dense_temporal.yaml"),
    ("custom_lexical_fulltext_temporal", "temporal", "outputs/custom_lexical_fulltext_temporal/snapshot-1-train/run.txt", "configs/custom_lexical_fulltext_temporal.yaml"),
    ("custom_title_abstract_rm3_temporal", "temporal", "outputs/custom_title_abstract_rm3_temporal/snapshot-1-train/run.txt", "configs/custom_title_abstract_rm3_temporal.yaml"),
    ("custom_title_abstract_rerank_temporal", "temporal", "outputs/custom_title_abstract_rerank_temporal/snapshot-1-train/run.txt", "configs/custom_title_abstract_rerank_temporal.yaml"),
    ("official_pyterrier_temporal_citation", "temporal_citation", "outputs/official_pyterrier_temporal_citation/snapshot-1-train/run.txt", "configs/official_pyterrier_temporal_citation.yaml"),
    ("custom_lexical_fulltext_temporal_citation", "temporal_citation", "outputs/custom_lexical_fulltext_temporal_citation/snapshot-1-train/run.txt", "configs/custom_lexical_fulltext_temporal_citation.yaml"),
    ("custom_title_abstract_rerank_temporal_citation", "temporal_citation", "outputs/custom_title_abstract_rerank_temporal_citation/snapshot-1-train/run.txt", "configs/custom_title_abstract_rerank_temporal_citation.yaml"),
    ("rrf_bm25_ta_dense_ta", "fusion", "outputs/rrf_bm25_ta_dense_ta/snapshot-1-train/run.txt", "configs/base/rrf_bm25_ta_dense_ta.yaml"),
    ("rrf_bm25_ft_dense_ta", "fusion", "outputs/rrf_bm25_ft_dense_ta/snapshot-1-train/run.txt", "configs/base/rrf_bm25_ft_dense_ta.yaml"),
    ("rrf_bm25_ta_bm25_ft_dense_ta", "fusion", "outputs/rrf_bm25_ta_bm25_ft_dense_ta/snapshot-1-train/run.txt", "configs/base/rrf_bm25_ta_bm25_ft_dense_ta.yaml"),
]


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


def _write_summary(rows_by_variant: dict[str, list[dict[str, object]]], total_models: int) -> str:
    lines = [
        "# Snapshot-1 Train Comparison Across All Current Models",
        "",
        f"Total current models in this report: `{total_models}`",
        "",
        "Model families:",
        "- 5 base models",
        "- 5 temporal sibling models",
        "- 3 citation-aware temporal sibling models",
        "- 3 RRF fusion models",
        "",
    ]
    for variant in ("dctr", "raw"):
        rows = rows_by_variant[variant]
        title = "DCTR Results" if variant == "dctr" else "Raw Results"
        lines.extend(
            [
                f"## {title}",
                "",
                "| Method | Family | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in rows:
            lines.append(
                "| {method} | {family} | {ndcg_cut_10:.4f} | {ndcg_cut_1000:.4f} | {map:.4f} | {recall_100:.4f} | {recall_1000:.4f} |".format(
                    **row
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a snapshot-1 train report across all current models.")
    parser.add_argument("--report-dir", default="outputs/reports/all_models_train_snapshot1", help="Output report directory.")
    args = parser.parse_args()

    report_dir = ROOT / args.report_dir
    rows: list[dict[str, object]] = []
    for variant in ("dctr", "raw"):
        qrels = load_qrels(clone_for_train_eval(load_config("configs/official_pyterrier.yaml"), qrels_variant=variant).dataset, "snapshot-1")
        for method, family, run_path_text, config_path in METHODS:
            run_path = ROOT / run_path_text
            if not run_path.exists():
                continue
            run = read_trec_run(run_path)
            aggregate, _ = evaluate_run_dict(qrels, run, list(DEFAULT_METRICS))
            row: dict[str, object] = {
                "method": method,
                "family": family,
                "qrels_variant": variant,
                "run_path": str(run_path.relative_to(ROOT)),
            }
            row.update(aggregate)
            rows.append(row)

    rows.sort(key=lambda row: (str(row["qrels_variant"]), -float(row["ndcg_cut_10"]), str(row["method"])))
    rows_by_variant = {variant: [row for row in rows if row["qrels_variant"] == variant] for variant in ("dctr", "raw")}

    _write_csv(rows, report_dir / "comparison_all.csv")
    _write_json(rows, report_dir / "comparison_all.json")
    _write_csv(rows_by_variant["dctr"], report_dir / "comparison_dctr.csv")
    _write_csv(rows_by_variant["raw"], report_dir / "comparison_raw.csv")
    (report_dir / "summary.md").write_text(_write_summary(rows_by_variant, len({row["method"] for row in rows})), encoding="utf-8")
    print(report_dir / "summary.md")


if __name__ == "__main__":
    main()
