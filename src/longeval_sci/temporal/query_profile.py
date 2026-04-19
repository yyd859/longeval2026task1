"""Query-side evidence profile for temporal and citation routing."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from math import log
import re

from longeval_sci.config import TemporalConfig
from longeval_sci.io.dataset import Document, SearchResult
from longeval_sci.temporal.citations import CitationTemporalFeatures


_TEMPORAL_TERMS = {
    "latest",
    "recent",
    "current",
    "new",
    "newest",
    "updated",
    "update",
    "modern",
    "emerging",
    "trend",
    "trends",
    "progress",
}
_CITATION_TERMS = {
    "seminal",
    "classic",
    "foundational",
    "influential",
    "impactful",
    "citation",
    "citations",
    "cited",
    "survey",
    "review",
    "benchmark",
}
_TEMPORAL_PHRASES = ("this year", "last year", "state of the art", "state-of-the-art")
_CITATION_PHRASES = ("highly cited", "well cited", "most cited")


@dataclass(slots=True)
class QueryEvidenceProfile:
    explicit_temporal: bool
    explicit_citation: bool
    temporal_entropy: float | None
    high_citation_share: float
    publication_year_span: int | None
    old_doc_share: float
    temporal_alpha: float
    citation_beta: float


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text.lower()))


def has_explicit_temporal_cue(query_text: str) -> bool:
    tokens = _tokenize(query_text)
    text = query_text.lower()
    return (
        bool(tokens & _TEMPORAL_TERMS)
        or any(phrase in text for phrase in _TEMPORAL_PHRASES)
        or bool(re.search(r"\b20(2[4-9]|3[0-9])\b", text))
        or bool(re.search(r"\b\d{4}-\d{1,2}(?:-\d{1,2})?\b", text))
    )


def has_explicit_citation_cue(query_text: str) -> bool:
    tokens = _tokenize(query_text)
    text = query_text.lower()
    return bool(tokens & _CITATION_TERMS) or any(phrase in text for phrase in _CITATION_PHRASES)


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in (None, "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00")) if fmt is None else datetime.strptime(text, fmt)
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _document_year(document: Document) -> int | None:
    for field in ("publishedDate", "createdDate", "updatedDate"):
        parsed = _parse_datetime(document.metadata.get(field))
        if parsed is not None:
            return parsed.year
    return None


def _normalized_entropy(values: list[int]) -> float | None:
    if not values:
        return None
    counts = Counter(values)
    if len(counts) <= 1:
        return 0.0
    total = float(sum(counts.values()))
    entropy = -sum((count / total) * log(count / total) for count in counts.values())
    return entropy / log(len(counts))


def _citation_count(feature: CitationTemporalFeatures | None) -> int:
    if feature is None:
        return 0
    return max(feature.nonself_inbound_citations, feature.total_inbound_citations)


def build_query_evidence_profile(
    *,
    query_text: str,
    ranked_results: list[SearchResult],
    doc_lookup: dict[str, Document],
    citation_lookup: dict[str, CitationTemporalFeatures],
    config: TemporalConfig,
) -> QueryEvidenceProfile:
    top_k = max(config.query_profile_top_k, 1)
    top_results = ranked_results[:top_k]
    top_documents = [doc_lookup[result.doc_id] for result in top_results if result.doc_id in doc_lookup]
    years = [year for document in top_documents if (year := _document_year(document)) is not None]
    temporal_entropy = _normalized_entropy(years)
    publication_year_span = (max(years) - min(years)) if years else None
    old_doc_share = 0.0
    if years:
        old_cutoff = max(years) - max(config.query_profile_old_doc_window_years, 1)
        old_doc_share = sum(1 for year in years if year <= old_cutoff) / len(years)

    explicit_temporal = has_explicit_temporal_cue(query_text)
    explicit_citation = has_explicit_citation_cue(query_text)

    if top_results:
        high_citation_docs = sum(
            1
            for result in top_results
            if _citation_count(citation_lookup.get(result.doc_id)) >= config.query_profile_high_citation_count_threshold
        )
        high_citation_share = high_citation_docs / len(top_results)
    else:
        high_citation_share = 0.0

    if explicit_temporal:
        temporal_alpha = config.query_profile_temporal_alpha_explicit
    elif temporal_entropy is not None and temporal_entropy <= config.query_profile_temporal_entropy_threshold:
        temporal_alpha = config.query_profile_temporal_alpha_concentrated
    else:
        temporal_alpha = config.query_profile_temporal_alpha_default

    if explicit_citation:
        citation_beta = config.query_profile_citation_beta_explicit
    elif high_citation_share >= config.query_profile_high_citation_share_threshold or (
        publication_year_span is not None
        and publication_year_span >= config.query_profile_year_span_threshold
        and old_doc_share >= config.query_profile_old_doc_share_threshold
    ):
        citation_beta = config.query_profile_citation_beta_high_share
    else:
        citation_beta = config.query_profile_citation_beta_default

    return QueryEvidenceProfile(
        explicit_temporal=explicit_temporal,
        explicit_citation=explicit_citation,
        temporal_entropy=temporal_entropy,
        high_citation_share=high_citation_share,
        publication_year_span=publication_year_span,
        old_doc_share=old_doc_share,
        temporal_alpha=temporal_alpha,
        citation_beta=citation_beta,
    )
