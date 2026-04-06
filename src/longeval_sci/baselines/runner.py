"""Official-baseline-aligned runner orchestration."""

from __future__ import annotations

import argparse
import gzip
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from longeval_sci.config import (
    ExperimentConfig,
    metrics_path_for_snapshot,
    per_query_metrics_path_for_snapshot,
    resolve_snapshot_id,
    run_path_for_snapshot,
    snapshot_output_dir,
)
from longeval_sci.evaluation.run_eval import evaluate_run
from longeval_sci.io.dataset import DatasetBundle, Document, Query, SearchResult, load_dataset_bundle
from longeval_sci.io.trec import write_trec_run
from longeval_sci.rerank.cross_encoder import CrossEncoderReranker
from longeval_sci.retrieval.bm25 import BM25Retriever
from longeval_sci.retrieval.dense import DenseRetriever
from longeval_sci.utils.logging import configure_logging
from longeval_sci.utils.paths import ensure_parent
from longeval_sci.utils.seed import set_seed


LOGGER = logging.getLogger(__name__)
DEFAULT_METRICS = ["ndcg_cut_10", "map", "recall_100", "recall_1000"]


@dataclass(slots=True)
class RunArtifacts:
    bundle: DatasetBundle
    run_path: Path
    metrics_path: Path
    per_query_metrics_path: Path


def _results_from_pairs(query_id: str, pairs: list[tuple[str, float]], run_name: str, top_k: int) -> list[SearchResult]:
    return [
        SearchResult(query_id=query_id, doc_id=doc_id, score=float(score), rank=rank, run_name=run_name)
        for rank, (doc_id, score) in enumerate(pairs[:top_k], start=1)
    ]


def _load_bundle(config: ExperimentConfig) -> RunArtifacts:
    configure_logging()
    set_seed(config.runtime.seed)
    bundle = load_dataset_bundle(config.dataset)
    snapshot_id = bundle.metadata.snapshot_id or resolve_snapshot_id(bundle.metadata.dataset_name, config.dataset.snapshot_id)
    run_path = run_path_for_snapshot(config, snapshot_id)
    metrics_path = metrics_path_for_snapshot(config, snapshot_id)
    per_query_metrics_path = per_query_metrics_path_for_snapshot(config, snapshot_id)
    LOGGER.info(
        "Loaded dataset %s with %s docs, %s queries, qrels=%s",
        bundle.metadata.dataset_name,
        len(bundle.documents),
        len(bundle.queries),
        bundle.metadata.has_qrels,
    )
    return RunArtifacts(bundle=bundle, run_path=run_path, metrics_path=metrics_path, per_query_metrics_path=per_query_metrics_path)


def _build_bm25(config: ExperimentConfig, documents: list[Document]) -> BM25Retriever:
    retriever = BM25Retriever()
    retriever.build_index(documents, config.retrieval.text_mode)
    if config.retrieval.index_dir:
        snapshot_id = resolve_snapshot_id(config.dataset.dataset_name, config.dataset.snapshot_id)
        retriever.save(str(Path(config.retrieval.index_dir) / snapshot_id / "bm25"))
    return retriever


def _build_dense(config: ExperimentConfig, documents: list[Document]) -> DenseRetriever:
    retriever = DenseRetriever(
        model_name=config.retrieval.model_name,
        text_mode=config.retrieval.text_mode,
        normalize_embeddings=config.retrieval.normalize_embeddings,
        query_prefix=config.retrieval.query_prefix,
        document_prefix=config.retrieval.document_prefix,
        batch_size=config.runtime.batch_size,
        device=config.runtime.device,
    )
    embeddings = retriever.encode_documents(documents)
    retriever.build_index(embeddings, [document.doc_id for document in documents])
    if config.retrieval.index_dir:
        snapshot_id = resolve_snapshot_id(config.dataset.dataset_name, config.dataset.snapshot_id)
        retriever.save(str(Path(config.retrieval.index_dir) / snapshot_id / "dense"))
    return retriever


def _run_bm25(config: ExperimentConfig, bundle: DatasetBundle) -> list[SearchResult]:
    retriever = _build_bm25(config, bundle.documents)
    results: list[SearchResult] = []
    for query in bundle.queries:
        pairs = retriever.search(query.text, config.retrieval.top_k)
        results.extend(_results_from_pairs(query.query_id, pairs, config.run_name, config.retrieval.top_k))
    return results


