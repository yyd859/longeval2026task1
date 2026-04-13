"""Preflight checks for official LongEval baseline runs."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.config import load_config
from longeval_sci.utils.paths import configure_java_home, configure_pyterrier_home


def _status(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def _check_java() -> tuple[bool, dict[str, str | bool]]:
    configure_java_home()
    java_home = os.environ.get("JAVA_HOME", "")
    details: dict[str, str | bool] = {"java_home_set": bool(java_home), "java_home": java_home or "(not set)"}
    try:
        result = subprocess.run(["java", "-version"], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        details["java_found"] = False
        details["java_version"] = "(java not on PATH)"
        return False, details

    version_text = (result.stderr or result.stdout).strip().splitlines()
    first_line = version_text[0] if version_text else "(unknown)"
    details["java_found"] = result.returncode == 0
    details["java_version"] = first_line
    details["java_17_hint"] = "17" in first_line
    ok = bool(java_home) and result.returncode == 0 and "17" in first_line
    return ok, details


def _check_python_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _check_pyterrier() -> tuple[bool, dict[str, str | bool]]:
    details: dict[str, str | bool] = {
        "pyterrier_installed": _check_python_module("pyterrier"),
        "pyjnius_installed": _check_python_module("jnius"),
    }
    if not details["pyterrier_installed"]:
        details["startup"] = "pyterrier not installed"
        return False, details
    try:
        import pyterrier as pt  # type: ignore

        configure_pyterrier_home()
        if not pt.java.started():
            pt.java.init()
        details["startup"] = "success"
        return True, details
    except Exception as exc:
        details["startup"] = str(exc)
        return False, details


def _check_dataset_cache() -> tuple[bool, dict[str, str | bool | int]]:
    config = load_config(ROOT / "configs" / "official_pyterrier.yaml")
    root = Path(config.dataset.dataset_root)
    queries_path = root / "longeval_adhoc-queries-snapshot-test.tsv"
    snapshot_dirs = [root / "snapshot1", root / "snapshot2", root / "snapshot3"]
    abstract_counts = sum(len(list(path.rglob("*abstract*/documents/*.jsonl"))) for path in snapshot_dirs if path.exists())
    fulltext_counts = sum(len(list(path.rglob("*fulltext*/documents/*.jsonl"))) for path in snapshot_dirs if path.exists())
    details: dict[str, str | bool | int] = {
        "dataset_root": str(root),
        "root_exists": root.exists(),
        "queries_exists": queries_path.exists(),
        "snapshot_dirs_present": sum(path.exists() for path in snapshot_dirs),
        "abstract_jsonl_files": abstract_counts,
        "fulltext_jsonl_files": fulltext_counts,
    }
    ok = root.exists() and queries_path.exists() and all(path.exists() for path in snapshot_dirs) and abstract_counts > 0
    return ok, details


def _check_dense_stack() -> tuple[bool, dict[str, str | bool | int]]:
    config = load_config(ROOT / "configs" / "official_pyterrier_dense.yaml")
    base_url = config.retrieval.service_base_url.rstrip("/")
    model_name = config.retrieval.model_name or "Qwen/Qwen3-Embedding-4B"
    details: dict[str, str | bool | int] = {
        "pyterrier_dr_installed": _check_python_module("pyterrier_dr"),
        "openai_installed": _check_python_module("openai"),
        "service_base_url": base_url,
        "model_name": model_name,
    }
    try:
        with urllib.request.urlopen(f"{base_url}/models", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        details["service_reachable"] = True
        model_ids = [item.get("id", "") for item in payload.get("data", []) if isinstance(item, dict)]
        details["models_seen"] = len(model_ids)
        details["model_present"] = model_name in model_ids
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        details["service_reachable"] = False
        details["service_error"] = str(exc)
        details["models_seen"] = 0
        details["model_present"] = False
    ok = bool(details["pyterrier_dr_installed"]) and bool(details["openai_installed"]) and bool(details["service_reachable"])
    return ok, details


def main() -> None:
    checks = [
        ("Java 17", _check_java),
        ("PyTerrier", _check_pyterrier),
        ("Dataset Cache", _check_dataset_cache),
        ("Dense Stack", _check_dense_stack),
    ]
    any_fail = False
    for name, check_fn in checks:
        ok, details = check_fn()
        any_fail = any_fail or not ok
        print(f"[{_status(ok)}] {name}")
        for key, value in details.items():
            print(f"  {key}: {value}")
    if any_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
