"""Vector index helpers with FAISS and NumPy backends."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class NumpyVectorIndex:
    """A simple similarity index used when FAISS is unavailable."""

    def __init__(self, embeddings: np.ndarray) -> None:
        self.embeddings = embeddings.astype(np.float32)

    def search(self, queries: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        if queries.ndim == 1:
            queries = queries[np.newaxis, :]
        scores = queries @ self.embeddings.T
        indices = np.argsort(-scores, axis=1)[:, :top_k]
        sorted_scores = np.take_along_axis(scores, indices, axis=1)
        return sorted_scores, indices


def build_vector_index(embeddings: np.ndarray, normalize: bool = True):
    """Build a FAISS index when available, otherwise fall back to NumPy."""
    vectors = embeddings.astype(np.float32)
    if normalize:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.clip(norms, 1e-12, None)
    try:
        import faiss

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        return index, vectors
    except ImportError:
        return NumpyVectorIndex(vectors), vectors


def search_vector_index(index, queries: np.ndarray, top_k: int, normalize: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Search either a FAISS or NumPy index."""
    query_vectors = queries.astype(np.float32)
    if normalize:
        norms = np.linalg.norm(query_vectors, axis=1, keepdims=True)
        query_vectors = query_vectors / np.clip(norms, 1e-12, None)
    return index.search(query_vectors, top_k)


def save_vector_index(path: str | Path, index, embeddings: np.ndarray, doc_ids: list[str]) -> None:
    """Persist a vector index and its metadata."""
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump({"doc_ids": doc_ids}, handle)
    try:
        import faiss

        faiss.write_index(index, str(output_dir / "index.faiss"))
    except ImportError:
        np.save(output_dir / "index.npy", embeddings)


def load_vector_index(path: str | Path):
    """Load a vector index and its associated document ids."""
    input_dir = Path(path)
    with (input_dir / "metadata.json").open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    faiss_path = input_dir / "index.faiss"
    if faiss_path.exists():
        import faiss

        return faiss.read_index(str(faiss_path)), metadata["doc_ids"]
    numpy_path = input_dir / "index.npy"
    if numpy_path.exists():
        embeddings = np.load(numpy_path)
        return NumpyVectorIndex(embeddings), metadata["doc_ids"]
    raise FileNotFoundError(f"No saved vector index found under {input_dir}")