def _run_dense(config: ExperimentConfig, bundle: DatasetBundle) -> list[SearchResult]:
    retriever = _build_dense(config, bundle.documents)
    results: list[SearchResult] = []
    for query in bundle.queries:
        pairs = retriever.search(query.text, config.retrieval.top_k)
        results.extend(_results_from_pairs(query.query_id, pairs, config.run_name, config.retrieval.top_k))
    return results


def _run_dense_rerank(config: ExperimentConfig, bundle: DatasetBundle) -> list[SearchResult]:
    retriever = _build_dense(config, bundle.documents)
    reranker = CrossEncoderReranker(
        model_name=config.rerank.model_name,
        text_mode=config.retrieval.text_mode,
        device=config.runtime.device,
        batch_size=config.runtime.batch_size,
    )
    document_lookup = {document.doc_id: document for document in bundle.documents}
    results: list[SearchResult] = []
    candidate_k = config.rerank.candidate_k or config.retrieval.top_k
    output_k = config.rerank.top_k or config.retrieval.top_k
    for query in bundle.queries:
        pairs = retriever.search(query.text, candidate_k)
        candidates = [document_lookup[doc_id] for doc_id, _ in pairs if doc_id in document_lookup]
        reranked = reranker.rerank(query.text, candidates, output_k)
        results.extend(_results_from_pairs(query.query_id, reranked, config.run_name, output_k))
    return results


def run_pipeline(config: ExperimentConfig) -> RunArtifacts:
    """Run a configured baseline pipeline and write outputs."""
    artifacts = _load_bundle(config)
    pipeline = config.pipeline

    if pipeline == "bm25_pt":
        results = _run_bm25(config, artifacts.bundle)
    elif pipeline == "dense_pt":
        results = _run_dense(config, artifacts.bundle)
    elif pipeline == "dense_rerank":
        results = _run_dense_rerank(config, artifacts.bundle)
    else:
        raise ValueError(f"Unsupported pipeline: {pipeline}")

    ensure_parent(artifacts.run_path)
    write_trec_run(results, artifacts.run_path)
    LOGGER.info("Wrote %s results to %s", len(results), artifacts.run_path)

    if artifacts.bundle.metadata.has_qrels:
        metrics = evaluate_run(
            dataset_config=config.dataset,
            run_path=str(artifacts.run_path),
            metrics=DEFAULT_METRICS,
            metrics_path=str(artifacts.metrics_path),
            per_query_metrics_path=str(artifacts.per_query_metrics_path),
        )
        LOGGER.info("Metrics: %s", metrics)
    else:
        LOGGER.info("No qrels available for %s; skipping evaluation", artifacts.bundle.metadata.dataset_name)

    return artifacts


def gzip_run_file(run_path: Path) -> Path:
    """Create a gzipped copy of a run file for submission packaging."""
    gz_path = run_path.with_suffix(run_path.suffix + ".gz")
    with run_path.open("rb") as source, gzip.open(gz_path, "wb") as target:
        target.write(source.read())
    return gz_path


def _pyterrier_status() -> tuple[bool, str]:
    try:
        import pyterrier as pt

        if not pt.started():
            try:
                pt.init()
            except Exception as exc:
                return False, f"PyTerrier import succeeded but initialization failed: {exc}"
        return True, "PyTerrier available"
    except Exception as exc:
        return False, f"PyTerrier unavailable; falling back to internal retrievers: {exc}"


