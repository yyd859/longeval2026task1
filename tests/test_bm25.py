from longeval_sci.config import load_config
from longeval_sci.io.dataset import load_documents
from longeval_sci.retrieval.bm25 import BM25Retriever


def test_bm25_retrieval_on_local_fixture():
    config = load_config("configs/local_fixture_dense_rerank.yaml")
    documents = load_documents(config.dataset)
    retriever = BM25Retriever()
    retriever.build_index(documents, text_mode="title_abstract")

    results = retriever.search("dense retrieval scientific", top_k=3)

    assert results
    assert results[0][0] == "D1"
