"""Configuration loading for LongEval-Sci experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised in lightweight environments
    yaml = None


DEFAULT_SNAPSHOTS = ("snapshot-1", "snapshot-2", "snapshot-3")


@dataclass(slots=True)
class DatasetConfig:
    backend: str = "ir_datasets_longeval"
    dataset_name: str = "longeval-sci-2026/snapshot-1"
    snapshot_id: str | None = None
    qrels_variant: str | None = "dctr"
    corpus_path: str | None = None
    queries_path: str | None = None
    qrels_path: str | None = None
    corpus_format: str | None = None
    queries_format: str | None = None
    qrels_format: str | None = None
    corpus_field_map: dict[str, str] = field(default_factory=dict)
    query_field_map: dict[str, str] = field(default_factory=dict)
    qrels_field_map: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalConfig:
    type: str
    text_mode: str = "title_abstract"
    top_k: int = 100
    index_dir: str | None = None
    model_name: str | None = None
    normalize_embeddings: bool = True
    query_prefix: str = ""
    document_prefix: str = ""
    candidate_k: int = 100
    bm25: dict[str, Any] = field(default_factory=dict)
    dense: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RerankConfig:
    enabled: bool = False
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    candidate_k: int = 100
    top_k: int | None = None


@dataclass(slots=True)
class OutputConfig:
    output_dir: str = "outputs"
    run_filename: str = "run.txt"
    metrics_filename: str = "metrics.json"
    per_query_metrics_filename: str = "per_query_metrics.csv"
    longitudinal_json_filename: str = "longitudinal_summary.json"
    longitudinal_csv_filename: str = "longitudinal_summary.csv"


@dataclass(slots=True)
class RuntimeConfig:
    device: str = "cpu"
    batch_size: int = 32
    seed: int = 42
    require_gpu: bool = False


@dataclass(slots=True)
class ExperimentConfig:
    run_name: str
    pipeline: str
    dataset: DatasetConfig
    retrieval: RetrievalConfig
    rerank: RerankConfig
    output: OutputConfig
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)


def _resolve_path(base_dir: Path, value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _simple_yaml_load(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if ":" not in stripped:
            raise ValueError(f"Unsupported YAML line: {raw_line}")
        key, value = stripped.split(":", maxsplit=1)
        key = key.strip()
        value = value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"Invalid YAML indentation near line: {raw_line}")

        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _simple_yaml_load(text)


def resolve_snapshot_id(dataset_name: str, snapshot_id: str | None = None) -> str:
    """Infer the snapshot identifier for an experiment."""
    if snapshot_id:
        return snapshot_id
    for candidate in DEFAULT_SNAPSHOTS:
        if candidate in dataset_name:
            return candidate
    return "snapshot-unknown"


def resolve_dataset_name(dataset: DatasetConfig) -> str:
    """Resolve the canonical dataset identifier including qrels variant when needed."""
    dataset_name = dataset.dataset_name
    if dataset.backend != "ir_datasets_longeval":
        return dataset_name
    if dataset.qrels_variant and not dataset_name.endswith(f"/{dataset.qrels_variant}"):
        if dataset_name.endswith("/sci") or dataset_name.endswith("/snapshot-1") or dataset_name.endswith("/snapshot-2") or dataset_name.endswith("/snapshot-3"):
            return f"{dataset_name}/{dataset.qrels_variant}"
    return dataset_name


def snapshot_output_dir(config: ExperimentConfig, snapshot_id: str | None = None) -> Path:
    """Return the output directory for a snapshot."""
    resolved_snapshot = resolve_snapshot_id(config.dataset.dataset_name, snapshot_id or config.dataset.snapshot_id)
    return Path(config.output.output_dir) / resolved_snapshot


def run_path_for_snapshot(config: ExperimentConfig, snapshot_id: str | None = None) -> Path:
    """Return the run file path for a snapshot."""
    return snapshot_output_dir(config, snapshot_id) / config.output.run_filename


def metrics_path_for_snapshot(config: ExperimentConfig, snapshot_id: str | None = None) -> Path:
    """Return the aggregate metrics path for a snapshot."""
    return snapshot_output_dir(config, snapshot_id) / config.output.metrics_filename


def per_query_metrics_path_for_snapshot(config: ExperimentConfig, snapshot_id: str | None = None) -> Path:
    """Return the per-query metrics path for a snapshot."""
    return snapshot_output_dir(config, snapshot_id) / config.output.per_query_metrics_filename


def load_config(path: str | Path) -> ExperimentConfig:
    """Load an experiment config from YAML."""
    config_path = Path(path).resolve()
    raw = _load_yaml(config_path)

    dataset = DatasetConfig(**raw["dataset"])
    retrieval = RetrievalConfig(**raw["retrieval"])
    rerank = RerankConfig(**raw.get("rerank", {}))
    output = OutputConfig(**raw.get("output", {}))
    runtime = RuntimeConfig(**raw.get("runtime", {}))

    base_dir = config_path.parent.parent if config_path.parent.name == "configs" else config_path.parent
    dataset.corpus_path = _resolve_path(base_dir, dataset.corpus_path)
    dataset.queries_path = _resolve_path(base_dir, dataset.queries_path)
    dataset.qrels_path = _resolve_path(base_dir, dataset.qrels_path)
    output.output_dir = _resolve_path(base_dir, output.output_dir) or output.output_dir
    retrieval.index_dir = _resolve_path(base_dir, retrieval.index_dir)

    if retrieval.bm25.get("index_dir"):
        retrieval.bm25["index_dir"] = _resolve_path(base_dir, retrieval.bm25["index_dir"])
    if retrieval.dense.get("index_dir"):
        retrieval.dense["index_dir"] = _resolve_path(base_dir, retrieval.dense["index_dir"])

    if not dataset.snapshot_id:
        dataset.snapshot_id = resolve_snapshot_id(dataset.dataset_name)

    return ExperimentConfig(
        run_name=raw["run_name"],
        pipeline=raw.get("pipeline", retrieval.type),
        dataset=dataset,
        retrieval=retrieval,
        rerank=rerank,
        output=output,
        runtime=runtime,
    )
