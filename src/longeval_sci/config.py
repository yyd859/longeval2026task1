"""Configuration loading for LongEval-Sci experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_SNAPSHOTS = ("snapshot-1", "snapshot-2", "snapshot-3")
DEFAULT_METRICS = ("ndcg_cut_10", "ndcg_cut_1000", "map", "recall_100", "recall_1000")


@dataclass(slots=True)
class DatasetConfig:
    backend: str = "local_snapshot_cache"
    dataset_root: str = ".cache/ir_datasets/longeval-sci-2026"
    snapshot_ids: list[str] = field(default_factory=lambda: list(DEFAULT_SNAPSHOTS))
    split: str | None = None
    qrels_variant: str = "dctr"
    cache_dir: str | None = ".cache/ir_datasets"
    load_fulltext: bool = False
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
    index_root: str | None = "indexes"
    model_name: str | None = None
    normalize_embeddings: bool = True
    query_prefix: str = ""
    document_prefix: str = ""
    candidate_k: int = 100
    lexical_text_mode: str = "full_text"
    dense_text_mode: str = "title_abstract"
    encode_chunk_size: int = 2048
    search_chunk_size: int = 50000
    service_base_url: str = "http://localhost:6543/v1"


@dataclass(slots=True)
class RerankConfig:
    enabled: bool = False
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    candidate_k: int = 100
    top_k: int = 100


@dataclass(slots=True)
class OutputConfig:
    output_root: str = "outputs"
    reports_root: str = "outputs/reports"
    run_filename: str = "run.txt"
    metrics_filename: str = "metrics.json"
    per_query_metrics_filename: str = "per_query_metrics.csv"


@dataclass(slots=True)
class RuntimeConfig:
    device: str = "cpu"
    batch_size: int = 32
    seed: int = 42
    require_gpu: bool = False
    pyterrier_memory_mb: int | None = 12288


@dataclass(slots=True)
class ExperimentConfig:
    run_name: str
    pipeline: str
    dataset: DatasetConfig
    retrieval: RetrievalConfig
    rerank: RerankConfig = field(default_factory=RerankConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    metrics: list[str] = field(default_factory=lambda: list(DEFAULT_METRICS))


def _resolve_path(base_dir: Path, value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())


def _deep_merge(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    merged = dict(parent)
    for key, value in child.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _simple_yaml_load(text: str) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load configs in this repository")
    return yaml.safe_load(text) or {}


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text) if yaml is not None else _simple_yaml_load(text)
    raw = raw or {}
    extends = raw.pop("extends", None)
    if extends:
        parent_path = (path.parent / extends).resolve()
        parent = _load_yaml(parent_path)
        raw = _deep_merge(parent, raw)
    return raw


def snapshot_dataset_name(dataset: DatasetConfig, snapshot_id: str) -> str:
    """Return the dataset identifier for a specific snapshot."""
    dataset_name = f"{dataset.dataset_root}/{snapshot_id}"
    if dataset.split:
        dataset_name = f"{dataset_name}/{dataset.split}"
    if dataset.backend == "ir_datasets_longeval" and dataset.qrels_variant:
        return f"{dataset_name}/{dataset.qrels_variant}"
    return dataset_name


def snapshot_output_name(dataset: DatasetConfig, snapshot_id: str) -> str:
    """Return the output folder name for a snapshot, including split when relevant."""
    if dataset.split:
        return f"{snapshot_id}-{dataset.split}"
    return snapshot_id


def baseline_output_dir(config: ExperimentConfig) -> Path:
    """Return the root output directory for a baseline."""
    return Path(config.output.output_root) / config.run_name


def baseline_reports_dir(config: ExperimentConfig) -> Path:
    """Return the reports directory for a baseline."""
    return Path(config.output.reports_root) / config.run_name


def snapshot_run_path(config: ExperimentConfig, snapshot_id: str) -> Path:
    return baseline_output_dir(config) / snapshot_output_name(config.dataset, snapshot_id) / config.output.run_filename


def snapshot_metrics_path(config: ExperimentConfig, snapshot_id: str) -> Path:
    return baseline_output_dir(config) / snapshot_output_name(config.dataset, snapshot_id) / config.output.metrics_filename


def snapshot_per_query_metrics_path(config: ExperimentConfig, snapshot_id: str) -> Path:
    return baseline_output_dir(config) / snapshot_output_name(config.dataset, snapshot_id) / config.output.per_query_metrics_filename


def snapshot_index_dir(config: ExperimentConfig, snapshot_id: str) -> Path | None:
    if not config.retrieval.index_root:
        return None
    return Path(config.retrieval.index_root) / config.run_name / snapshot_id


def load_config(path: str | Path) -> ExperimentConfig:
    """Load an experiment config from YAML."""
    config_path = Path(path).resolve()
    raw = _load_yaml(config_path)
    base_dir = config_path.parent.parent if config_path.parent.name == "configs" else config_path.parent

    dataset = DatasetConfig(**raw.get("dataset", {}))
    retrieval = RetrievalConfig(**raw["retrieval"])
    rerank = RerankConfig(**raw.get("rerank", {}))
    output = OutputConfig(**raw.get("output", {}))
    runtime = RuntimeConfig(**raw.get("runtime", {}))
    metrics = list(raw.get("metrics", list(DEFAULT_METRICS)))

    dataset.cache_dir = _resolve_path(base_dir, dataset.cache_dir)
    dataset.corpus_path = _resolve_path(base_dir, dataset.corpus_path)
    dataset.queries_path = _resolve_path(base_dir, dataset.queries_path)
    dataset.qrels_path = _resolve_path(base_dir, dataset.qrels_path)
    output.output_root = _resolve_path(base_dir, output.output_root) or output.output_root
    output.reports_root = _resolve_path(base_dir, output.reports_root) or output.reports_root
    retrieval.index_root = _resolve_path(base_dir, retrieval.index_root)

    return ExperimentConfig(
        run_name=raw["run_name"],
        pipeline=raw["pipeline"],
        dataset=dataset,
        retrieval=retrieval,
        rerank=rerank,
        output=output,
        runtime=runtime,
        metrics=metrics,
    )
