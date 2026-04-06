"""Built-in ranking metrics for fallback evaluation."""

from __future__ import annotations

import math


def dcg_at_k(relevances: list[int], k: int) -> float:
    """Compute discounted cumulative gain at k."""
    score = 0.0
    for rank, rel in enumerate(relevances[:k], start=1):
        score += (2**rel - 1) / math.log2(rank + 1)
    return score


def ndcg_at_k(qrels: dict[str, int], ranked_doc_ids: list[str], k: int) -> float:
    """Compute nDCG@k."""
    actual = [qrels.get(doc_id, 0) for doc_id in ranked_doc_ids[:k]]
    ideal = sorted(qrels.values(), reverse=True)
    ideal_score = dcg_at_k(ideal, k)
    if ideal_score == 0.0:
        return 0.0
    return dcg_at_k(actual, k) / ideal_score


def average_precision(qrels: dict[str, int], ranked_doc_ids: list[str]) -> float:
    """Compute average precision using relevance > 0."""
    relevant_total = sum(1 for rel in qrels.values() if rel > 0)
    if relevant_total == 0:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for rank, doc_id in enumerate(ranked_doc_ids, start=1):
        if qrels.get(doc_id, 0) > 0:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / relevant_total


def recall_at_k(qrels: dict[str, int], ranked_doc_ids: list[str], k: int) -> float:
    """Compute recall@k using relevance > 0."""
    relevant_docs = {doc_id for doc_id, rel in qrels.items() if rel > 0}
    if not relevant_docs:
        return 0.0
    retrieved = set(ranked_doc_ids[:k])
    return len(retrieved & relevant_docs) / len(relevant_docs)


def reciprocal_rank_at_k(qrels: dict[str, int], ranked_doc_ids: list[str], k: int) -> float:
    """Compute reciprocal rank at k."""
    for rank, doc_id in enumerate(ranked_doc_ids[:k], start=1):
        if qrels.get(doc_id, 0) > 0:
            return 1.0 / rank
    return 0.0
