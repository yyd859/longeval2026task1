"""Path helpers."""

from __future__ import annotations

from pathlib import Path


def ensure_parent(path: str | Path) -> Path:
    """Ensure the parent directory for a file path exists."""
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved
