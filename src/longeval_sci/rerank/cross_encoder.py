"""Cross-encoder style reranking with optional model-backed scoring."""

from __future__ import annotations

from collections import Counter

from longeval_sci.io.dataset import Document
from longeval_sci.preprocess.fields import build_document_text


class LexicalPairScorer:
    """Fallback pair scorer used when cross-encoder dependencies are unavailable."""

    def predict(self, pairs: list[tuple[str, str]], **_: object) -> list[float]:
        scores: list[float] = []
        for query, document in pairs:
            query_terms = Counter(query.lower().split())
            document_terms = Counter(document.lower().split())
            overlap = sum(min(query_terms[token], document_terms[token]) for token in query_terms)
            scores.append(float(overlap))
        return scores


class CrossEncoderReranker:
    """Rerank candidate documents with a cross-encoder or a lexical fallback."""

    def __init__(self, model_name: str, text_mode: str = "title_abstract", device: str = "cpu", batch_size: int = 32) -> None:
        self.model_name = model_name
        self.text_mode = text_mode
        self.device = device
        self.batch_size = batch_size
        self._model = self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import CrossEncoder

            return CrossEncoder(self.model_name, device=self.device)
        except Exception:
            return LexicalPairScorer()

    def rerank(
        self,
        query: str,
        candidates: list[Document],
        top_k: int | None = None,
    ) -> list[tuple[str, float]]:
        """Rerank a candidate set and return doc ids with scores."""
        pairs = [(query, build_document_text(document, self.text_mode)) for document in candidates]
        scores = self._model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda item: float(item[1]), reverse=True)
        outputs = [(document.doc_id, float(score)) for document, score in ranked]
        if top_k is not None:
            return outputs[:top_k]
        return outputs
