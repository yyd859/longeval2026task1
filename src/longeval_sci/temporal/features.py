"""Temporal metadata and lightweight content feature extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import exp
from typing import Iterable
import re

from longeval_sci.config import TemporalConfig
from longeval_sci.io.dataset import DatasetBundle, Document
from longeval_sci.preprocess.fields import build_document_text

_SNAPSHOT_CUTOFFS = {
    "snapshot-1": datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC),
    "snapshot-2": datetime(2025, 8, 31, 23, 59, 59, tzinfo=UTC),
    "snapshot-3": datetime(2025, 11, 30, 23, 59, 59, tzinfo=UTC),
}


@dataclass(slots=True)
class TemporalDocumentFeatures:
    age_days: float | None
    update_age_days: float | None
    recency_score: float
    update_score: float
    foundation_score: float
    novelty_score: float
    publication_datetime: datetime | None
    update_datetime: datetime | None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    formats = (
        None,
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    )
    for fmt in formats:
        try:
            if fmt is None:
                parsed = datetime.fromisoformat(normalized)
            else:
                parsed = datetime.strptime(normalized, fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            continue
    return None


def _document_datetime_candidates(document: Document, config: TemporalConfig) -> tuple[datetime | None, datetime | None]:
    created = _parse_datetime(document.metadata.get("createdDate"))
    published = _parse_datetime(document.metadata.get("publishedDate"))
    updated = _parse_datetime(document.metadata.get("updatedDate"))
    publication_dt = (created or published) if config.use_creation_date else (published or created)
    update_dt = updated or publication_dt
    if not config.use_update_date:
        update_dt = publication_dt
    return publication_dt, update_dt


def resolve_evaluation_time(bundle: DatasetBundle, config: TemporalConfig) -> datetime:
    if config.evaluation_time_field == "snapshot" and bundle.metadata.timestamp:
        parsed = _parse_datetime(bundle.metadata.timestamp)
        if parsed is not None:
            return parsed
    if config.evaluation_time_field == "snapshot":
        snapshot_cutoff = _SNAPSHOT_CUTOFFS.get(bundle.metadata.snapshot_id)
        if snapshot_cutoff is not None:
            return snapshot_cutoff

    candidates: list[datetime] = []
    for document in bundle.documents:
        publication_dt, update_dt = _document_datetime_candidates(document, config)
        if publication_dt is not None:
            candidates.append(publication_dt)
        if update_dt is not None:
            candidates.append(update_dt)
    if candidates:
        return max(candidates)
    return datetime.now(tz=UTC)


def _safe_days(delta_seconds: float) -> float:
    return max(delta_seconds / 86400.0, 0.0)


def _exp_decay(days: float | None, half_life_days: float) -> float:
    if days is None:
        return 0.0
    half_life = max(half_life_days, 1.0)
    return exp(-days / half_life)


def _foundation_curve(days: float | None, half_life_days: float) -> float:
    if days is None:
        return 0.0
    half_life = max(half_life_days, 1.0)
    return 1.0 - exp(-days / half_life)


_NOVELTY_TERMS = {"recent", "latest", "emerging", "novel", "state-of-the-art", "update", "updated", "current"}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text.lower()))


def _lexical_novelty(query_text: str, document: Document, text_mode: str) -> float:
    query_terms = _tokenize(query_text)
    document_terms = _tokenize(build_document_text(document, text_mode))
    if not document_terms:
        return 0.0
    novelty_terms = len((_NOVELTY_TERMS & document_terms) - query_terms)
    unseen_terms = len(document_terms - query_terms)
    return min(1.0, (novelty_terms * 0.2) + (unseen_terms / max(len(document_terms), 1)) * 0.1)


def compute_temporal_features(
    document: Document,
    *,
    query_text: str,
    evaluation_time: datetime,
    config: TemporalConfig,
    text_mode: str,
) -> TemporalDocumentFeatures:
    publication_dt, update_dt = _document_datetime_candidates(document, config)

    age_days = None
    if publication_dt is not None and config.use_age:
        age_days = _safe_days((evaluation_time - publication_dt).total_seconds())
    update_age_days = None
    if update_dt is not None and config.use_update_date:
        update_age_days = _safe_days((evaluation_time - update_dt).total_seconds())

    recency_score = _exp_decay(age_days, config.freshness_half_life_days) if config.use_recency_decay else 0.0
    update_score = _exp_decay(update_age_days, config.freshness_half_life_days) if config.use_update_date else 0.0
    foundation_score = _foundation_curve(age_days, config.age_half_life_days) if config.use_age else 0.0
    novelty_score = _lexical_novelty(query_text, document, text_mode) if config.use_lexical_novelty else 0.0

    return TemporalDocumentFeatures(
        age_days=age_days,
        update_age_days=update_age_days,
        recency_score=recency_score,
        update_score=update_score,
        foundation_score=foundation_score,
        novelty_score=novelty_score,
        publication_datetime=publication_dt,
        update_datetime=update_dt,
    )


def collect_candidate_datetimes(
    documents: Iterable[Document],
    config: TemporalConfig,
) -> list[datetime]:
    values: list[datetime] = []
    for document in documents:
        publication_dt, update_dt = _document_datetime_candidates(document, config)
        if publication_dt is not None:
            values.append(publication_dt)
        if update_dt is not None:
            values.append(update_dt)
    return values
