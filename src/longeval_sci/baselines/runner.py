"""Baseline orchestration for LongEval-Sci."""

from __future__ import annotations

import logging
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from longeval_sci.config import (
    ExperimentConfig,
    baseline_output_dir,
    snapshot_index_dir,
    snapshot_metrics_path,
    snapshot_per_query_metrics_path,
    snapshot_run_path,
)
from longeval_sci.evaluation.run_eval import evaluate_run
from longeval_sci.io.dataset import DatasetBundle, Document, SearchResult, iter_snapshot_cache_text_records, load_dataset_bundle
from longeval_sci.io.trec import write_trec_run
from longeval_sci.preprocess.fields import build_document_text
from longeval_sci.rerank.cross_encoder import CrossEncoderReranker
from longeval_sci.retrieval.bm25 import BM25Retriever
from longeval_sci.retrieval.dense import DenseRetriever
from longeval_sci.retrieval.hybrid import union_results
from longeval_sci.utils.logging import configure_logging
from longeval_sci.utils.paths import configure_pyterrier_home, ensure_dir, ensure_parent
from longeval_sci.utils.seed import set_seed


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SnapshotRunResult:
    snapshot_id: str
    dataset_name: str
    run_path: Path
    metrics_path: Path
    per_query_metrics_path: Path
    metrics: dict[str, float] | None
    execution_backend: str
    doc_count: int
    query_count: int


@dataclass(slots=True)
class BaselineRunResult:
    config: ExperimentConfig
    snapshots: list[SnapshotRunResult]


def _write_metrics_status(
    config: ExperimentConfig,
    bundle: DatasetBundle,
    snapshot_id: str,
    metrics_path: Path,
    per_query_path: Path,
) -> None:
    ensure_parent(metrics_path)
    payload = {
        "dataset_name": bundle.metadata.dataset_name,
        "snapshot_id": snapshot_id,
        "metrics": None,
        "status": "skipped",
        "reason": "qrels_unavailable",
    }
    with metrics_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    ensure_parent(per_query_path)
    with per_query_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("query_id,status,reason\n")


def _ensure_pyterrier_started(memory_limit_mb: int | None = 12288) -> Any:
    try:
        import pyterrier as pt  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyTerrier is not installed in this environment.") from exc

    configure_pyterrier_home()
    try:
        pt.java.set_memory_limit(memory_limit_mb)
        if not pt.java.started():
            pt.java.init()
    except Exception as exc:
        raise RuntimeError(
            "PyTerrier could not start. Ensure `pyterrier[java]` is installed and JAVA_HOME points to a working JDK."
        ) from exc
    return pt


