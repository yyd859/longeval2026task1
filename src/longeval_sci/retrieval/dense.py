"""Dense retrieval with pluggable embedding backends."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from longeval_sci.io.dataset import Document
from longeval_sci.preprocess.fields import build_document_text
from longeval_sci.retrieval.faiss_utils import build_vector_index, load_vector_index, save_vector_index, search_vector_index


class HashingEmbedder:
    """Deterministic fallback embedder for smoke tests and environments without model deps."""

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def encode(self, texts: list[str], normalize_embeddings: bool = True, **_: object) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in text.lower().split():
                digest = hashlib.md5(token.encode("utf-8")).hexdigest()
                index = int(digest[:8], 16) % self.dimension
                sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
                vectors[row, index] += sign
        if normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.clip(norms, 1e-12, None)
        return vectors


class DenseRetriever:
    """Dense retriever with optional sentence-transformers + FAISS support."""

    def __init__(
        self,
        model_name: str | None = None,
        text_mode: str = "title_abstract",
        normalize_embeddings: bool = True,
        query_prefix: str = "",
        document_prefix: str = "",
        batch_size: int = 32,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name or "hashing"
        self.text_mode = text_mode
        self.normalize_embeddings = normalize_embeddings
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self.batch_size = batch_size
        self.device = device
        self.index = None
        self.doc_ids: list[str] = []
        self.documents: dict[str, Document] = {}
        self.embeddings: np.ndarray | None = None
        self._encoder = self._load_encoder()

    def _load_encoder(self):
        try:
            from sentence_transformers import SentenceTransformer

            return SentenceTransformer(self.model_name, device=self.device)
        except Exception:
            return HashingEmbedder()

    def _encode(self, texts: list[str]) -> np.ndarray:
        return self._encoder.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def encode_documents(self, documents: list[Document]) -> np.ndarray:
        """Encode documents into dense vectors."""
        self.documents = {document.doc_id: document for document in documents}
        texts = [self.document_prefix + build_document_text(document, self.text_mode) for document in documents]
        return self._encode(texts)

    def build_index(self, embeddings: np.ndarray, doc_ids: list[str]) -> None:
        """Build the vector index."""
        self.index, self.embeddings = build_vector_index(embeddings, normalize=self.normalize_embeddings)
        self.doc_ids = doc_ids

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Search the vector index for the given query."""
        if self.index is None:
            raise ValueError("Dense index has not been built or loaded")
        query_embedding = self._encode([self.query_prefix + query])
        scores, indices = search_vector_index(self.index, query_embedding, top_k=top_k, normalize=self.normalize_embeddings)
        pairs: list[tuple[str, float]] = []
        for score, index in zip(scores[0], indices[0], strict=True):
            pairs.append((self.doc_ids[int(index)], float(score)))
        return pairs

    def save(self, path: str) -> None:
        """Persist the dense index."""
        if self.index is None or self.embeddings is None:
            raise ValueError("Dense index has not been built")
        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)
        save_vector_index(output_dir, self.index, self.embeddings, self.doc_ids)
        metadata = {
            "model_name": self.model_name,
            "text_mode": self.text_mode,
            "normalize_embeddings": self.normalize_embeddings,
            "query_prefix": self.query_prefix,
            "document_prefix": self.document_prefix,
        }
        with (output_dir / "dense_config.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle)

    def load(self, path: str) -> None:
        """Load a previously saved dense index."""
        self.index, self.doc_ids = load_vector_index(path)
        config_path = Path(path) / "dense_config.json"
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            self.model_name = metadata.get("model_name", self.model_name)
            self.text_mode = metadata.get("text_mode", self.text_mode)
            self.normalize_embeddings = metadata.get("normalize_embeddings", self.normalize_embeddings)
            self.query_prefix = metadata.get("query_prefix", self.query_prefix)
            self.document_prefix = metadata.get("document_prefix", self.document_prefix)
