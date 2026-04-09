"""Dataset normalization for LongEval-Sci."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from longeval_sci.config import DatasetConfig, snapshot_dataset_name
from longeval_sci.io.readers import read_records
from longeval_sci.utils.paths import configure_ir_datasets_home


@dataclass(slots=True)
class Document:
    doc_id: str
    title: str = ""
    abstract: str = ""
    full_text: str = ""
    snapshot_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Query:
    query_id: str
    text: str
    snapshot_id: str | None = None


@dataclass(slots=True)
class SearchResult:
    query_id: str
    doc_id: str
    score: float
    rank: int
    run_name: str


@dataclass(slots=True)
class DatasetMetadata:
    backend: str
    dataset_name: str
    snapshot_id: str
    qrels_variant: str | None
    timestamp: str | None = None
    prior_dataset_names: list[str] = field(default_factory=list)
    has_qrels: bool = False


@dataclass(slots=True)
class DatasetBundle:
    documents: list[Document]
    queries: list[Query]
    qrels: dict[str, dict[str, int]] | None
    metadata: DatasetMetadata


def _as_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _object_to_record(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    fields = getattr(item, "_fields", None)
    if fields:
        return {field_name: getattr(item, field_name) for field_name in fields}
    if hasattr(item, "__dict__"):
        return {key: value for key, value in vars(item).items() if not key.startswith("_")}
    return {}


def _extract_value(item: Any, candidate_names: Iterable[str], default: Any = "") -> Any:
    for name in candidate_names:
        if hasattr(item, name):
            return getattr(item, name)
        if isinstance(item, dict) and name in item:
            return item[name]
    return default


def _load_local_bundle(config: DatasetConfig, snapshot_id: str) -> DatasetBundle:
    if not config.corpus_path or not config.queries_path:
        raise ValueError("Local dataset loading requires corpus_path and queries_path")
    documents: list[Document] = []
    for record in read_records(config.corpus_path, config.corpus_format):
        doc_id = _as_text(record.get(config.corpus_field_map.get("doc_id", "doc_id")) or record.get("doc_id"))
        if not doc_id:
            raise ValueError("Local corpus record is missing doc_id")
        documents.append(
            Document(
                doc_id=doc_id,
                title=_as_text(record.get(config.corpus_field_map.get("title", "title"))),
                abstract=_as_text(record.get(config.corpus_field_map.get("abstract", "abstract"))),
                full_text=_as_text(
                    record.get(config.corpus_field_map.get("full_text", "full_text")) or record.get("text") or record.get("body")
                ),
                snapshot_id=snapshot_id,
                metadata={key: value for key, value in record.items() if key not in {"doc_id", "title", "abstract", "full_text", "text", "body", "snapshot_id"}},
            )
        )

    queries: list[Query] = []
    for record in read_records(config.queries_path, config.queries_format):
        query_id = _as_text(record.get(config.query_field_map.get("query_id", "query_id")) or record.get("query_id"))
        text = _as_text(record.get(config.query_field_map.get("query_text", "query_text")) or record.get("query_text"))
        if not query_id or not text:
            raise ValueError("Local query record is missing query_id or query_text")
        queries.append(Query(query_id=query_id, text=text, snapshot_id=snapshot_id))

    qrels = _load_qrels_file(config)

    metadata = DatasetMetadata(
        backend="local_files",
        dataset_name=config.dataset_root,
        snapshot_id=snapshot_id,
        qrels_variant=config.qrels_variant,
        has_qrels=qrels is not None,
    )
    return DatasetBundle(documents=documents, queries=queries, qrels=qrels, metadata=metadata)


def _snapshot_dir_name(snapshot_id: str) -> str:
    return snapshot_id.replace("-", "")


def _load_qrels_file(config: DatasetConfig) -> dict[str, dict[str, int]] | None:
    if not config.qrels_path or not Path(config.qrels_path).exists():
        return None

    qrels: dict[str, dict[str, int]] = {}
    for record in read_records(config.qrels_path, config.qrels_format):
        query_id = _as_text(record.get(config.qrels_field_map.get("query_id", "query_id")) or record.get("query_id"))
        doc_id = _as_text(record.get(config.qrels_field_map.get("doc_id", "doc_id")) or record.get("doc_id"))
        relevance = int(record.get(config.qrels_field_map.get("relevance", "relevance")) or record.get("relevance") or 0)
        qrels.setdefault(query_id, {})[doc_id] = relevance
    return qrels


def _snapshot_cache_files(root: Path, snapshot_id: str, kind: str) -> list[Path]:
    snapshot_root = root / _snapshot_dir_name(snapshot_id)
    if not snapshot_root.exists():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_root}")
    return sorted(path for path in snapshot_root.rglob("*.jsonl") if kind in str(path).lower())


def _join_snapshot_text(parts: list[str]) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip()).strip()


def iter_snapshot_cache_text_records(config: DatasetConfig, snapshot_id: str, text_mode: str) -> Iterable[dict[str, str]]:
    """Stream snapshot-cache documents as docno/text records for large lexical indexing."""
    root = Path(config.dataset_root)
    if text_mode == "full_text":
        source_files = _snapshot_cache_files(root, snapshot_id, "fulltext")
    elif text_mode == "title_abstract":
        source_files = _snapshot_cache_files(root, snapshot_id, "abstract")
    else:
        raise ValueError(f"Unsupported snapshot-cache streaming text mode: {text_mode}")

    for path in source_files:
        for record in read_records(path, "jsonl"):
            doc_id = _as_text(record.get("doc_id") or record.get("id") or record.get("docno"))
            if not doc_id:
                continue
            title = _as_text(record.get("title"))
            abstract = _as_text(record.get("abstract"))
            full_text = _as_text(record.get("full_text") or record.get("fullText") or record.get("text") or record.get("body"))
            if text_mode == "full_text":
                text = _join_snapshot_text([full_text or _join_snapshot_text([title, abstract])])
            else:
                text = _join_snapshot_text([title, abstract])
            yield {"docno": doc_id, "text": text}


def _load_snapshot_cache_bundle(config: DatasetConfig, snapshot_id: str) -> DatasetBundle:
    root = Path(config.dataset_root)
    snapshot_root = root / _snapshot_dir_name(snapshot_id)
    if not snapshot_root.exists():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_root}")

    abstract_files = sorted(
        path for path in snapshot_root.rglob("*.jsonl") if "abstract" in str(path).lower()
    )
    fulltext_files = []
    if config.load_fulltext:
        fulltext_files = sorted(
            path for path in snapshot_root.rglob("*.jsonl") if "fulltext" in str(path).lower()
        )
    if not abstract_files and not fulltext_files:
        raise FileNotFoundError(f"No JSONL document files found under {snapshot_root}")

    documents_by_id: dict[str, Document] = {}

    def upsert_document(record: dict[str, Any], is_fulltext: bool) -> None:
        doc_id = _as_text(record.get("doc_id") or record.get("id") or record.get("docno"))
        if not doc_id:
            raise ValueError(f"Snapshot cache record is missing a document id: {record}")
        document = documents_by_id.get(doc_id)
        if document is None:
            document = Document(doc_id=doc_id, snapshot_id=snapshot_id)
            documents_by_id[doc_id] = document

        title = _as_text(record.get("title"))
        abstract = _as_text(record.get("abstract"))
        full_text = ""
        if config.load_fulltext:
            full_text = _as_text(record.get("full_text") or record.get("fullText") or record.get("text") or record.get("body"))
        if title and not document.title:
            document.title = title
        if abstract and not document.abstract:
            document.abstract = abstract
        if is_fulltext and full_text:
            document.full_text = full_text
        elif full_text and not document.full_text and not is_fulltext:
            document.full_text = full_text

        for key, value in record.items():
            if key not in {"id", "doc_id", "docno", "title", "abstract", "fullText", "full_text", "text", "body"}:
                document.metadata.setdefault(key, value)

    for path in abstract_files:
        for record in read_records(path, "jsonl"):
            upsert_document(record, is_fulltext=False)
    for path in fulltext_files:
        for record in read_records(path, "jsonl"):
            upsert_document(record, is_fulltext=True)

    default_queries_name = (
        "task1_longeval_adhoc-queries-snapshot-train.tsv"
        if config.split == "train"
        else "longeval_adhoc-queries-snapshot-test.tsv"
    )
    queries_path = Path(config.queries_path) if config.queries_path else root / default_queries_name
    if not queries_path.exists():
        raise FileNotFoundError(f"Queries file not found: {queries_path}")
    queries: list[Query] = []
    with queries_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split("\t", maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"Invalid query line in {queries_path} at line {line_number}: expected 2 TSV columns")
            queries.append(Query(query_id=_as_text(parts[0]), text=_as_text(parts[1]), snapshot_id=snapshot_id))

    qrels = _load_qrels_file(config)

    metadata = DatasetMetadata(
        backend="local_snapshot_cache",
        dataset_name=f"longeval-sci-2026/{snapshot_id}/{config.split + '/' if config.split else ''}{config.qrels_variant}",
        snapshot_id=snapshot_id,
        qrels_variant=config.qrels_variant,
        has_qrels=qrels is not None,
    )
    return DatasetBundle(
        documents=list(documents_by_id.values()),
        queries=queries,
        qrels=qrels,
        metadata=metadata,
    )


def _load_ir_bundle(config: DatasetConfig, snapshot_id: str) -> DatasetBundle:
    configure_ir_datasets_home(config.cache_dir)
    try:
        from ir_datasets_longeval import load
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Install ir-datasets-longeval to use the official LongEval data loader") from exc

    dataset_name = snapshot_dataset_name(config, snapshot_id)
    dataset = load(dataset_name)

    documents: list[Document] = []
    for doc in dataset.docs_iter():
        record = _object_to_record(doc)
        documents.append(
            Document(
                doc_id=_as_text(_extract_value(doc, ("doc_id", "docno", "id"), record.get("doc_id"))),
                title=_as_text(_extract_value(doc, ("title",), record.get("title"))),
                abstract=_as_text(_extract_value(doc, ("abstract", "summary"), record.get("abstract"))),
                full_text=_as_text(_extract_value(doc, ("full_text", "text", "body"), record.get("text"))),
                snapshot_id=snapshot_id,
                metadata={
                    key: value
                    for key, value in record.items()
                    if key not in {"doc_id", "docno", "id", "title", "abstract", "summary", "full_text", "text", "body"}
                },
            )
        )

    queries: list[Query] = []
    if hasattr(dataset, "queries_iter"):
        for query in dataset.queries_iter():
            record = _object_to_record(query)
            queries.append(
                Query(
                    query_id=_as_text(_extract_value(query, ("query_id", "qid", "id"), record.get("query_id"))),
                    text=_as_text(_extract_value(query, ("text", "query", "title"), record.get("text"))),
                    snapshot_id=snapshot_id,
                )
            )

    qrels: dict[str, dict[str, int]] | None = None
    if hasattr(dataset, "qrels_iter"):
        try:
            qrels = {}
            for qrel in dataset.qrels_iter():
                query_id = _as_text(_extract_value(qrel, ("query_id", "qid"), ""))
                doc_id = _as_text(_extract_value(qrel, ("doc_id", "docno"), ""))
                relevance = int(_extract_value(qrel, ("relevance", "score", "label"), 0))
                qrels.setdefault(query_id, {})[doc_id] = relevance
        except Exception:
            qrels = None

    timestamp = None
    if hasattr(dataset, "get_timestamp"):
        try:
            timestamp = str(dataset.get_timestamp())
        except Exception:
            timestamp = None

    prior_dataset_names: list[str] = []
    if hasattr(dataset, "get_prior_datasets"):
        try:
            prior_dataset_names = [prior._irds_id() for prior in dataset.get_prior_datasets() if hasattr(prior, "_irds_id")]
        except Exception:
            prior_dataset_names = []

    metadata = DatasetMetadata(
        backend="ir_datasets_longeval",
        dataset_name=dataset_name,
        snapshot_id=snapshot_id,
        qrels_variant=config.qrels_variant,
        timestamp=timestamp,
        prior_dataset_names=prior_dataset_names,
        has_qrels=qrels is not None,
    )
    return DatasetBundle(documents=documents, queries=queries, qrels=qrels, metadata=metadata)


def load_dataset_bundle(config: DatasetConfig, snapshot_id: str) -> DatasetBundle:
    """Load one snapshot bundle from the configured backend."""
    if config.backend == "local_files":
        return _load_local_bundle(config, snapshot_id)
    if config.backend == "local_snapshot_cache":
        return _load_snapshot_cache_bundle(config, snapshot_id)
    if config.backend == "ir_datasets_longeval":
        return _load_ir_bundle(config, snapshot_id)
    raise ValueError(f"Unsupported dataset backend: {config.backend}")


def load_qrels(config: DatasetConfig, snapshot_id: str) -> dict[str, dict[str, int]]:
    """Load qrels for a snapshot."""
    bundle = load_dataset_bundle(config, snapshot_id)
    if bundle.qrels is None:
        raise ValueError(f"No qrels are available for dataset {bundle.metadata.dataset_name}")
    return bundle.qrels
