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
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    parsed = parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    if len(value) == 10:
        return parsed.replace(hour=23, minute=59, second=59)
    return parsed


def week_end(week_start: str) -> datetime:
    return parse_cutoff_date(week_start) + timedelta(days=6)


def _as_text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _join_text(parts: list[str]) -> str:
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
