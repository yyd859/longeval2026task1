"""Path helpers."""

from __future__ import annotations

import os
import shutil
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


def configure_java_home() -> str | None:
    """Populate JAVA_HOME from the environment or a common local JDK install."""
    java_home = os.environ.get("JAVA_HOME")
    if java_home and Path(java_home).exists():
        return java_home

    candidates = [
        Path("C:/Program Files/Java/jdk-17"),
        Path("C:/Program Files/Eclipse Adoptium/jdk-17"),
        Path("C:/Program Files/Microsoft/jdk-17"),
    ]
    for candidate in candidates:
        if candidate.exists():
            os.environ["JAVA_HOME"] = str(candidate)
            java_bin = candidate / "bin"
            path_entries = os.environ.get("Path", "").split(os.pathsep)
            if str(java_bin) not in path_entries:
                os.environ["Path"] = os.pathsep.join([str(java_bin), *path_entries])
            return str(candidate)

    java_path = shutil.which("java")
    if java_path:
        java_bin = Path(java_path).resolve().parent
        candidate = java_bin.parent
        if (candidate / "bin" / "java.exe").exists() or (candidate / "bin" / "java").exists():
            os.environ.setdefault("JAVA_HOME", str(candidate))
            return str(candidate)
    return None
