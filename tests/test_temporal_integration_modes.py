from __future__ import annotations

import unittest

from longeval_sci.config import DatasetConfig, ExperimentConfig, RetrievalConfig, TemporalConfig
from longeval_sci.io.dataset import DatasetBundle, DatasetMetadata, Document, Query, SearchResult
from longeval_sci.temporal.citations import CitationTemporalFeatures
from longeval_sci.temporal.query_profile import build_query_evidence_profile
from longeval_sci.temporal.rerank import temporal_rerank_results
from longeval_sci.temporal.router import classify_evidence_route


def _fixture_inputs(query_text: str):
    documents = [
        Document(
            doc_id=f"D{index}",
            title=f"Document {index}",
            abstract="scientific retrieval",
            metadata={
                "publishedDate": f"2025-0{index}-01",
                "updatedDate": f"2025-0{index}-15",
            },
        )
        for index in range(1, 4)
    ]
    bundle = DatasetBundle(
        documents=documents,
        queries=[Query(query_id="Q1", text=query_text)],
        qrels=None,
        metadata=DatasetMetadata(
            backend="fixture",
            dataset_name="fixture",
            snapshot_id="snapshot-1",
            qrels_variant="dctr",
        ),
    )
    results = [
        SearchResult(query_id="Q1", doc_id=document.doc_id, score=float(10 - index), rank=index, run_name="fixture")
        for index, document in enumerate(documents, start=1)
    ]
    config = ExperimentConfig(
        run_name="fixture",
        pipeline="fixture",
        dataset=DatasetConfig(),
        retrieval=RetrievalConfig(type="bm25", text_mode="title_abstract", top_k=3),
    )
    return config, bundle, results


class TemporalIntegrationModeTest(unittest.TestCase):
    def test_evidence_router_classifier(self) -> None:
        self.assertEqual(classify_evidence_route("latest neural retrieval updates in 2026"), "temporal")
        self.assertEqual(classify_evidence_route("seminal influential retrieval papers"), "citation")
        self.assertEqual(classify_evidence_route("recent survey comparing retrieval benchmarks"), "mixed")

    def test_query_profile_alpha_beta_rules(self) -> None:
        config, bundle, results = _fixture_inputs("neural retrieval methods")
        doc_lookup = {document.doc_id: document for document in bundle.documents}
        temporal_profile = build_query_evidence_profile(
            query_text="latest retrieval updates in 2026",
            ranked_results=results,
            doc_lookup=doc_lookup,
            citation_lookup={},
            config=config.temporal,
        )
        self.assertEqual(temporal_profile.temporal_alpha, 0.25)

        concentrated_profile = build_query_evidence_profile(
            query_text="neural retrieval methods",
            ranked_results=results,
            doc_lookup=doc_lookup,
            citation_lookup={},
            config=config.temporal,
        )
        self.assertEqual(concentrated_profile.temporal_alpha, 0.15)

        citation_profile = build_query_evidence_profile(
            query_text="seminal retrieval benchmark",
            ranked_results=results,
            doc_lookup=doc_lookup,
            citation_lookup={},
            config=config.temporal,
        )
        self.assertEqual(citation_profile.citation_beta, 0.25)

        high_citation_profile = build_query_evidence_profile(
            query_text="retrieval methods",
            ranked_results=results,
            doc_lookup=doc_lookup,
            citation_lookup={
                "D1": CitationTemporalFeatures(total_inbound_citations=20),
                "D2": CitationTemporalFeatures(total_inbound_citations=20),
            },
            config=config.temporal,
        )
        self.assertEqual(high_citation_profile.citation_beta, 0.12)

        bundle.documents[0].metadata["publishedDate"] = "2015-01-01"
        bundle.documents[1].metadata["publishedDate"] = "2016-01-01"
        bundle.documents[2].metadata["publishedDate"] = "2025-01-01"
        old_span_profile = build_query_evidence_profile(
            query_text="retrieval methods",
            ranked_results=results,
            doc_lookup=doc_lookup,
            citation_lookup={},
            config=config.temporal,
        )
        self.assertEqual(old_span_profile.citation_beta, 0.12)

    def test_citation_only_missing_data_is_noop(self) -> None:
        config, bundle, results = _fixture_inputs("seminal influential retrieval papers")
        config.temporal = TemporalConfig(
            enabled=True,
            integration_mode="citation_only",
            rerank_top_k=3,
            use_citation_features=True,
            citation_network_path="missing-citation-network.csv",
        )

        reranked = temporal_rerank_results(results=results, bundle=bundle, config=config)

        self.assertEqual([result.doc_id for result in reranked], [result.doc_id for result in results])
        self.assertEqual({result.rank for result in reranked}, {1, 2, 3})

    def test_router_modes_with_missing_citation_data(self) -> None:
        query_texts = [
            "latest neural retrieval updates in 2026",
            "seminal influential retrieval papers",
            "recent survey comparing retrieval benchmarks",
        ]
        for query_text in query_texts:
            config, bundle, results = _fixture_inputs(query_text)
            config.temporal = TemporalConfig(
                enabled=True,
                integration_mode="router",
                rerank_top_k=3,
                use_citation_features=True,
                citation_network_path="missing-citation-network.csv",
            )

            reranked = temporal_rerank_results(results=results, bundle=bundle, config=config)

            self.assertEqual(len(reranked), 3)
            self.assertEqual({result.rank for result in reranked}, {1, 2, 3})

    def test_additive_mode_with_missing_citation_data(self) -> None:
        config, bundle, results = _fixture_inputs("recent scientific retrieval updates")
        config.temporal = TemporalConfig(
            enabled=True,
            integration_mode="additive",
            rerank_top_k=3,
            use_citation_features=True,
            citation_network_path="missing-citation-network.csv",
            recency_weight=0.06,
            update_weight=0.04,
            foundation_weight=0.04,
            novelty_weight=0.03,
            citation_total_weight=0.04,
            citation_recent_weight=0.05,
            citation_foundation_weight=0.04,
            citation_emerging_weight=0.05,
            citation_outbound_weight=0.01,
        )

        reranked = temporal_rerank_results(results=results, bundle=bundle, config=config)

        self.assertEqual(len(reranked), 3)
        self.assertEqual({result.rank for result in reranked}, {1, 2, 3})
        self.assertFalse(any(result.score != result.score for result in reranked))


if __name__ == "__main__":
    unittest.main()
