"""Simple BM25 retriever suitable for baseline experimentation."""

from __future__ import annotations

import math
import pickle
import re
from pathlib import Path

from longeval_sci.io.dataset import Document
from longeval_sci.preprocess.fields import build_document_text


TOKEN_PATTERN = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    """Tokenize text for lexical retrieval."""
    return TOKEN_PATTERN.findall(text.lower())


class BM25Retriever:
    """A lightweight BM25 retriever with save/load support."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.text_mode = "title_abstract"
        self.doc_ids: list[str] = []
        self.documents: dict[str, Document] = {}
        self.term_frequencies: list[dict[str, int]] = []
        self.document_lengths: list[int] = []
        self.document_frequency: dict[str, int] = {}
        self.average_document_length = 0.0

    def build_index(self, documents: list[Document], text_mode: str) -> None:
        """Build the in-memory BM25 index."""
        self.text_mode = text_mode
        self.doc_ids = []
        self.documents = {document.doc_id: document for document in documents}
        self.term_frequencies = []
        self.document_lengths = []
        self.document_frequency = {}

        for document in documents:
            tokens = tokenize(build_document_text(document, text_mode))
            freqs: dict[str, int] = {}
            for token in tokens:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_ids.append(document.doc_id)
            self.term_frequencies.append(freqs)
            self.document_lengths.append(len(tokens))
            for token in freqs:
                self.document_frequency[token] = self.document_frequency.get(token, 0) + 1

        if not self.document_lengths:
            raise ValueError("Cannot build a BM25 index with no documents")
        self.average_document_length = sum(self.document_lengths) / len(self.document_lengths)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Search the BM25 index and return scored doc ids."""
        query_terms = tokenize(query)
        num_docs = len(self.doc_ids)
        scores: list[tuple[str, float]] = []

        for doc_index, doc_id in enumerate(self.doc_ids):
            score = 0.0
            freqs = self.term_frequencies[doc_index]
            doc_length = self.document_lengths[doc_index]
            for term in query_terms:
                if term not in freqs:
                    continue
                df = self.document_frequency.get(term, 0)
                idf = math.log(1 + ((num_docs - df + 0.5) / (df + 0.5)))
                tf = freqs[term]
                denom = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.average_document_length))
                score += idf * ((tf * (self.k1 + 1)) / denom)
            if score > 0.0:
                scores.append((doc_id, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]

    def save(self, path: str) -> None:
        """Persist the BM25 index to disk."""
        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "k1": self.k1,
            "b": self.b,
            "text_mode": self.text_mode,
            "doc_ids": self.doc_ids,
            "documents": self.documents,
            "term_frequencies": self.term_frequencies,
            "document_lengths": self.document_lengths,
            "document_frequency": self.document_frequency,
            "average_document_length": self.average_document_length,
        }
        with (output_dir / "bm25.pkl").open("wb") as handle:
            pickle.dump(payload, handle)

    def load(self, path: str) -> None:
        """Load a previously saved BM25 index."""
        with (Path(path) / "bm25.pkl").open("rb") as handle:
            payload = pickle.load(handle)
        self.k1 = payload["k1"]
        self.b = payload["b"]
        self.text_mode = payload["text_mode"]
        self.doc_ids = payload["doc_ids"]
        self.documents = payload["documents"]
        self.term_frequencies = payload["term_frequencies"]
        self.document_lengths = payload["document_lengths"]
        self.document_frequency = payload["document_frequency"]
        self.average_document_length = payload["average_document_length"]
