"""Path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_parent(path: str | Path) -> Path:
    """Ensure the parent directory for a file path exists."""
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists and return its path."""
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def configure_ir_datasets_home(cache_dir: str | Path | None) -> Path | None:
    """Set a workspace-local ir_datasets cache directory when needed."""
    if cache_dir is None:
        return None
    cache_path = ensure_dir(cache_dir)
    os.environ.setdefault("IR_DATASETS_HOME", str(cache_path))
    return cache_path


def configure_pyterrier_home(cache_dir: str | Path | None = ".cache/pyterrier") -> Path | None:
    """Set a workspace-local pyterrier home directory when needed."""
    if cache_dir is None:
        return None
    cache_path = ensure_dir(cache_dir)
    os.environ.setdefault("PYTERRIER_HOME", str(cache_path))
    return cache_path
