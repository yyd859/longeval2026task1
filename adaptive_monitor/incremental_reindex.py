"""Incremental lexical reindexing helpers.

The incremental path builds a delta PyTerrier index for documents added after a
known reindex cutoff, then merges the live index and delta index into a shadow
index. Promotion remains the responsibility of reindex_pipeline.py.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.config import DatasetConfig  # noqa: E402
from longeval_sci.io.dataset import _snapshot_cache_files  # noqa: E402
from longeval_sci.io.readers import read_records  # noqa: E402
from longeval_sci.utils.paths import ensure_dir  # noqa: E402


@dataclass(slots=True)
class IncrementalReindexResult:
    snapshot_id: str
    text_mode: str
    date_field: str
    start_after: str
    end_at: str
    live_index_path: str
    delta_index_path: str
    merged_index_path: str
    delta_doc_count: int
    strategy: str = "delta_index_then_terrier_merge"


def parse_cutoff_date(value: str) -> datetime:
    """
    Parse an ISO-8601 timestamp string and return a timezone-aware UTC datetime.
    
    Parameters:
        value (str): ISO-8601 timestamp. A trailing "Z" is treated as UTC; a date-only string ("YYYY-MM-DD") is allowed.
    
    Returns:
        datetime: A timezone-aware datetime in UTC. If `value` is date-only (10 characters), the time is set to 23:59:59.
    """
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    parsed = parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    if len(value) == 10:
        return parsed.replace(hour=23, minute=59, second=59)
    return parsed


def week_end(week_start: str) -> datetime:
    """
    Return the end datetime of a 7-day window starting at the given week_start.
    
    Parameters:
        week_start (str): ISO-8601 date or timestamp string. If the string is date-only (YYYY-MM-DD),
            the time is interpreted as 23:59:59. Timezones are normalized to UTC.
    
    Returns:
        datetime: Timezone-aware UTC datetime equal to `week_start` (normalized) plus six days.
    """
    return parse_cutoff_date(week_start) + timedelta(days=6)


def _as_text(value: object) -> str:
    """
    Normalize a value into a trimmed text string.
    
    Parameters:
        value (object): Value to normalize; None becomes an empty string.
    
    Returns:
        text (str): Empty string if `value` is None, otherwise `str(value)` with leading and trailing whitespace removed.
    """
    return "" if value is None else str(value).strip()


def _parse_dt(value: object) -> datetime | None:
    """
    Parse an ISO-8601 date/time-like value and return a timezone-aware UTC datetime, or `None` when input is falsy or unparseable.
    
    Parameters:
        value (object): A string-like ISO-8601 timestamp (may include "Z") or any object convertible to `str`.
    
    Returns:
        datetime | None: A `datetime` normalized to UTC (with tzinfo=UTC), or `None` if `value` is falsy or cannot be parsed.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _join_text(parts: list[str]) -> str:
    """
    Join a list of text fragments into a single newline-separated string, omitting empty fragments.
    
    Parameters:
        parts (list[str]): Fragments to join; each fragment is stripped and empty fragments are ignored.
    
    Returns:
        str: The joined string with fragments separated by `\n` and trimmed of leading/trailing whitespace.
    """
    return "\n".join(part.strip() for part in parts if part and part.strip()).strip()


