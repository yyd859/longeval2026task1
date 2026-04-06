"""Document field construction helpers."""

from __future__ import annotations

from longeval_sci.io.dataset import Document
from longeval_sci.preprocess.text import normalize_whitespace


def _join_non_empty(parts: list[str]) -> str:
    return normalize_whitespace("\n".join(part.strip() for part in parts if part and part.strip()))


def build_title_abstract_text(document: Document) -> str:
    """Build title + abstract text for a document."""
    return _join_non_empty([document.title, document.abstract])


def build_fulltext_text(document: Document) -> str:
    """Build full-text text for a document."""
    return _join_non_empty([document.full_text or build_title_abstract_text(document)])


def build_all_text(document: Document) -> str:
    """Build title + abstract + full text for a document."""
    return _join_non_empty([document.title, document.abstract, document.full_text])


def build_document_text(document: Document, text_mode: str) -> str:
    """Build the document text for a configured mode."""
    if text_mode == "title_abstract":
        return build_title_abstract_text(document)
    if text_mode == "full_text":
        return build_fulltext_text(document)
    if text_mode == "all_text":
        return build_all_text(document)
    raise ValueError(f"Unsupported text mode: {text_mode}")