def _pyterrier_to_results(run_frame: Any, run_name: str, top_k: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    grouped_rows: dict[str, list[object]] = {}
    for row in run_frame.itertuples(index=False):
        grouped_rows.setdefault(str(getattr(row, "qid")), []).append(row)

    for query_id, rows in grouped_rows.items():
        ranked_rows = sorted(
            rows,
            key=lambda row: (-float(getattr(row, "score")), str(getattr(row, "docno"))),
        )
        for rank, row in enumerate(ranked_rows[:top_k], start=1):
            results.append(
                SearchResult(
                    query_id=query_id,
                    doc_id=str(getattr(row, "docno")),
                    score=float(getattr(row, "score")),
                    rank=rank,
                    run_name=run_name,
                )
            )
    return results


def _results_from_pairs(query_id: str, pairs: list[tuple[str, float]], run_name: str, top_k: int) -> list[SearchResult]:
    return [
        SearchResult(query_id=query_id, doc_id=doc_id, score=float(score), rank=rank, run_name=run_name)
        for rank, (doc_id, score) in enumerate(pairs[:top_k], start=1)
    ]


def _build_bm25(config: ExperimentConfig, documents: list[Document], snapshot_id: str, text_mode: str) -> BM25Retriever:
    retriever = BM25Retriever()
    retriever.build_index(documents, text_mode)
    index_dir = snapshot_index_dir(config, snapshot_id)
    if index_dir is not None:
        retriever.save(str(index_dir / f"bm25_{text_mode}"))
    return retriever


def _build_dense(config: ExperimentConfig, documents: list[Document], snapshot_id: str, text_mode: str) -> DenseRetriever:
    retriever = DenseRetriever(
        model_name=config.retrieval.model_name,
        text_mode=text_mode,
        normalize_embeddings=config.retrieval.normalize_embeddings,
        query_prefix=config.retrieval.query_prefix,
        document_prefix=config.retrieval.document_prefix,
        batch_size=config.runtime.batch_size,
        device=config.runtime.device,
        encode_chunk_size=config.retrieval.encode_chunk_size,
        search_chunk_size=config.retrieval.search_chunk_size,
    )
    index_dir = snapshot_index_dir(config, snapshot_id)
    if index_dir is None:
        embeddings = retriever.encode_documents(documents)
        retriever.build_index(embeddings, [document.doc_id for document in documents])
        return retriever

    dense_index_dir = index_dir / f"dense_{text_mode}"
    metadata_path = dense_index_dir / "metadata.json"
    index_path = dense_index_dir / "index.faiss"
    numpy_index_path = dense_index_dir / "index.npy"
    if metadata_path.exists() and (index_path.exists() or numpy_index_path.exists()):
        LOGGER.info("Loading existing dense index from %s", dense_index_dir)
        retriever.load(dense_index_dir)
        return retriever

    retriever.build_index_from_documents(documents, dense_index_dir)
    return retriever


def _run_lexical(bundle: DatasetBundle, config: ExperimentConfig, snapshot_id: str, text_mode: str) -> list[SearchResult]:
    retriever = _build_bm25(config, bundle.documents, snapshot_id, text_mode)
    results: list[SearchResult] = []
    for query in bundle.queries:
        pairs = retriever.search(query.text, config.retrieval.top_k)
        results.extend(_results_from_pairs(query.query_id, pairs, config.run_name, config.retrieval.top_k))
    return results


def _run_official_pyterrier(bundle: DatasetBundle, config: ExperimentConfig, snapshot_id: str) -> list[SearchResult]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("official_pyterrier requires pandas and pyterrier to be installed") from exc

    pt = _ensure_pyterrier_started(config.runtime.pyterrier_memory_mb)

    index_dir = snapshot_index_dir(config, snapshot_id)
    if index_dir is None:
        raise ValueError("official_pyterrier requires retrieval.index_root to be configured")
    pt_index_dir = ensure_dir(index_dir / "pyterrier_index")

    if not (pt_index_dir / "data.properties").exists():
        indexer = pt.IterDictIndexer(
            str(pt_index_dir.resolve()),
            overwrite=True,
            meta={"docno": 100, "text": 20480},
        )
        docs = (
            {
                "docno": document.doc_id,
                "text": build_document_text(document, config.retrieval.text_mode),
            }
            for document in bundle.documents
        )
        indexer.index(docs)

    index = pt.IndexFactory.of(str(pt_index_dir.resolve()))
    topics = pd.DataFrame([{"qid": query.query_id, "query": query.text} for query in bundle.queries])
    tokeniser = pt.java.autoclass("org.terrier.indexing.tokenisation.Tokeniser").getTokeniser()
    topics["query"] = topics["query"].apply(lambda value: " ".join(tokeniser.getTokens(value)))
    run_frame = pt.terrier.Retriever(index, wmodel="BM25")(topics)
    return _pyterrier_to_results(run_frame, config.run_name, config.retrieval.top_k)


def _run_snapshot_cache_pyterrier_lexical(
    bundle: DatasetBundle,
    config: ExperimentConfig,
    snapshot_id: str,
    text_mode: str,
    run_name: str,
    top_k: int,
) -> list[SearchResult]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("PyTerrier lexical streaming requires pandas and pyterrier to be installed") from exc

    pt = _ensure_pyterrier_started(config.runtime.pyterrier_memory_mb)
    index_dir = snapshot_index_dir(config, snapshot_id)
    if index_dir is None:
        raise ValueError("PyTerrier lexical streaming requires retrieval.index_root to be configured")
    pt_index_dir = ensure_dir(index_dir / f"pyterrier_index_{text_mode}")

    if not (pt_index_dir / "data.properties").exists():
        indexer = pt.IterDictIndexer(
            str(pt_index_dir.resolve()),
            overwrite=True,
            meta={"docno": 100, "text": 20480},
        )
        indexer.index(iter_snapshot_cache_text_records(config.dataset, snapshot_id, text_mode))

    index = pt.IndexFactory.of(str(pt_index_dir.resolve()))
    topics = pd.DataFrame([{"qid": query.query_id, "query": query.text} for query in bundle.queries])
    tokeniser = pt.java.autoclass("org.terrier.indexing.tokenisation.Tokeniser").getTokeniser()
    topics["query"] = topics["query"].apply(lambda value: " ".join(tokeniser.getTokens(value)))
    run_frame = pt.terrier.Retriever(index, wmodel="BM25")(topics)
    return _pyterrier_to_results(run_frame, run_name, top_k)


def _run_official_pyterrier_dense(bundle: DatasetBundle, config: ExperimentConfig, snapshot_id: str) -> list[SearchResult]:
    try:
        import numpy as np
        import pandas as pd
        from openai import OpenAI
        from pyterrier_dr import FlexIndex
    except ImportError as exc:
        raise RuntimeError(
            "official_pyterrier_dense requires pyterrier_dr and openai. "
            "Install them and start the embedding service before running this baseline."
        ) from exc

    pt = _ensure_pyterrier_started(config.runtime.pyterrier_memory_mb)

    transformer_base = cast(type[Any], pt.Transformer)

    class VLLMEncoder(transformer_base):
        def __init__(self, model_name: str, base_url: str, batch_size: int) -> None:
            super().__init__()
            self.client = OpenAI(base_url=base_url, api_key="vllm-token")
            self.model_name = model_name
            self.batch_size = batch_size

        def transform(self, input_df: Any) -> Any:
            is_query = "query" in input_df.columns
            text_column = "query" if is_query else "text"
            output_column = "query_vec" if is_query else "doc_vec"
            texts = input_df[text_column].tolist()
            if is_query:
                texts = [f"Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:{text}" for text in texts]

            embeddings = []
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start:start + self.batch_size]
                response = self.client.embeddings.create(input=batch, model=self.model_name)
                embeddings.append(np.array([item.embedding for item in response.data], dtype="float32"))
            input_df[output_column] = list(np.vstack(embeddings))
            return input_df

    index_dir = snapshot_index_dir(config, snapshot_id)
    if index_dir is None:
        raise ValueError("official_pyterrier_dense requires retrieval.index_root to be configured")
    pt_index_dir = ensure_dir(index_dir / "pyterrier_dense_index")
    flex_path = pt_index_dir / "my_index.flex"
    encoder = VLLMEncoder(
        model_name=config.retrieval.model_name or "Qwen/Qwen3-Embedding-4B",
        base_url=config.retrieval.service_base_url,
        batch_size=config.runtime.batch_size,
    )

    if not flex_path.exists():
        index = FlexIndex(flex_path)
        docs = (
            {
                "docno": document.doc_id,
                "text": build_document_text(document, config.retrieval.text_mode),
            }
            for document in bundle.documents
        )
        (encoder >> index).index(docs)

    index = FlexIndex(flex_path)
    topics = pd.DataFrame([{"qid": query.query_id, "query": query.text} for query in bundle.queries])
    run_frame = (encoder >> index.retriever())(topics)
    return _pyterrier_to_results(run_frame, config.run_name, config.retrieval.top_k)


