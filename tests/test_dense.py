from longeval_sci.config import load_config
from longeval_sci.io.dataset import load_documents
from longeval_sci.retrieval.dense import DenseRetriever


def test_dense_retrieval_on_local_fixture():
    config = load_config("configs/local_fixture_dense_rerank.yaml")
    documents = load_documents(config.dataset)
    retriever = DenseRetriever(
        model_name=config.retrieval.model_name,
        text_mode=config.retrieval.text_mode,
        normalize_embeddings=config.retrieval.normalize_embeddings,
        query_prefix=config.retrieval.query_prefix,
        document_prefix=config.retrieval.document_prefix,
    )
    embeddings = retriever.encode_documents(documents)
    retriever.build_index(embeddings, [document.doc_id for document in documents])

    results = retriever.search("scientific retrieval dense models", top_k=3)

    assert results
    assert len(results) <= 3
