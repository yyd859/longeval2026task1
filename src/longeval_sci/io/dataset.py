"""Dataset normalization for LongEval-Sci."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from longeval_sci.config import DatasetConfig, resolve_dataset_name, resolve_snapshot_id
from longeval_sci.io.readers import read_records


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


def _first_present(record: dict[str, Any], field_names: list[str], required: bool, kind: str, path: str) -> Any:
    for field_name in field_names:
        if field_name in record:
            return record[field_name]
    if required:
        raise ValueError(f"{kind} record in {path} is missing required fields: {field_names}")
    return None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _object_to_record(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    fields = getattr(item, "_fields", None)
    if fields:
        return {field: getattr(item, field) for field in fields}
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


def _load_documents_from_records(config: DatasetConfig) -> list[Document]:
    field_map = config.corpus_field_map
    assert config.corpus_path is not None
    records = read_records(config.corpus_path, config.corpus_format)
    documents: list[Document] = []
    for record in records:
        doc_id = _as_text(
            _first_present(record, [field_map.get("doc_id", "doc_id"), "id", "docno"], True, "Document", config.corpus_path)
        )
        if not doc_id:
            raise ValueError(f"Document in {config.corpus_path} has an empty doc_id")
        title = _as_text(_first_present(record, [field_map.get("title", "title")], False, "Document", config.corpus_path))
        abstract = _as_text(
            _first_present(record, [field_map.get("abstract", "abstract"), "summary"], False, "Document", config.corpus_path)
        )
        full_text = _as_text(
            _first_present(record, [field_map.get("full_text", "full_text"), "text", "body"], False, "Document", config.corpus_path)
        )
        snapshot_id = _as_text(
            _first_present(record, [field_map.get("snapshot_id", "snapshot_id"), "snapshot"], False, "Document", config.corpus_path)
        ) or config.snapshot_id
        reserved = {
            field_map.get("doc_id", "doc_id"),
            "id",
            "docno",
            field_map.get("title", "title"),
            field_map.get("abstract", "abstract"),
            "summary",
            field_map.get("full_text", "full_text"),
            "text",
            "body",
            field_map.get("snapshot_id", "snapshot_id"),
            "snapshot",
        }
        metadata = {key: value for key, value in record.items() if key not in reserved}
        documents.append(
            Document(
                doc_id=doc_id,
                title=title,
                abstract=abstract,
                full_text=full_text,
                snapshot_id=snapshot_id or None,
                metadata=metadata,
            )
        )
    return documents


def _load_queries_from_records(config: DatasetConfig) -> list[Query]:
    field_map = config.query_field_map
    assert config.queries_path is not None
    records = read_records(config.queries_path, config.queries_format)
    queries: list[Query] = []
    for record in records:
        query_id = _as_text(
            _first_present(record, [field_map.get("query_id", "query_id"), "qid", "id"], True, "Query", config.queries_path)
        )
        if not query_id:
            raise ValueError(f"Query in {config.queries_path} has an empty query_id")
        query_text = _as_text(
            _first_present(record, [field_map.get("query_text", "query_text"), "text", "query"], True, "Query", config.queries_path)
        )
        snapshot_id = _as_text(
            _first_present(record, [field_map.get("snapshot_id", "snapshot_id"), "snapshot"], False, "Query", config.queries_path)
        ) or config.snapshot_id
        queries.append(Query(query_id=query_id, text=query_text, snapshot_id=snapshot_id or None))
    return queries


def _load_qrels_from_records(config: DatasetConfig) -> dict[str, dict[str, int]]:
    if not config.qrels_path:
        raise ValueError("Qrels path is required for local-file evaluation")
    field_map = config.qrels_field_map
    records = read_records(config.qrels_path, config.qrels_format)
    qrels: dict[str, dict[str, int]] = {}
    for record in records:
        query_id = _as_text(
            _first_present(record, [field_map.get("query_id", "query_id"), "qid"], True, "Qrels", config.qrels_path)
        )
        doc_id = _as_text(
            _first_present(record, [field_map.get("doc_id", "doc_id"), "docno"], True, "Qrels", config.qrels_path)
        )
        relevance_raw = _first_present(
            record, [field_map.get("relevance", "relevance"), "label", "score"], True, "Qrels", config.qrels_path
        )
        qrels.setdefault(query_id, {})[doc_id] = int(relevance_raw)
    return qrels


def _load_local_dataset(config: DatasetConfig) -> DatasetBundle:
    if not config.corpus_path or not config.queries_path:
        raise ValueError("Local dataset loading requires corpus_path and queries_path")
    documents = _load_documents_from_records(config)
    queries = _load_queries_from_records(config)
    qrels = _load_qrels_from_records(config) if config.qrels_path and Path(config.qrels_path).exists() else None
    metadata = DatasetMetadata(
        backend="local_files",
        dataset_name=config.dataset_name,
        snapshot_id=config.snapshot_id or resolve_snapshot_id(config.dataset_name, config.snapshot_id),
        qrels_variant=config.qrels_variant,
        has_qrels=qrels is not None,
    )
    return DatasetBundle(documents=documents, queries=queries, qrels=qrels, metadata=metadata)


def _load_ir_datasets_bundle(config: DatasetConfig) -> DatasetBundle:
    try:
        from ir_datasets_longeval import load
    except ImportError as exc:
        raise ImportError(
            "ir-datasets-longeval is required for the default LongEval 2026 data path. "
            "Install it with `pip install ir-datasets-longeval`."
        ) from exc

    resolved_name = resolve_dataset_name(config)
    dataset = load(resolved_name)
    snapshot_id = config.snapshot_id or resolve_snapshot_id(resolved_name)

    documents: list[Document] = []
    for doc in dataset.docs_iter():
        record = _object_to_record(doc)
        doc_id = _as_text(_extract_value(doc, ("doc_id", "docno", "id"), record.get("doc_id", "")))
        title = _as_text(_extract_value(doc, ("title",), record.get("title", "")))
        abstract = _as_text(_extract_value(doc, ("abstract", "summary"), record.get("abstract", "")))
        full_text = _as_text(_extract_value(doc, ("full_text", "text", "body"), record.get("text", "")))
        metadata = {
            key: value
            for key, value in record.items()
            if key not in {"doc_id", "docno", "id", "title", "abstract", "summary", "full_text", "text", "body"}
        }
        documents.append(
            Document(
                doc_id=doc_id,
                title=title,
                abstract=abstract,
                full_text=full_text,
                snapshot_id=snapshot_id,
                metadata=metadata,
            )
        )

    queries: list[Query] = []
    if hasattr(dataset, "queries_iter"):
        for query in dataset.queries_iter():
            record = _object_to_record(query)
            query_id = _as_text(_extract_value(query, ("query_id", "qid", "id"), record.get("query_id", "")))
            text = _as_text(_extract_value(query, ("text", "query", "title"), record.get("text", "")))
            queries.append(Query(query_id=query_id, text=text, snapshot_id=snapshot_id))

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
            for prior_dataset in dataset.get_prior_datasets():
                if hasattr(prior_dataset, "_irds_id"):
                    prior_dataset_names.append(str(prior_dataset._irds_id()))
                elif hasattr(prior_dataset, "dataset_id"):
                    prior_dataset_names.append(str(prior_dataset.dataset_id))
        except Exception:
            prior_dataset_names = []

    metadata = DatasetMetadata(
        backend="ir_datasets_longeval",
        dataset_name=resolved_name,
        snapshot_id=snapshot_id,
        qrels_variant=config.qrels_variant,
        timestamp=timestamp,
        prior_dataset_names=[name for name in prior_dataset_names if name],
        has_qrels=qrels is not None,
    )
    return DatasetBundle(documents=documents, queries=queries, qrels=qrels, metadata=metadata)


def load_dataset_bundle(config: DatasetConfig) -> DatasetBundle:
    """Load a dataset from the configured backend."""
    if config.backend == "ir_datasets_longeval":
        return _load_ir_datasets_bundle(config)
    if config.backend == "local_files":
        return _load_local_dataset(config)
    raise ValueError(f"Unsupported dataset backend: {config.backend}")


def load_dataset(config: DatasetConfig) -> tuple[list[Document], list[Query], dict[str, dict[str, int]] | None]:
    """Load documents, queries, and optionally qrels."""
    bundle = load_dataset_bundle(config)
    return bundle.documents, bundle.queries, bundle.qrels


def load_documents(config: DatasetConfig) -> list[Document]:
    """Load only documents from the configured backend."""
    return load_dataset_bundle(config).documents


def load_queries(config: DatasetConfig) -> list[Query]:
    """Load only queries from the configured backend."""
    return load_dataset_bundle(config).queries


def load_qrels(config: DatasetConfig) -> dict[str, dict[str, int]]:
    """Load qrels from the configured backend."""
    bundle = load_dataset_bundle(config)
    if bundle.qrels is None:
        raise ValueError(f"No qrels are available for dataset {bundle.metadata.dataset_name}")
    return bundle.qrels
