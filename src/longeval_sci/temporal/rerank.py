"""Temporal reranking overlay."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log1p
from pathlib import Path
from typing import Callable

from longeval_sci.config import ExperimentConfig
from longeval_sci.io.dataset import DatasetBundle, Document, Query, SearchResult
from longeval_sci.temporal.citations import CitationTemporalFeatures, load_or_build_citation_feature_cache
from longeval_sci.temporal.cluster import lookup_cluster_hints
from longeval_sci.temporal.features import compute_temporal_features, resolve_evaluation_time
from longeval_sci.temporal.history import lookup_historical_hints
from longeval_sci.temporal.intent import TemporalIntentPrediction, classify_temporal_intent
from longeval_sci.temporal.query_profile import build_query_evidence_profile
from longeval_sci.temporal.router import classify_evidence_route


_CITATION_COMPONENT_KEYS = (
    "citation_total",
    "citation_recent",
    "citation_foundation",
    "citation_emerging",
    "citation_outbound",
)
_INTEGRATION_MODES = {"direct", "citation_only", "router", "additive"}


@dataclass(slots=True)
class TemporalScoreBreakdown:
    doc_id: str
    base_score: float
    temporal_score: float
    citation_score: float
    final_score: float
    intent_label: str
    evidence_route: str


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


def _integration_mode(config: ExperimentConfig) -> str:
    mode = config.temporal.integration_mode.lower().strip()
    if mode not in _INTEGRATION_MODES:
        raise ValueError(f"Unsupported temporal integration_mode: {config.temporal.integration_mode}")
    return mode


def _citation_features_requested(config: ExperimentConfig) -> bool:
    mode = _integration_mode(config)
    return config.temporal.use_citation_features or mode in {"citation_only", "router", "additive"}


def _load_citation_lookup(
    *,
    config: ExperimentConfig,
    evaluation_time,
    grouped: dict[str, list[SearchResult]],
    progress_callback: Callable[[str, int, int, str], None] | None,
) -> dict[str, CitationTemporalFeatures]:
    if not _citation_features_requested(config) or not config.temporal.citation_network_path:
        return {}

    citation_path = Path(config.temporal.citation_network_path)
    candidate_doc_ids: set[str] = set()
    for query_results in grouped.values():
        ranked = sorted(query_results, key=lambda item: item.rank)
        for result in ranked[: config.temporal.rerank_top_k]:
            candidate_doc_ids.add(result.doc_id)

    if not citation_path.exists():
        if progress_callback is not None:
            progress_callback(
                "citation_features",
                len(candidate_doc_ids),
                len(candidate_doc_ids),
                f"Citation file not found at {citation_path}; using zero citation scores.",
            )
        return {}

    if progress_callback is not None:
        progress_callback(
            "citation_features",
            0,
            len(candidate_doc_ids),
            f"Building citation features for {len(candidate_doc_ids)} candidate documents.",
        )
    citation_lookup = load_or_build_citation_feature_cache(
        citation_path,
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
    return citation_lookup


def _temporal_score(weights: dict[str, float], features) -> float:
    return (
        weights["recency"] * features.recency_score
        + weights["update"] * features.update_score
        + weights["foundation"] * features.foundation_score
        + weights["novelty"] * features.novelty_score
    )


def _citation_score(
    weights: dict[str, float],
    normalized_citation_components: dict[str, dict[str, float]],
    doc_id: str,
) -> float:
    return sum(
        weights[key] * normalized_citation_components[key].get(doc_id, 0.0)
        for key in _CITATION_COMPONENT_KEYS
    )


def _final_score(
    *,
    mode: str,
    route: str,
    relevance_score: float,
    temporal_score: float,
    citation_score: float,
) -> float:
    if mode == "citation_only":
        return relevance_score + citation_score
    if mode == "router":
        if route == "citation":
            return relevance_score + citation_score
        if route == "mixed":
            return relevance_score + temporal_score + citation_score
        return relevance_score + temporal_score
    return relevance_score + temporal_score + citation_score


def _overlay_enabled(config: ExperimentConfig, result: SearchResult, relevance_score: float) -> bool:
    if result.rank > config.temporal.overlay_candidate_k:
        return False
    return relevance_score >= config.temporal.overlay_relevance_threshold


def _route_with_profile(query_text: str, profile, config: ExperimentConfig) -> str:
    text_route = classify_evidence_route(query_text)
    temporal_signal = (
        profile.explicit_temporal
        or profile.temporal_alpha >= config.temporal.query_profile_temporal_alpha_concentrated
    )
    citation_signal = (
        profile.explicit_citation
        or profile.citation_beta >= config.temporal.query_profile_citation_beta_high_share
    )
    if temporal_signal and citation_signal:
        return "mixed"
    if citation_signal:
        return "citation"
    if temporal_signal:
        return "temporal"
    return text_route


def temporal_rerank_results(
    *,
    results: list[SearchResult],
    bundle: DatasetBundle,
    config: ExperimentConfig,
    progress_callback: Callable[[str, int, int, str], None] | None = None,
) -> list[SearchResult]:
    if not config.temporal.enabled:
        return results

    mode = _integration_mode(config)
    evaluation_time = resolve_evaluation_time(bundle, config.temporal)
    doc_lookup: dict[str, Document] = {document.doc_id: document for document in bundle.documents}
    query_lookup: dict[str, Query] = {query.query_id: query for query in bundle.queries}
    grouped: dict[str, list[SearchResult]] = defaultdict(list)
    for result in results:
        grouped[result.query_id].append(result)

    citation_lookup = _load_citation_lookup(
        config=config,
        evaluation_time=evaluation_time,
        grouped=grouped,
        progress_callback=progress_callback,
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
        query_profile = build_query_evidence_profile(
            query_text=query.text,
            ranked_results=query_results,
            doc_lookup=doc_lookup,
            citation_lookup=citation_lookup,
            config=config.temporal,
        )
        evidence_route = _route_with_profile(query.text, query_profile, config) if mode == "router" else mode
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
            for key in _CITATION_COMPONENT_KEYS
        }

        scored: list[tuple[SearchResult, float]] = []
        for result in head:
            document = doc_lookup.get(result.doc_id)
            if document is None:
                scored.append((result, normalized.get(result.doc_id, 0.0)))
                continue
            features = per_doc_temporal[result.doc_id]
            normalized_relevance = normalized.get(result.doc_id, 0.0)
            relevance_score = weights["base"] * normalized_relevance
            temporal_score = _temporal_score(weights, features)
            citation_score = _citation_score(weights, normalized_citation_components, result.doc_id)
            if historical_hints is not None and result.doc_id in historical_hints.prior_docs:
                temporal_score += config.temporal.history_boost
            if cluster_hints is not None and result.doc_id in cluster_hints.prior_docs:
                temporal_score += config.temporal.cluster_boost
            if mode in {"citation_only", "router", "additive"}:
                if _overlay_enabled(config, result, normalized_relevance):
                    temporal_score *= query_profile.temporal_alpha
                    citation_score *= query_profile.citation_beta
                else:
                    temporal_score = 0.0
                    citation_score = 0.0
            final_score = _final_score(
                mode=mode,
                route=evidence_route,
                relevance_score=relevance_score,
                temporal_score=temporal_score,
                citation_score=citation_score,
            )
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
                f"Finished temporal overlay for query {index}/{total_queries} ({intent.label}; {evidence_route}).",
            )
    return reranked_all