def _run_dense(bundle: DatasetBundle, config: ExperimentConfig, snapshot_id: str, text_mode: str) -> list[SearchResult]:
    retriever = _build_dense(config, bundle.documents, snapshot_id, text_mode)
    results: list[SearchResult] = []
    for query in bundle.queries:
        pairs = retriever.search(query.text, config.retrieval.top_k)
        results.extend(_results_from_pairs(query.query_id, pairs, config.run_name, config.retrieval.top_k))
    return results


def _run_dense_rerank(bundle: DatasetBundle, config: ExperimentConfig, snapshot_id: str) -> list[SearchResult]:
    retriever = _build_dense(config, bundle.documents, snapshot_id, config.retrieval.dense_text_mode)
    reranker = CrossEncoderReranker(
        model_name=config.rerank.model_name,
        text_mode=config.retrieval.dense_text_mode,
        device=config.runtime.device,
        batch_size=config.runtime.batch_size,
    )
    doc_lookup = {document.doc_id: document for document in bundle.documents}
    results: list[SearchResult] = []
    candidate_k = config.rerank.candidate_k
    output_k = config.rerank.top_k
    for query in bundle.queries:
        pairs = retriever.search(query.text, candidate_k)
        candidates = [doc_lookup[doc_id] for doc_id, _ in pairs if doc_id in doc_lookup]
        reranked = reranker.rerank(query.text, candidates, output_k)
        results.extend(_results_from_pairs(query.query_id, reranked, config.run_name, output_k))
    return results


