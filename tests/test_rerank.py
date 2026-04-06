from longeval_sci.config import load_config
from longeval_sci.io.dataset import load_documents
from longeval_sci.rerank.cross_encoder import CrossEncoderReranker


def test_reranker_on_local_fixture():
    config = load_config("configs/local_fixture_dense_rerank.yaml")
    documents = load_documents(config.dataset)
    reranker = CrossEncoderReranker(
        model_name=config.rerank.model_name,
        text_mode=config.retrieval.text_mode,
        device=config.runtime.device,
        batch_size=config.runtime.batch_size,
    )

    ranked = reranker.rerank("cross encoder reranking precision", documents, top_k=3)

    assert ranked
    assert ranked[0][1] >= ranked[-1][1]
