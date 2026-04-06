"""Evaluation wrapper with optional pytrec_eval support."""

from __future__ import annotations

from longeval_sci.evaluation.metrics import average_precision, ndcg_at_k, recall_at_k, reciprocal_rank_at_k


def _translate_metric_name(metric: str) -> tuple[str, int | None]:
    if metric == "map":
        return "map", None
    if metric.startswith("ndcg_cut_"):
        return "ndcg", int(metric.rsplit("_", maxsplit=1)[-1])
    if metric.startswith("recall_"):
        return "recall", int(metric.rsplit("_", maxsplit=1)[-1])
    if metric.startswith("recip_rank_cut_"):
        return "mrr", int(metric.rsplit("_", maxsplit=1)[-1])
    raise ValueError(f"Unsupported metric requested: {metric}")


def evaluate_run_dict(
    qrels: dict[str, dict[str, int]],
    run: dict[str, dict[str, float]],
    metrics: list[str],
) -> tuple[dict[str, float], list[dict[str, str | float]]]:
    """Evaluate a run and return aggregate plus per-query metrics."""
    try:
        import pytrec_eval

        evaluator = pytrec_eval.RelevanceEvaluator(qrels, set(metrics))
        per_query = evaluator.evaluate(run)
        per_query_rows: list[dict[str, str | float]] = []
        for query_id, values in per_query.items():
            row: dict[str, str | float] = {"query_id": query_id}
            row.update({metric: float(score) for metric, score in values.items()})
            per_query_rows.append(row)
        aggregate = {}
        for metric in metrics:
            aggregate[metric] = sum(float(values.get(metric, 0.0)) for values in per_query.values()) / max(len(per_query), 1)
        return aggregate, per_query_rows
    except ImportError:
        per_query_rows = []
        for query_id, query_qrels in qrels.items():
            ranked = sorted(run.get(query_id, {}).items(), key=lambda item: item[1], reverse=True)
            ranked_doc_ids = [doc_id for doc_id, _ in ranked]
            row: dict[str, str | float] = {"query_id": query_id}
            for metric in metrics:
                kind, cutoff = _translate_metric_name(metric)
                if kind == "map":
                    row[metric] = average_precision(query_qrels, ranked_doc_ids)
                elif kind == "ndcg":
                    row[metric] = ndcg_at_k(query_qrels, ranked_doc_ids, cutoff or 10)
                elif kind == "recall":
                    row[metric] = recall_at_k(query_qrels, ranked_doc_ids, cutoff or 100)
                elif kind == "mrr":
                    row[metric] = reciprocal_rank_at_k(query_qrels, ranked_doc_ids, cutoff or 10)
            per_query_rows.append(row)
        aggregate = {}
        for metric in metrics:
            aggregate[metric] = sum(float(row[metric]) for row in per_query_rows) / max(len(per_query_rows), 1)
        return aggregate, per_query_rows
