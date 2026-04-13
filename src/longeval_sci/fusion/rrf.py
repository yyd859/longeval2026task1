"""Reciprocal Rank Fusion over existing run outputs."""

from __future__ import annotations

from collections import defaultdict

from longeval_sci.io.dataset import SearchResult


def _ensure_ranked(results: list[SearchResult]) -> list[SearchResult]:
    grouped: dict[str, list[SearchResult]] = defaultdict(list)
    for result in results:
        grouped[result.query_id].append(result)

    ranked: list[SearchResult] = []
    for query_id, query_results in grouped.items():
        sorted_results = sorted(
            query_results,
            key=lambda item: (item.rank if item.rank > 0 else 10**9, -item.score, item.doc_id),
        )
        ranked.extend(
            SearchResult(
                query_id=query_id,
                doc_id=result.doc_id,
                score=result.score,
                rank=rank,
                run_name=result.run_name,
            )
            for rank, result in enumerate(sorted_results, start=1)
        )
    return ranked


def rrf_fuse(
    runs: list[list[SearchResult]],
    *,
    k: int = 60,
    top_k: int = 1000,
    run_name: str = "rrf",
) -> list[SearchResult]:
    """Fuse multiple run outputs with Reciprocal Rank Fusion."""
    fused_by_query: dict[str, dict[str, float]] = defaultdict(dict)

    for run in runs:
        for result in _ensure_ranked(run):
            fused_by_query[result.query_id].setdefault(result.doc_id, 0.0)
            fused_by_query[result.query_id][result.doc_id] += 1.0 / (k + result.rank)

    fused_results: list[SearchResult] = []
    for query_id, doc_scores in fused_by_query.items():
        ranked = sorted(doc_scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]
        fused_results.extend(
            SearchResult(
                query_id=query_id,
                doc_id=doc_id,
                score=float(score),
                rank=rank,
                run_name=run_name,
            )
            for rank, (doc_id, score) in enumerate(ranked, start=1)
        )
    return fused_results
