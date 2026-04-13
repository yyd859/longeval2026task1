from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

from longeval_sci.baselines.runner import run_baseline
from longeval_sci.config import DatasetConfig, ExperimentConfig, OutputConfig, RetrievalConfig, RerankConfig, RuntimeConfig, TemporalConfig
from longeval_sci.evaluation.longitudinal import write_longitudinal_outputs
from longeval_sci.io.dataset import SearchResult, load_dataset_bundle
from longeval_sci.rerank.cross_encoder import CrossEncoderReranker
from longeval_sci.retrieval.bm25 import BM25Retriever
from longeval_sci.retrieval.dense import DenseRetriever
from longeval_sci.temporal.intent import classify_temporal_intent
from longeval_sci.temporal.rerank import temporal_rerank_results


FIXTURE_DIR = Path("tests/fixtures")


def _fixture_config(run_name: str, pipeline: str) -> ExperimentConfig:
    return ExperimentConfig(
        run_name=run_name,
        pipeline=pipeline,
        dataset=DatasetConfig(
            backend="local_files",
            dataset_root="tests-fixture",
            snapshot_ids=["snapshot-1"],
            qrels_variant="dctr",
            corpus_path=str(FIXTURE_DIR / "corpus.jsonl"),
            queries_path=str(FIXTURE_DIR / "queries.jsonl"),
            qrels_path=str(FIXTURE_DIR / "qrels.tsv"),
            cache_dir=".cache/test_ir_datasets",
        ),
        retrieval=RetrievalConfig(
            type="dense" if "dense" in pipeline or "hybrid" in pipeline else "bm25",
            text_mode="title_abstract",
            top_k=100,
            index_root="outputs/test_indexes",
            model_name="intfloat/e5-base-v2",
            query_prefix="query: ",
            document_prefix="passage: ",
            candidate_k=100,
            lexical_text_mode="full_text",
            dense_text_mode="title_abstract",
        ),
        rerank=RerankConfig(enabled="rerank" in pipeline, candidate_k=100, top_k=100),
        temporal=TemporalConfig(),
        output=OutputConfig(output_root="outputs/test_runs", reports_root="outputs/test_reports"),
        runtime=RuntimeConfig(device="cpu", batch_size=8, seed=42),
    )


class LocalFixtureIntegrationTest(unittest.TestCase):
    def test_dataset_loading(self) -> None:
        bundle = load_dataset_bundle(_fixture_config("fixture", "custom_lexical_fulltext").dataset, "snapshot-1")
        self.assertEqual(len(bundle.documents), 5)
        self.assertEqual(len(bundle.queries), 2)
        self.assertTrue(bundle.metadata.has_qrels)

    def test_component_smoke(self) -> None:
        config = _fixture_config("fixture", "custom_dense_rerank")
        bundle = load_dataset_bundle(config.dataset, "snapshot-1")

        bm25 = BM25Retriever()
        bm25.build_index(bundle.documents, "title_abstract")
        self.assertTrue(bm25.search("dense retrieval scientific", 3))

        dense = DenseRetriever(
            model_name=config.retrieval.model_name,
            text_mode="title_abstract",
            normalize_embeddings=True,
            query_prefix=config.retrieval.query_prefix,
            document_prefix=config.retrieval.document_prefix,
        )
        embeddings = dense.encode_documents(bundle.documents)
        dense.build_index(embeddings, [document.doc_id for document in bundle.documents])
        self.assertTrue(dense.search("scientific retrieval dense models", 3))

        reranker = CrossEncoderReranker(config.rerank.model_name, text_mode="title_abstract")
        self.assertTrue(reranker.rerank("cross encoder reranking precision", bundle.documents, 3))

    def test_temporal_overlay_smoke(self) -> None:
        config = _fixture_config("fixture_temporal", "custom_lexical_fulltext")
        config.temporal = TemporalConfig(enabled=True, rerank_top_k=3)
        bundle = load_dataset_bundle(config.dataset, "snapshot-1")
        intent = classify_temporal_intent("latest survey of scientific retrieval")
        self.assertIn(intent.label, {"foundational", "current", "evolving", "survey"})

        for index, document in enumerate(bundle.documents, start=1):
            document.metadata["publishedDate"] = f"2025-0{index}-01"
            document.metadata["updatedDate"] = f"2025-0{index}-15"
        query_id = bundle.queries[0].query_id

        reranked = temporal_rerank_results(
            results=[
                SearchResult(query_id=query_id, doc_id=document.doc_id, score=float(10 - idx), rank=idx + 1, run_name="fixture")
                for idx, document in enumerate(bundle.documents[:3])
            ],
            bundle=bundle,
            config=config,
        )
        self.assertEqual(len(reranked), 3)
        self.assertEqual({result.rank for result in reranked}, {1, 2, 3})

    def test_baseline_suite_on_fixture(self) -> None:
        pipelines = [
            "custom_lexical_fulltext",
            "custom_dense_rerank",
            "custom_hybrid_union_rerank",
        ]
        if os.environ.get("JAVA_HOME"):
            pipelines.append("official_pyterrier")
        if os.environ.get("JAVA_HOME") and os.environ.get("LONGEVAL_RUN_OFFICIAL_DENSE_SMOKE") == "1":
            pipelines.append("official_pyterrier_dense")
        results = []
        for pipeline in pipelines:
            result = run_baseline(_fixture_config(pipeline, pipeline))
            self.assertEqual(len(result.snapshots), 1)
            self.assertIsNotNone(result.snapshots[0].metrics)
            results.append(result)
        artifacts = write_longitudinal_outputs(results, "outputs/test_reports")
        self.assertTrue(Path(artifacts["json"]).exists())
        self.assertTrue(Path(artifacts["csv"]).exists())
        self.assertTrue(Path(artifacts["markdown"]).exists())
        self.assertTrue(Path(artifacts["html"]).exists())


@unittest.skipUnless(
    importlib.util.find_spec("ir_datasets_longeval") is not None and os.environ.get("LONGEVAL_RUN_OFFICIAL_SMOKE") == "1",
    "official dataset smoke disabled",
)
class OfficialDatasetSmokeTest(unittest.TestCase):
    def test_snapshot_datasets_resolve(self) -> None:
        from longeval_sci.utils.paths import configure_ir_datasets_home

        configure_ir_datasets_home(".cache/test_ir_datasets")
        for snapshot_id in ["snapshot-1", "snapshot-2", "snapshot-3"]:
            bundle = load_dataset_bundle(
                DatasetConfig(
                    backend="ir_datasets_longeval",
                    dataset_root="longeval-sci-2026",
                    snapshot_ids=[snapshot_id],
                    qrels_variant="dctr",
                    cache_dir=".cache/test_ir_datasets",
                ),
                snapshot_id,
            )
            self.assertEqual(bundle.metadata.snapshot_id, snapshot_id)


if __name__ == "__main__":
    unittest.main()
