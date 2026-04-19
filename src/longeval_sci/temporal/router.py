"""Query-level routing for temporal and citation evidence."""

from __future__ import annotations

import re

from longeval_sci.temporal.query_profile import has_explicit_citation_cue, has_explicit_temporal_cue


EVIDENCE_ROUTES = {"temporal", "citation", "mixed"}

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
_MIXED_TERMS = {
    "compare",
    "comparison",
    "comparative",
    "versus",
    "vs",
    "evolving",
    "evolution",
    "development",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text.lower()))


def classify_evidence_route(query_text: str) -> str:
    """Route a query to temporal, citation, or mixed evidence priority."""
    tokens = _tokenize(query_text)

    temporal_score = sum(1 for token in tokens if token in _TEMPORAL_TERMS)
    citation_score = sum(1 for token in tokens if token in _CITATION_TERMS)
    mixed_score = sum(1 for token in tokens if token in _MIXED_TERMS)

    if has_explicit_temporal_cue(query_text):
        temporal_score += 1
    if has_explicit_citation_cue(query_text):
        citation_score += 2

    if mixed_score > 0 or (temporal_score > 0 and citation_score > 0):
        return "mixed"
    if citation_score > 0:
        return "citation"
    return "temporal"
