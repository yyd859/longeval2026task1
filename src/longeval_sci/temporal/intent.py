"""Rule-based temporal intent classification."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
import re


@dataclass(slots=True)
class TemporalIntentPrediction:
    label: str
    scores: dict[str, float]


_FOUNDATIONAL_TERMS = {
    "overview",
    "background",
    "history",
    "historical",
    "introduction",
    "fundamentals",
    "foundational",
    "classic",
    "seminal",
    "survey",
    "tutorial",
    "review",
}
_CURRENT_TERMS = {
    "latest",
    "recent",
    "current",
    "new",
    "newest",
    "today",
    "state-of-the-art",
    "sota",
    "modern",
    "update",
    "updated",
}
_EVOLVING_TERMS = {
    "trend",
    "trends",
    "emerging",
    "evolving",
    "compare",
    "comparison",
    "comparative",
    "versus",
    "vs",
    "development",
    "progress",
}
_SURVEY_TERMS = {"survey", "review", "overview", "benchmark", "comparison", "comparative"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text.lower())


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    numerators = {label: exp(value - max_score) for label, value in scores.items()}
    denom = sum(numerators.values()) or 1.0
    return {label: value / denom for label, value in numerators.items()}


def classify_temporal_intent(query_text: str) -> TemporalIntentPrediction:
    tokens = _tokenize(query_text)
    token_set = set(tokens)
    text = query_text.lower()

    raw_scores = {
        "foundational": 0.2,
        "current": 0.2,
        "evolving": 0.2,
        "survey": 0.2,
    }

    raw_scores["foundational"] += sum(1.0 for token in token_set if token in _FOUNDATIONAL_TERMS)
    raw_scores["current"] += sum(1.0 for token in token_set if token in _CURRENT_TERMS)
    raw_scores["evolving"] += sum(1.0 for token in token_set if token in _EVOLVING_TERMS)
    raw_scores["survey"] += sum(1.0 for token in token_set if token in _SURVEY_TERMS)

    if "?" in query_text:
        raw_scores["survey"] += 0.1
    if any(year in text for year in ("2023", "2024", "2025", "2026")):
        raw_scores["current"] += 1.0
    if "state of the art" in text:
        raw_scores["current"] += 1.5
    if "how has" in text or "change" in text or "changed" in text:
        raw_scores["evolving"] += 1.0
    if any(token in token_set for token in {"survey", "overview", "review"}):
        raw_scores["survey"] += 1.2

    scores = _softmax(raw_scores)
    label = max(scores.items(), key=lambda item: item[1])[0]
    return TemporalIntentPrediction(label=label, scores=scores)