def iter_incremental_text_records(
    dataset_config: DatasetConfig,
    snapshot_id: str,
    text_mode: str,
    *,
    date_field: str,
    start_after: datetime,
    end_at: datetime,
) -> Iterable[dict[str, str]]:
    """
    Yield PyTerrier-ready records for documents whose parsed date is after `start_after` and up to and including `end_at`.
    
    This generator iterates cached snapshot JSONL files for the given snapshot and text kind, parses each record's date using the module's ISO-8601 parser, filters records to the interval (start_after, end_at], extracts a stable document identifier from `doc_id`, `id`, or `docno`, and assembles a single `text` field according to `text_mode`. If a record lacks a parsable date or a non-empty document id it is skipped. An unsupported `text_mode` raises ValueError.
    
    Parameters:
        dataset_config (DatasetConfig): Dataset configuration containing at least `dataset_root`.
        snapshot_id (str): Identifier of the snapshot whose cached files to read.
        text_mode (str): Determines text assembly. `"full_text"` uses the record's full text when available (falls back to title+abstract); `"title_abstract"` joins title and abstract.
        date_field (str): JSON field name in each record that holds the document timestamp.
        start_after (datetime): Exclusive lower bound; records with parsed date <= this value are excluded.
        end_at (datetime): Inclusive upper bound; records with parsed date > this value are excluded.
    
    Returns:
        Iterable[dict[str, str]]: An iterator of dictionaries with keys:
            - "docno": document identifier string
            - "text": assembled document text
    """
    kind = "fulltext" if text_mode == "full_text" else "abstract"
    for path in _snapshot_cache_files(Path(dataset_config.dataset_root), snapshot_id, kind):
        for record in read_records(path, "jsonl"):
            doc_dt = _parse_dt(record.get(date_field))
            if doc_dt is None or doc_dt <= start_after or doc_dt > end_at:
                continue
            doc_id = _as_text(record.get("doc_id") or record.get("id") or record.get("docno"))
            if not doc_id:
                continue
            title = _as_text(record.get("title"))
            abstract = _as_text(record.get("abstract"))
            full_text = _as_text(record.get("full_text") or record.get("fullText") or record.get("text") or record.get("body"))
            if text_mode == "full_text":
                text = _join_text([full_text or _join_text([title, abstract])])
            elif text_mode == "title_abstract":
                text = _join_text([title, abstract])
            else:
                raise ValueError(f"Unsupported incremental lexical text mode: {text_mode}")
            yield {"docno": doc_id, "text": text}


def _counting_iter(records: Iterable[dict[str, str]], counter: dict[str, int]) -> Iterable[dict[str, str]]:
    """
    Wraps an iterable of record dicts and increments a provided mutable counter for each yielded record.
    
    Parameters:
        records (Iterable[dict[str, str]]): An iterable of record dictionaries to forward.
        counter (dict[str, int]): A mutable mapping expected to contain an integer under the key `"count"`; this value is incremented once per yielded record.
    
    Returns:
        Iterable[dict[str, str]]: Each input record yielded unchanged.
    """
    for record in records:
        counter["count"] += 1
        yield record


def build_delta_pyterrier_index(
    dataset_config: DatasetConfig,
    snapshot_id: str,
    text_mode: str,
    delta_index_dir: Path,
    *,
    date_field: str,
    start_after: datetime,
    end_at: datetime,
    memory_limit_mb: int | None,
) -> int:
    """
    Create a PyTerrier delta index on disk containing documents whose record date is after `start_after` and up to and including `end_at`.
    
    Parameters:
        dataset_config (DatasetConfig): Configuration used to locate snapshot cache files for the dataset.
        snapshot_id (str): Identifier of the snapshot to read cached records from.
        text_mode (str): Determines how document text is assembled; e.g. `"full_text"` or `"title_abstract"`.
        delta_index_dir (Path): Filesystem path where the delta index will be created (directory is ensured and overwritten).
        date_field (str): Name of the document field containing the record datetime used for filtering.
        start_after (datetime): Exclusive lower bound for document datetimes; documents with datetime <= this value are excluded.
        end_at (datetime): Inclusive upper bound for document datetimes; documents with datetime > this value are excluded.
        memory_limit_mb (int | None): Optional memory limit (MB) passed when starting PyTerrier; `None` leaves default behavior.
    
    Returns:
        int: Total number of documents indexed into the delta index.
    """
    from longeval_sci.baselines.runner import _ensure_pyterrier_started  # noqa: PLC0415

    pt = _ensure_pyterrier_started(memory_limit_mb)
    ensure_dir(delta_index_dir)
    indexer = pt.IterDictIndexer(
        str(delta_index_dir.resolve()),
        overwrite=True,
        meta={"docno": 100, "text": 20480},
    )
    counter = {"count": 0}
    records = iter_incremental_text_records(
        dataset_config,
        snapshot_id,
        text_mode,
        date_field=date_field,
        start_after=start_after,
        end_at=end_at,
    )
    indexer.index(_counting_iter(records, counter))
    return counter["count"]


