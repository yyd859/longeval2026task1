"""Lightweight placeholders for future cluster-based temporal transfer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ClusterHints:
    similar_queries: list[str] = field(default_factory=list)
    prior_docs: list[str] = field(default_factory=list)
    similarity: float = 0.0


def lookup_cluster_hints(query_text: str) -> ClusterHints:
    """Return a placeholder cluster object for future Run 2 work."""
    _ = query_text
    return ClusterHints()