def _run_hybrid_rerank(bundle: DatasetBundle, config: ExperimentConfig, snapshot_id: str) -> list[SearchResult]:
    if config.dataset.backend == "local_snapshot_cache" and config.retrieval.lexical_text_mode == "full_text":
        lexical_results = _run_snapshot_cache_pyterrier_lexical(
            bundle,
            config,
            snapshot_id,
            config.retrieval.lexical_text_mode,
            f"{config.run_name}_lexical",
            config.rerank.candidate_k,
        )
        lexical_lookup: dict[str, list[tuple[str, float]]] = {}
        for result in lexical_results:
            lexical_lookup.setdefault(result.query_id, []).append((result.doc_id, result.score))
    else:
        bm25 = _build_bm25(config, bundle.documents, snapshot_id, config.retrieval.lexical_text_mode)
        lexical_lookup = {}
        for query in bundle.queries:
            lexical_lookup[query.query_id] = bm25.search(query.text, config.rerank.candidate_k)

    dense = _build_dense(config, bundle.documents, snapshot_id, config.retrieval.dense_text_mode)
    reranker = CrossEncoderReranker(
        model_name=config.rerank.model_name,
        text_mode=config.retrieval.dense_text_mode,
        device=config.runtime.device,
        batch_size=config.runtime.batch_size,
    )
    doc_lookup = {document.doc_id: document for document in bundle.documents}
    results: list[SearchResult] = []
    candidate_k = config.rerank.candidate_k
    output_k = config.rerank.top_k
    for query in bundle.queries:
        lexical_pairs = lexical_lookup.get(query.query_id, [])
        dense_pairs = dense.search(query.text, candidate_k)
        candidate_ids = union_results(lexical_pairs, dense_pairs, top_k=candidate_k * 2)
        candidates = [doc_lookup[doc_id] for doc_id in candidate_ids if doc_id in doc_lookup]
        reranked = reranker.rerank(query.text, candidates, output_k)
        results.extend(_results_from_pairs(query.query_id, reranked, config.run_name, output_k))
    return results


def _pyterrier_status() -> str:
    try:
        _ensure_pyterrier_started()
        return "pyterrier"
    except Exception:
        return "internal_fallback"


