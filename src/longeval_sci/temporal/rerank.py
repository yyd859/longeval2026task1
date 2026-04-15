"""Temporal reranking overlay."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log1p
from typing import Callable

from longeval_sci.config import ExperimentConfig
from longeval_sci.io.dataset import DatasetBundle, Document, Query, SearchResult
from longeval_sci.temporal.citations import CitationTemporalFeatures, load_or_build_citation_feature_cache
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
        "citation_total": config.temporal.citation_total_weight,
        "citation_recent": config.temporal.citation_recent_weight,
        "citation_foundation": config.temporal.citation_foundation_weight,
        "citation_emerging": config.temporal.citation_emerging_weight,
        "citation_outbound": config.temporal.citation_outbound_weight,
    }
    label = intent.label
    if label == "current":
        base["recency"] *= 1.6
        base["update"] *= 1.5
        base["foundation"] *= -0.35
        base["novelty"] *= 1.2
        base["citation_total"] *= 0.45
        base["citation_recent"] *= 1.6
        base["citation_foundation"] *= 0.35
        base["citation_emerging"] *= 1.6
        base["citation_outbound"] *= 0.5
    elif label == "foundational":
        base["recency"] *= -0.25
        base["update"] *= -0.25
        base["foundation"] *= 1.8
        base["novelty"] *= 0.3
        base["citation_total"] *= 1.4
        base["citation_recent"] *= 0.35
        base["citation_foundation"] *= 1.7
        base["citation_emerging"] *= 0.35
        base["citation_outbound"] *= 0.9
    elif label == "evolving":
        base["recency"] *= 1.1
        base["update"] *= 1.1
        base["foundation"] *= 0.8
        base["novelty"] *= 1.3
        base["citation_total"] *= 0.9
        base["citation_recent"] *= 1.15
        base["citation_foundation"] *= 0.85
        base["citation_emerging"] *= 1.25
        base["citation_outbound"] *= 0.7
    elif label == "survey":
        base["recency"] *= 0.3
        base["update"] *= 0.3
        base["foundation"] *= 1.1
        base["novelty"] *= 0.5
        base["citation_total"] *= 1.25
        base["citation_recent"] *= 0.55
        base["citation_foundation"] *= 1.2
        base["citation_emerging"] *= 0.45
        base["citation_outbound"] *= 1.1
    return base


def _normalize_named_values(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    numeric_values = list(values.values())
    max_value = max(numeric_values)
    min_value = min(numeric_values)
    if max_value == min_value:
        return {key: 1.0 if max_value > 0 else 0.0 for key in values}
    scale = max_value - min_value
    return {key: (value - min_value) / scale for key, value in values.items()}


def _citation_signal_bundle(feature: CitationTemporalFeatures | None) -> dict[str, float]:
    if feature is None:
        return {
            "citation_total": 0.0,
            "citation_recent": 0.0,
            "citation_foundation": 0.0,
            "citation_emerging": 0.0,
            "citation_outbound": 0.0,
        }
    total_inbound = max(feature.nonself_inbound_citations, feature.total_inbound_citations)
    recent_inbound = max(feature.nonself_recent_inbound_citations, feature.recent_inbound_citations)
    return {
        "citation_total": log1p(total_inbound),
        "citation_recent": log1p(recent_inbound),
        "citation_foundation": feature.foundational_signal,
        "citation_emerging": feature.emerging_signal,
        "citation_outbound": log1p(feature.total_outbound_citations),
    }


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

    citation_lookup: dict[str, CitationTemporalFeatures] = {}
    if config.temporal.use_citation_features and config.temporal.citation_network_path:
        candidate_doc_ids: set[str] = set()
        for query_results in grouped.values():
            ranked = sorted(query_results, key=lambda item: item.rank)
            for result in ranked[: config.temporal.rerank_top_k]:
                candidate_doc_ids.add(result.doc_id)
        if progress_callback is not None:
            progress_callback(
                "citation_features",
                0,
                len(candidate_doc_ids),
                f"Building citation features for {len(candidate_doc_ids)} candidate documents.",
            )
        citation_lookup = load_or_build_citation_feature_cache(
            config.temporal.citation_network_path,
            cutoff=evaluation_time,
            allowed_doc_ids=candidate_doc_ids,
            recent_window_days=config.temporal.citation_recent_window_days,
            exclude_self_citations=config.temporal.exclude_self_citations,
            cache_root=config.temporal.citation_cache_root,
        )
        if progress_callback is not None:
            progress_callback(
                "citation_features",
                len(candidate_doc_ids),
                len(candidate_doc_ids),
                f"Loaded citation features for {len(citation_lookup)} candidate documents.",
            )

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

        per_doc_temporal = {}
        per_doc_citation = {}
        for result in head:
            document = doc_lookup.get(result.doc_id)
            if document is None:
                continue
            per_doc_temporal[result.doc_id] = compute_temporal_features(
                document,
                query_text=query.text,
                evaluation_time=evaluation_time,
                config=config.temporal,
                text_mode=config.retrieval.text_mode,
            )
            per_doc_citation[result.doc_id] = _citation_signal_bundle(citation_lookup.get(result.doc_id))

        normalized_citation_components = {
            key: _normalize_named_values({doc_id: values[key] for doc_id, values in per_doc_citation.items()})
            for key in ("citation_total", "citation_recent", "citation_foundation", "citation_emerging", "citation_outbound")
        }

        scored: list[tuple[SearchResult, float]] = []
        for result in head:
            document = doc_lookup.get(result.doc_id)
            if document is None:
                scored.append((result, normalized.get(result.doc_id, 0.0)))
                continue
            features = per_doc_temporal[result.doc_id]
            final_score = (
                weights["base"] * normalized.get(result.doc_id, 0.0)
                + weights["recency"] * features.recency_score
                + weights["update"] * features.update_score
                + weights["foundation"] * features.foundation_score
                + weights["novelty"] * features.novelty_score
                + weights["citation_total"] * normalized_citation_components["citation_total"].get(result.doc_id, 0.0)
                + weights["citation_recent"] * normalized_citation_components["citation_recent"].get(result.doc_id, 0.0)
                + weights["citation_foundation"] * normalized_citation_components["citation_foundation"].get(result.doc_id, 0.0)
                + weights["citation_emerging"] * normalized_citation_components["citation_emerging"].get(result.doc_id, 0.0)
                + weights["citation_outbound"] * normalized_citation_components["citation_outbound"].get(result.doc_id, 0.0)
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
