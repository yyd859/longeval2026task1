"""Flexible readers for benchmark files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def infer_format(path: str | Path, explicit_format: str | None = None) -> str:
    """Infer a structured file format from path or explicit config."""
    if explicit_format:
        return explicit_format.lower()
    suffix = Path(path).suffix.lower()
    mapping = {".json": "json", ".jsonl": "jsonl", ".tsv": "tsv", ".csv": "csv"}
    if suffix not in mapping:
        raise ValueError(f"Unsupported file extension for {path!s}. Expected one of: .json, .jsonl, .tsv, .csv")
    return mapping[suffix]


def ensure_dict(value: Any, path: Path) -> dict[str, Any]:
    """Validate that a parsed record is dictionary-like."""
    if not isinstance(value, dict):
        raise ValueError(f"Record in {path} must be a JSON object, got {type(value).__name__}")
    return value


def read_records(path: str | Path, file_format: str | None = None) -> list[dict[str, Any]]:
    """Read structured records from JSON, JSONL, TSV, or CSV."""
    format_name = infer_format(path, file_format)
    record_path = Path(path)
    if not record_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {record_path}")

    if format_name == "json":
        with record_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return [ensure_dict(item, record_path) for item in payload]
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], list):
            return [ensure_dict(item, record_path) for item in payload["data"]]
        raise ValueError(f"JSON file {record_path} must contain a list of records or a top-level 'data' list")

    if format_name == "jsonl":
        records: list[dict[str, Any]] = []
        with record_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    records.append(ensure_dict(json.loads(stripped), record_path))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL in {record_path} at line {line_number}: {exc}") from exc
        return records

    delimiter = "\t" if format_name == "tsv" else ","
    with record_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"Delimited file {record_path} is missing a header row")
        return [dict(row) for row in reader]
