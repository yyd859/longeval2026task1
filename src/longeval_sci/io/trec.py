"""TREC run IO helpers."""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

from longeval_sci.io.dataset import SearchResult


def write_trec_run(results: list[SearchResult], path: str | Path) -> None:
    """Write search results in standard TREC run format."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        for result in results:
            handle.write(
                f"{result.query_id} Q0 {result.doc_id} {result.rank} {result.score:.6f} {result.run_name}\n"
            )


def read_trec_run(path: str | Path) -> dict[str, dict[str, float]]:
    """Read a TREC run file into a nested dictionary."""
    run: dict[str, dict[str, float]] = {}
    input_path = Path(path)
    opener = gzip.open if input_path.suffix == ".gz" else Path.open
    with opener(input_path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            parts = line.strip().split()
            if len(parts) != 6:
                raise ValueError(f"Invalid TREC line in {path} at {line_number}: expected 6 columns, got {len(parts)}")
            query_id, _, doc_id, _, score, _ = parts
            run.setdefault(query_id, {})[doc_id] = float(score)
    return run


def write_per_query_csv(rows: list[dict[str, str | float]], path: str | Path) -> None:
    """Write per-query metrics to CSV."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
