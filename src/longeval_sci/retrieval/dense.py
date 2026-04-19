"""Dense retrieval with chunked indexing for large LongEval snapshots."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np

from longeval_sci.io.dataset import Document
from longeval_sci.preprocess.fields import build_document_text


LOGGER = logging.getLogger(__name__)


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


class DiskBackedVectorIndex:
    """Exact inner-product search over a disk-backed NumPy array."""

    def __init__(self, embeddings_path: str | Path, search_chunk_size: int = 50_000) -> None:
        self.embeddings_path = Path(embeddings_path)
        self.search_chunk_size = search_chunk_size

    def search(self, queries: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        embeddings = np.load(self.embeddings_path, mmap_mode="r")
        if queries.ndim == 1:
            queries = queries[np.newaxis, :]

        all_scores: list[np.ndarray] = []
        all_indices: list[np.ndarray] = []
        for query in queries:
            best_scores = np.full(top_k, -np.inf, dtype=np.float32)
            best_indices = np.full(top_k, -1, dtype=np.int64)
            for start in range(0, embeddings.shape[0], self.search_chunk_size):
                end = min(start + self.search_chunk_size, embeddings.shape[0])
                chunk = embeddings[start:end]
                chunk_scores = chunk @ query
                local_top_k = min(top_k, chunk_scores.shape[0])
                local_indices = np.argpartition(-chunk_scores, local_top_k - 1)[:local_top_k]
                candidate_scores = chunk_scores[local_indices]
                candidate_indices = local_indices.astype(np.int64) + start

                merged_scores = np.concatenate([best_scores, candidate_scores.astype(np.float32, copy=False)])
                merged_indices = np.concatenate([best_indices, candidate_indices])
                keep = np.argsort(-merged_scores)[:top_k]
                best_scores = merged_scores[keep]
                best_indices = merged_indices[keep]

            all_scores.append(best_scores)
            all_indices.append(best_indices)

        return np.vstack(all_scores), np.vstack(all_indices)


class DenseRetriever:
    """Dense retriever with optional sentence-transformers and chunked indexing."""

    def __init__(
        self,
        model_name: str | None = None,
        text_mode: str = "title_abstract",
        normalize_embeddings: bool = True,
        query_prefix: str = "",
        document_prefix: str = "",
        batch_size: int = 32,
        device: str = "cpu",
        encode_chunk_size: int = 2048,
        search_chunk_size: int = 50_000,
    ) -> None:
        self.model_name = model_name or "hashing"
        self.text_mode = text_mode
        self.normalize_embeddings = normalize_embeddings
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self.batch_size = batch_size
        self.device = device
        self.encode_chunk_size = encode_chunk_size
        self.search_chunk_size = search_chunk_size
        self.index = None
        self.doc_ids: list[str] = []
        self.documents: dict[str, Document] = {}
        self.embeddings_path: Path | None = None
        self.model_version: str | None = None
        self._encoder = self._load_encoder()
        self.embedding_dimension: int | None = None

    def _load_encoder(self):
        try:
            from sentence_transformers import SentenceTransformer
            import sentence_transformers as _st

            self.model_version = _st.__version__
            return SentenceTransformer(self.model_name, device=self.device)
        except Exception:
            self.model_version = None
            return HashingEmbedder()

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._encoder.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if self.embedding_dimension is None:
            self.embedding_dimension = int(vectors.shape[1])
        return vectors

    def get_embedding_dimension(self) -> int:
        if self.embedding_dimension is None:
            self._encode(["dimension probe"])
        assert self.embedding_dimension is not None
        return self.embedding_dimension

    def _document_texts(self, documents: list[Document], start: int, end: int) -> list[str]:
        return [self.document_prefix + build_document_text(document, self.text_mode) for document in documents[start:end]]

    def encode_documents(self, documents: list[Document]) -> np.ndarray:
        """Encode documents into dense vectors in-memory."""
        self.documents = {document.doc_id: document for document in documents}
        texts = [self.document_prefix + build_document_text(document, self.text_mode) for document in documents]
        return self._encode(texts)

    def build_index(self, embeddings: np.ndarray, doc_ids: list[str]) -> None:
        """Build an in-memory vector index for small collections."""
        vectors = embeddings.astype(np.float32)
        if self.normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / np.clip(norms, 1e-12, None)

        try:
            import faiss

            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(vectors)
            self.index = index
        except ImportError:
            self.index = DiskBackedVectorIndex(self._write_numpy_index(vectors, Path.cwd() / ".dense_tmp.npy"), self.search_chunk_size)
        self.doc_ids = doc_ids

    def _write_numpy_index(self, vectors: np.ndarray, path: Path) -> Path:
        np.save(path, vectors.astype(np.float32))
        self.embeddings_path = path
        return path

    def build_index_from_documents(self, documents: list[Document], output_dir: str | Path) -> None:
        """Encode and index a large collection incrementally."""
        if not documents:
            raise ValueError("Cannot build dense index with no documents")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self.documents = {document.doc_id: document for document in documents}
        self.doc_ids = [document.doc_id for document in documents]

        total = len(documents)
        LOGGER.info(
            "Building dense index for %s documents with chunk size %s",
            total,
            self.encode_chunk_size,
        )

        try:
            import faiss

            first_end = min(self.encode_chunk_size, total)
            first_batch = self._encode(self._document_texts(documents, 0, first_end)).astype(np.float32)
            index = faiss.IndexFlatIP(first_batch.shape[1])
            index.add(first_batch)

            for start in range(first_end, total, self.encode_chunk_size):
                end = min(start + self.encode_chunk_size, total)
                batch = self._encode(self._document_texts(documents, start, end)).astype(np.float32)
                index.add(batch)
                LOGGER.info("Encoded dense chunk %s-%s / %s", start, end, total)

            self.index = index
        except ImportError:
            first_end = min(self.encode_chunk_size, total)
            first_batch = self._encode(self._document_texts(documents, 0, first_end)).astype(np.float32)
            dimension = first_batch.shape[1]
            embeddings_path = output_path / "index.npy"
            matrix = np.lib.format.open_memmap(
                embeddings_path,
                mode="w+",
                dtype=np.float32,
                shape=(total, dimension),
            )
            matrix[0:first_end] = first_batch
            del first_batch

            for start in range(first_end, total, self.encode_chunk_size):
                end = min(start + self.encode_chunk_size, total)
                matrix[start:end] = self._encode(self._document_texts(documents, start, end)).astype(np.float32)
                LOGGER.info("Encoded dense chunk %s-%s / %s", start, end, total)

            del matrix
            self.embeddings_path = embeddings_path
            self.index = DiskBackedVectorIndex(embeddings_path, self.search_chunk_size)

        self.save(output_path)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Search the vector index for the given query."""
        if self.index is None:
            raise ValueError("Dense index has not been built or loaded")
        query_embedding = self._encode([self.query_prefix + query]).astype(np.float32)
        scores, indices = self.index.search(query_embedding, top_k)
        pairs: list[tuple[str, float]] = []
        for score, index in zip(scores[0], indices[0], strict=True):
            if int(index) < 0:
                continue
            pairs.append((self.doc_ids[int(index)], float(score)))
        return pairs

    def save(self, path: str | Path) -> None:
        """Persist the dense index."""
        if self.index is None:
            raise ValueError("Dense index has not been built")

        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "doc_ids": self.doc_ids,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "text_mode": self.text_mode,
            "normalize_embeddings": self.normalize_embeddings,
            "query_prefix": self.query_prefix,
            "document_prefix": self.document_prefix,
            "search_chunk_size": self.search_chunk_size,
            "embedding_dimension": self.embedding_dimension,
        }
        with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle)

        try:
            import faiss

            if hasattr(self.index, "search") and not isinstance(self.index, DiskBackedVectorIndex):
                faiss.write_index(self.index, str(output_dir / "index.faiss"))
                return
        except ImportError:
            pass

        if self.embeddings_path is None:
            raise ValueError("Disk-backed dense index is missing the embeddings path")
        if self.embeddings_path.resolve() != (output_dir / "index.npy").resolve():
            np.save(output_dir / "index.npy", np.load(self.embeddings_path, mmap_mode="r"))

    def load(self, path: str | Path) -> None:
        """Load a previously saved dense index."""
        input_dir = Path(path)
        with (input_dir / "metadata.json").open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.doc_ids = metadata["doc_ids"]
        self.model_name = metadata.get("model_name", self.model_name)
        self.model_version = metadata.get("model_version", self.model_version)
        self.text_mode = metadata.get("text_mode", self.text_mode)
        self.normalize_embeddings = metadata.get("normalize_embeddings", self.normalize_embeddings)
        self.query_prefix = metadata.get("query_prefix", self.query_prefix)
        self.document_prefix = metadata.get("document_prefix", self.document_prefix)
        self.search_chunk_size = metadata.get("search_chunk_size", self.search_chunk_size)
        self.embedding_dimension = metadata.get("embedding_dimension", self.embedding_dimension)

        faiss_path = input_dir / "index.faiss"
        if faiss_path.exists():
            import faiss

            self.index = faiss.read_index(str(faiss_path))
            if self.embedding_dimension is None and hasattr(self.index, "d"):
                self.embedding_dimension = int(self.index.d)
            return

        numpy_path = input_dir / "index.npy"
        if not numpy_path.exists():
            raise FileNotFoundError(f"No dense index found under {input_dir}")
        self.embeddings_path = numpy_path
        if self.embedding_dimension is None:
            self.embedding_dimension = int(np.load(numpy_path, mmap_mode="r").shape[1])
        self.index = DiskBackedVectorIndex(numpy_path, self.search_chunk_size)