def build_config_from_args(
    *,
    run_name: str,
    pipeline: str,
    dataset_name: str,
    snapshot_id: str | None,
    qrels_variant: str | None,
    output_dir: str,
    index_dir: str | None,
    device: str,
    batch_size: int,
    top_k: int,
    text_mode: str,
    model_name: str | None,
    rerank_model: str | None,
    candidate_k: int,
) -> ExperimentConfig:
    from longeval_sci.config import DatasetConfig, OutputConfig, RetrievalConfig, RerankConfig, RuntimeConfig

    rerank_enabled = pipeline == "dense_rerank"
    return ExperimentConfig(
        run_name=run_name,
        pipeline=pipeline,
        dataset=DatasetConfig(
            backend="ir_datasets_longeval",
            dataset_name=dataset_name,
            snapshot_id=snapshot_id,
            qrels_variant=qrels_variant,
        ),
        retrieval=RetrievalConfig(
            type="dense" if pipeline != "bm25_pt" else "bm25",
            text_mode=text_mode,
            top_k=top_k,
            index_dir=index_dir,
            model_name=model_name,
            normalize_embeddings=True,
            query_prefix="query: " if pipeline != "bm25_pt" else "",
            document_prefix="passage: " if pipeline != "bm25_pt" else "",
        ),
        rerank=RerankConfig(
            enabled=rerank_enabled,
            model_name=rerank_model or "cross-encoder/ms-marco-MiniLM-L-12-v2",
            candidate_k=candidate_k,
            top_k=top_k,
        ),
        output=OutputConfig(output_dir=output_dir),
        runtime=RuntimeConfig(device=device, batch_size=batch_size),
    )


def _common_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--dataset", required=True, help="Dataset id, e.g. longeval-sci-2026/snapshot-1")
    parser.add_argument("--snapshot-id", default=None, help="Optional explicit snapshot id")
    parser.add_argument("--output-dir", required=True, help="Root output directory")
    parser.add_argument("--index-dir", default=None, help="Optional index root directory")
    parser.add_argument("--qrels-variant", default="dctr", choices=["raw", "dctr"], help="Qrels variant")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--text-mode", default="title_abstract")
    parser.add_argument("--candidate-k", type=int, default=100)
    parser.add_argument("--model-name", default="intfloat/e5-base-v2")
    parser.add_argument("--rerank-model", default="cross-encoder/ms-marco-MiniLM-L-12-v2")
    parser.add_argument("--gzip-run", action="store_true", help="Also write run.txt.gz for submission packaging")
    return parser


def main_run_baseline_pyterrier() -> None:
    configure_logging()
    parser = _common_parser("Run the official-style lexical baseline")
    parser.set_defaults(model_name=None)
    args = parser.parse_args()
    available, message = _pyterrier_status()
    LOGGER.info(message)
    config = build_config_from_args(
        run_name="bm25_pt",
        pipeline="bm25_pt",
        dataset_name=args.dataset,
        snapshot_id=args.snapshot_id,
        qrels_variant=args.qrels_variant,
        output_dir=args.output_dir,
        index_dir=args.index_dir,
        device=args.device,
        batch_size=args.batch_size,
        top_k=args.top_k,
        text_mode=args.text_mode,
        model_name=None,
        rerank_model=None,
        candidate_k=args.candidate_k,
    )
    artifacts = run_pipeline(config)
    if args.gzip_run:
        gzip_run_file(artifacts.run_path)


def main_run_baseline_pyterrier_dense() -> None:
    configure_logging()
    parser = _common_parser("Run the official-style dense baseline")
    args = parser.parse_args()
    available, message = _pyterrier_status()
    LOGGER.info(message)
    config = build_config_from_args(
        run_name="dense_pt",
        pipeline="dense_pt",
        dataset_name=args.dataset,
        snapshot_id=args.snapshot_id,
        qrels_variant=args.qrels_variant,
        output_dir=args.output_dir,
        index_dir=args.index_dir,
        device=args.device,
        batch_size=args.batch_size,
        top_k=args.top_k,
        text_mode=args.text_mode,
        model_name=args.model_name,
        rerank_model=args.rerank_model,
        candidate_k=args.candidate_k,
    )
    artifacts = run_pipeline(config)
    if args.gzip_run:
        gzip_run_file(artifacts.run_path)


def main_run_pipeline() -> None:
    from longeval_sci.config import load_config

    configure_logging()
    parser = argparse.ArgumentParser(description="Run a configured baseline pipeline")
    parser.add_argument("--config", required=True)
    parser.add_argument("--pipeline", choices=["bm25_pt", "dense_pt", "dense_rerank"], default=None)
    parser.add_argument("--gzip-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.pipeline:
        config = deepcopy(config)
        config.pipeline = args.pipeline
    artifacts = run_pipeline(config)
    if args.gzip_run:
        gzip_run_file(artifacts.run_path)