def merge_pyterrier_indexes(live_index_dir: Path, delta_index_dir: Path, merged_index_dir: Path) -> None:
    """
    Merge a live PyTerrier index and a delta PyTerrier index into a new on-disk merged (shadow) index.
    
    Merges the index structures from live_index_dir and delta_index_dir into merged_index_dir using Terrier's StructureMerger with reverse meta enabled. The destination directory will be created if it does not exist; it must be empty if it already exists.
    
    Parameters:
        live_index_dir (Path): Path to the existing live PyTerrier index directory (must contain data.properties).
        delta_index_dir (Path): Path to the delta PyTerrier index directory to merge (must contain data.properties).
        merged_index_dir (Path): Path where the merged shadow index will be created.
    
    Raises:
        FileNotFoundError: If either live_index_dir or delta_index_dir is missing its data.properties file.
        FileExistsError: If merged_index_dir exists and is not empty.
    """
    from longeval_sci.baselines.runner import _ensure_pyterrier_started  # noqa: PLC0415

    pt = _ensure_pyterrier_started()
    live_properties = live_index_dir / "data.properties"
    delta_properties = delta_index_dir / "data.properties"
    if not live_properties.exists():
        raise FileNotFoundError(f"Live PyTerrier index is missing data.properties: {live_index_dir}")
    if not delta_properties.exists():
        raise FileNotFoundError(f"Delta PyTerrier index is missing data.properties: {delta_index_dir}")
    if merged_index_dir.exists() and any(merged_index_dir.iterdir()):
        raise FileExistsError(f"Merged shadow index directory is not empty: {merged_index_dir}")

    ensure_dir(merged_index_dir)
    live_index = pt.terrier.IndexFactory.of(str(live_index_dir.resolve()))
    delta_index = pt.terrier.IndexFactory.of(str(delta_index_dir.resolve()))
    merged_index = pt.terrier.J.IndexOnDisk.createNewIndex(str(merged_index_dir.resolve()), "data")
    merger = pt.terrier.J.StructureMerger(live_index, delta_index, merged_index)
    merger.setReverseMeta(True)
    merger.mergeStructures()
    try:
        merged_index.close()
    except Exception:
        pass
    try:
        live_index.close()
    except Exception:
        pass
    try:
        delta_index.close()
    except Exception:
        pass


def build_incremental_lexical_shadow_index(
    *,
    dataset_config: DatasetConfig,
    snapshot_id: str,
    text_mode: str,
    live_index_dir: Path,
    shadow_index_dir: Path,
    delta_index_dir: Path,
    date_field: str,
    start_after: datetime,
    end_at: datetime,
    memory_limit_mb: int | None,
    manifest_path: Path | None = None,
) -> IncrementalReindexResult:
    """
    Orchestrates an incremental lexical reindex: build a delta PyTerrier index for documents in a date window, merge it with the live index into a shadow (merged) index, and return a manifest of the operation.
    
    Parameters:
        dataset_config (DatasetConfig): Dataset configuration used to locate snapshot cache files.
        snapshot_id (str): Identifier of the snapshot to read records from.
        text_mode (str): Text assembly mode; e.g., "full_text" or "title_abstract".
        live_index_dir (Path): Path to the existing live PyTerrier index to be merged with the delta.
        shadow_index_dir (Path): Destination path for the merged (shadow) index; must not be a non-empty existing directory.
        delta_index_dir (Path): Path where the temporary delta PyTerrier index will be created/overwritten.
        date_field (str): Document field name containing the record timestamp used for window filtering.
        start_after (datetime): Lower bound of the date window; documents with timestamps less than or equal to this are excluded.
        end_at (datetime): Upper bound of the date window; documents with timestamps greater than this are excluded.
        memory_limit_mb (int | None): Optional PyTerrier memory limit in megabytes used when creating the delta index.
        manifest_path (Path | None): If provided, file path where a JSON manifest of the returned IncrementalReindexResult will be written (parent directories will be created).
    
    Returns:
        IncrementalReindexResult: Summary of the reindex operation, including input metadata, filesystem paths for live/delta/merged indices, and the counted number of documents indexed into the delta.
    """
    delta_doc_count = build_delta_pyterrier_index(
        dataset_config,
        snapshot_id,
        text_mode,
        delta_index_dir,
        date_field=date_field,
        start_after=start_after,
        end_at=end_at,
        memory_limit_mb=memory_limit_mb,
    )
    merge_pyterrier_indexes(live_index_dir, delta_index_dir, shadow_index_dir)
    result = IncrementalReindexResult(
        snapshot_id=snapshot_id,
        text_mode=text_mode,
        date_field=date_field,
        start_after=start_after.isoformat(),
        end_at=end_at.isoformat(),
        live_index_path=str(live_index_dir),
        delta_index_path=str(delta_index_dir),
        merged_index_path=str(shadow_index_dir),
        delta_doc_count=delta_doc_count,
    )
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")
    return result
