"""Hybrid candidate generation utilities."""

from __future__ import annotations


def union_results(
    lexical_results: list[tuple[str, float]],
    dense_results: list[tuple[str, float]],
    top_k: int | None = None,
) -> list[str]:
    """Return candidate ids from a simple union of ranked lists."""
    seen: set[str] = set()
    merged: list[str] = []
    for result_list in (lexical_results, dense_results):
        for doc_id, _ in result_list:
            if doc_id not in seen:
                seen.add(doc_id)
                merged.append(doc_id)
    if top_k is not None:
        return merged[:top_k]
    return merged


def reciprocal_rank_fusion(
    lexical_results: list[tuple[str, float]],
    dense_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Optional RRF support for later ablations."""
    scores: dict[str, float] = {}
    for result_list in (lexical_results, dense_results):
        for rank, (doc_id, _) in enumerate(result_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
