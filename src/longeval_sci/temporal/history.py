"""Lightweight placeholders for future historical transfer features."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class HistoricalHints:
    prior_docs: list[str] = field(default_factory=list)
    prior_terms: list[str] = field(default_factory=list)
    similarity: float = 0.0


def lookup_historical_hints(query_text: str) -> HistoricalHints:
    """Return a placeholder history object for future Run 2 work."""
    _ = query_text
    return HistoricalHints()
