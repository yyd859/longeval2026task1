"""Temporal reranking overlay."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from longeval_sci.config import ExperimentConfig
from longeval_sci.io.dataset import DatasetBundle, Document, Query, SearchResult
from longeval_sci.temporal.cluster import lookup_cluster_hints
from longeval_sci.temporal.features import compute_temporal_features, resolve_evaluation_time
from longeval_sci.temporal.history import lookup_historical_hints
from longeval_sci.temporal.intent import TemporalIntentPrediction, classify_temporal_intent


@dataclass(slots=True)
class TemporalScoreBreakdown:
    doc_id: str
    base_score: float
    temporal_score: float
    final_score: float
    intent_label: str


def _normalize_scores(results: list[SearchResult]) -> dict[str, float]:
    if not results:
        return {}
    scores = [result.score for result in results]
    max_score = max(scores)
    min_score = min(scores)
    if max_score == min_score:
        return {result.doc_id: 1.0 for result in results}
    scale = max_score - min_score
    return {result.doc_id: (result.score - min_score) / scale for result in results}


def _intent_weights(config: ExperimentConfig, intent: TemporalIntentPrediction) -> dict[str, float]:
    base = {
        "base": config.temporal.base_weight,
        "recency": config.temporal.recency_weight,
        "update": config.temporal.update_weight,
        "foundation": config.temporal.foundation_weight,
        "novelty": config.temporal.novelty_weight,
    }
    label = intent.label
    if label == "current":
        base["recency"] *= 1.6
        base["update"] *= 1.5
        base["foundation"] *= -0.35
        base["novelty"] *= 1.2
    elif label == "foundational":
        base["recency"] *= -0.25
        base["update"] *= -0.25
        base["foundation"] *= 1.8
        base["novelty"] *= 0.3
    elif label == "evolving":
        base["recency"] *= 1.1
        base["update"] *= 1.1
        base["foundation"] *= 0.8
        base["novelty"] *= 1.3
    elif label == "survey":
        base["recency"] *= 0.3
        base["update"] *= 0.3
        base["foundation"] *= 1.1
        base["novelty"] *= 0.5
    return base


def temporal_rerank_results(
    *,
    results: list[SearchResult],
    bundle: DatasetBundle,
    config: ExperimentConfig,
    progress_callback: Callable[[str, int, int, str], None] | None = None,
) -> list[SearchResult]:
    if not config.temporal.enabled:
        return results

    evaluation_time = resolve_evaluation_time(bundle, config.temporal)
    doc_lookup: dict[str, Document] = {document.doc_id: document for document in bundle.documents}
    query_lookup: dict[str, Query] = {query.query_id: query for query in bundle.queries}
    grouped: dict[str, list[SearchResult]] = defaultdict(list)
    for result in results:
        grouped[result.query_id].append(result)

    reranked_all: list[SearchResult] = []
    total_queries = len(query_lookup)
    for index, query in enumerate(bundle.queries, start=1):
        query_results = sorted(grouped.get(query.query_id, []), key=lambda item: item.rank)
        if not query_results:
            continue
        if progress_callback is not None:
            progress_callback(
                "temporal_reranking",
                index - 1,
                total_queries,
                f"Applying temporal overlay to query {index}/{total_queries}.",
            )

        rerank_depth = min(config.temporal.rerank_top_k, len(query_results))
        head = query_results[:rerank_depth]
        tail = query_results[rerank_depth:]
        normalized = _normalize_scores(head)
        intent = classify_temporal_intent(query.text) if config.temporal.use_query_intent else TemporalIntentPrediction(
            label="evolving",
            scores={"evolving": 1.0},
        )
        weights = _intent_weights(config, intent)
        historical_hints = lookup_historical_hints(query.text) if config.temporal.use_history else None
        cluster_hints = lookup_cluster_hints(query.text) if config.temporal.use_cluster_fallback else None

        scored: list[tuple[SearchResult, float]] = []
        for result in head:
            document = doc_lookup.get(result.doc_id)
            if document is None:
                scored.append((result, normalized.get(result.doc_id, 0.0)))
                continue
            features = compute_temporal_features(
                document,
                query_text=query.text,
                evaluation_time=evaluation_time,
                config=config.temporal,
                text_mode=config.retrieval.text_mode,
            )
            final_score = (
                weights["base"] * normalized.get(result.doc_id, 0.0)
                + weights["recency"] * features.recency_score
                + weights["update"] * features.update_score
                + weights["foundation"] * features.foundation_score
                + weights["novelty"] * features.novelty_score
            )
            if historical_hints is not None and result.doc_id in historical_hints.prior_docs:
                final_score += config.temporal.history_boost
            if cluster_hints is not None and result.doc_id in cluster_hints.prior_docs:
                final_score += config.temporal.cluster_boost
            scored.append((result, final_score))

        ranked_head = sorted(scored, key=lambda item: item[1], reverse=True)
        reranked_head = [
            SearchResult(
                query_id=result.query_id,
                doc_id=result.doc_id,
                score=float(final_score),
                rank=0,
                run_name=result.run_name,
            )
            for result, final_score in ranked_head
        ]
        tail_results = [
            SearchResult(
                query_id=result.query_id,
                doc_id=result.doc_id,
                score=result.score,
                rank=0,
                run_name=result.run_name,
            )
            for result in tail
        ]
        combined = reranked_head + tail_results
        reranked_all.extend(
            SearchResult(
                query_id=result.query_id,
                doc_id=result.doc_id,
                score=result.score,
                rank=rank,
                run_name=result.run_name,
            )
            for rank, result in enumerate(combined[: config.retrieval.top_k], start=1)
        )
        if progress_callback is not None:
            progress_callback(
                "temporal_reranking",
                index,
                total_queries,
                f"Finished temporal overlay for query {index}/{total_queries} ({intent.label}).",
            )
    return reranked_all