def _pipeline_runner(config: ExperimentConfig, bundle: DatasetBundle, snapshot_id: str) -> tuple[list[SearchResult], str]:
    pipeline = config.pipeline
    if pipeline == "official_pyterrier":
        return _run_official_pyterrier(bundle, config, snapshot_id), _pyterrier_status()
    if pipeline == "official_pyterrier_dense":
        return _run_official_pyterrier_dense(bundle, config, snapshot_id), _pyterrier_status()
    if pipeline == "custom_lexical_fulltext":
        if config.dataset.backend == "local_snapshot_cache":
            return (
                _run_snapshot_cache_pyterrier_lexical(
                    bundle,
                    config,
                    snapshot_id,
                    "full_text",
                    config.run_name,
                    config.retrieval.top_k,
                ),
                "pyterrier",
            )
        return _run_lexical(bundle, config, snapshot_id, "full_text"), "internal"
    if pipeline == "custom_dense_rerank":
        return _run_dense_rerank(bundle, config, snapshot_id), "internal"
    if pipeline == "custom_hybrid_union_rerank":
        return _run_hybrid_rerank(bundle, config, snapshot_id), "internal"
    raise ValueError(f"Unsupported pipeline: {pipeline}")


def run_baseline(config: ExperimentConfig) -> BaselineRunResult:
    """Run one baseline across all configured snapshots."""
    configure_logging()
    set_seed(config.runtime.seed)
    ensure_dir(baseline_output_dir(config))

    snapshot_results: list[SnapshotRunResult] = []
    for snapshot_id in config.dataset.snapshot_ids:
        bundle = load_dataset_bundle(config.dataset, snapshot_id)
        LOGGER.info(
            "Running %s on %s with %s documents and %s queries",
            config.run_name,
            bundle.metadata.dataset_name,
            len(bundle.documents),
            len(bundle.queries),
        )
        results, backend = _pipeline_runner(config, bundle, snapshot_id)
        run_path = snapshot_run_path(config, snapshot_id)
        metrics_path = snapshot_metrics_path(config, snapshot_id)
        per_query_path = snapshot_per_query_metrics_path(config, snapshot_id)
        ensure_parent(run_path)
        write_trec_run(results, run_path)

        metrics: dict[str, float] | None = None
        if bundle.metadata.has_qrels:
            metrics = evaluate_run(
                dataset_config=config.dataset,
                snapshot_id=snapshot_id,
                run_path=str(run_path),
                metrics=config.metrics,
                metrics_path=str(metrics_path),
                per_query_metrics_path=str(per_query_path),
            )
        else:
            _write_metrics_status(config, bundle, snapshot_id, metrics_path, per_query_path)
        snapshot_results.append(
            SnapshotRunResult(
                snapshot_id=snapshot_id,
                dataset_name=bundle.metadata.dataset_name,
                run_path=run_path,
                metrics_path=metrics_path,
                per_query_metrics_path=per_query_path,
                metrics=metrics,
                execution_backend=backend,
                doc_count=len(bundle.documents),
                query_count=len(bundle.queries),
            )
        )
    return BaselineRunResult(config=config, snapshots=snapshot_results)


def clone_for_snapshot(config: ExperimentConfig, snapshot_id: str) -> ExperimentConfig:
    """Create a one-snapshot copy of a config."""
    cloned = deepcopy(config)
    cloned.dataset.snapshot_ids = [snapshot_id]
    return cloned


def clone_for_train_eval(
    config: ExperimentConfig,
    qrels_variant: str = "dctr",
    queries_path: str | None = None,
    qrels_path: str | None = None,
) -> ExperimentConfig:
    """Create a snapshot-1 train-eval copy of a config."""
    cloned = deepcopy(config)
    cloned.dataset.snapshot_ids = ["snapshot-1"]
    cloned.dataset.split = "train"
    cloned.dataset.qrels_variant = qrels_variant
    cloned.dataset.queries_path = queries_path or ".cache/ir_datasets/longeval-sci-2026/task1_longeval_adhoc-queries-snapshot-train.tsv"
    cloned.dataset.qrels_path = qrels_path or f".cache/ir_datasets/longeval-sci-2026/task1_longeval_adhoc-qrels-snapshot-train-{qrels_variant}.txt"
    return cloned
