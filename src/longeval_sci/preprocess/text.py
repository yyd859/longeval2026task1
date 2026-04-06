"""Text normalization helpers."""

from __future__ import annotations


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace while preserving token boundaries."""
    return " ".join(text.split())
