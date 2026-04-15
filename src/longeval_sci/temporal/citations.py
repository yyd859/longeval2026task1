"""Citation-based temporal feature utilities.

This module is intentionally lightweight in the first pass:

- stream the OpenCitations CSV once for a chosen cutoff time
- aggregate per-document citation statistics as of that cutoff
- expose raw and gently-normalized signals that later rerankers can use

The key design rule is that citation features must be *as-of* the evaluation
time, so we filter citation edges by their `creation` date and never use edges
from the future relative to the snapshot or monthly split being evaluated.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from math import log1p
from pathlib import Path
from typing import Iterable
import csv
import re


@dataclass(slots=True)
class CitationTemporalFeatures:
    total_inbound_citations: int = 0
    recent_inbound_citations: int = 0
    nonself_inbound_citations: int = 0
    nonself_recent_inbound_citations: int = 0
    total_outbound_citations: int = 0
    recent_outbound_citations: int = 0
    mean_inbound_citation_lag_days: float | None = None
    recent_inbound_ratio: float = 0.0
    citation_velocity: float = 0.0
    foundational_signal: float = 0.0
    emerging_signal: float = 0.0


@dataclass(slots=True)
class _MutableCitationStats:
    total_inbound: int = 0
    recent_inbound: int = 0
    nonself_inbound: int = 0
    nonself_recent_inbound: int = 0
    total_outbound: int = 0
    recent_outbound: int = 0
    lag_days_sum: float = 0.0
    lag_days_count: int = 0


_DURATION_PATTERN = re.compile(
    r"^P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<days>\d+)D)?$"
)


def _parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_iso_duration_days(value: str | None) -> float | None:
    if not value:
        return None
    match = _DURATION_PATTERN.match(value.strip())
    if not match:
        return None
    years = int(match.group("years") or 0)
    months = int(match.group("months") or 0)
    days = int(match.group("days") or 0)
    # Approximation is sufficient for aggregate temporal signals.
    return float(years * 365 + months * 30 + days)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def iter_citation_rows(path: str | Path) -> Iterable[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield {key: (value or "").strip() for key, value in row.items()}


def aggregate_citation_features(
    path: str | Path,
    *,
    cutoff: datetime,
    allowed_doc_ids: set[str] | None = None,
    recent_window_days: int = 180,
    exclude_self_citations: bool = True,
) -> dict[str, CitationTemporalFeatures]:
    """Aggregate citation features as of a cutoff time.

    Parameters
    ----------
    path:
        OpenCitations CSV path.
    cutoff:
        Evaluation-time cutoff. Citation edges created after this time are
        ignored to avoid future leakage.
    allowed_doc_ids:
        Optional set of corpus doc ids. When provided, only docs in this set
        get aggregated statistics.
    recent_window_days:
        Window used for "recent" citation activity.
    exclude_self_citations:
        When true, `journal_sc` and `author_sc` edges do not contribute to the
        non-self citation counters.
    """

    cutoff_utc = cutoff if cutoff.tzinfo is not None else cutoff.replace(tzinfo=UTC)
    recent_cutoff = cutoff_utc - timedelta(days=max(recent_window_days, 1))
    stats: dict[str, _MutableCitationStats] = defaultdict(_MutableCitationStats)

    for row in iter_citation_rows(path):
        creation_dt = _parse_iso_date(row.get("creation"))
        if creation_dt is None or creation_dt > cutoff_utc:
            continue

        is_recent = creation_dt >= recent_cutoff
        is_self_citation = _truthy(row.get("journal_sc")) or _truthy(row.get("author_sc"))
        count_for_nonself = not (exclude_self_citations and is_self_citation)

        cited_doc_id = row.get("cited_doc_id", "")
        if cited_doc_id and (allowed_doc_ids is None or cited_doc_id in allowed_doc_ids):
            cited_stats = stats[cited_doc_id]
            cited_stats.total_inbound += 1
            if is_recent:
                cited_stats.recent_inbound += 1
            if count_for_nonself:
                cited_stats.nonself_inbound += 1
                if is_recent:
                    cited_stats.nonself_recent_inbound += 1
            lag_days = _parse_iso_duration_days(row.get("timespan"))
            if lag_days is not None:
                cited_stats.lag_days_sum += lag_days
                cited_stats.lag_days_count += 1

        citing_doc_id = row.get("citing_doc_id", "")
        if citing_doc_id and (allowed_doc_ids is None or citing_doc_id in allowed_doc_ids):
            citing_stats = stats[citing_doc_id]
            citing_stats.total_outbound += 1
            if is_recent:
                citing_stats.recent_outbound += 1

    features: dict[str, CitationTemporalFeatures] = {}
    recent_denominator = float(max(recent_window_days, 1))
    for doc_id, doc_stats in stats.items():
        total_for_ratio = max(doc_stats.total_inbound, 1)
        recent_ratio = doc_stats.recent_inbound / total_for_ratio
        mean_lag = None
        if doc_stats.lag_days_count:
            mean_lag = doc_stats.lag_days_sum / doc_stats.lag_days_count

        # Simple, explainable derived signals for later reranking.
        velocity = doc_stats.recent_inbound / recent_denominator
        foundational_signal = log1p(max(doc_stats.nonself_inbound, doc_stats.total_inbound, 0)) * (1.0 - recent_ratio)
        emerging_signal = log1p(doc_stats.recent_inbound) * recent_ratio

        features[doc_id] = CitationTemporalFeatures(
            total_inbound_citations=doc_stats.total_inbound,
            recent_inbound_citations=doc_stats.recent_inbound,
            nonself_inbound_citations=doc_stats.nonself_inbound,
            nonself_recent_inbound_citations=doc_stats.nonself_recent_inbound,
            total_outbound_citations=doc_stats.total_outbound,
            recent_outbound_citations=doc_stats.recent_outbound,
            mean_inbound_citation_lag_days=mean_lag,
            recent_inbound_ratio=recent_ratio,
            citation_velocity=velocity,
            foundational_signal=foundational_signal,
            emerging_signal=emerging_signal,
        )
    return features


def _cache_key(
    *,
    cutoff: datetime,
    allowed_doc_ids: set[str] | None,
    recent_window_days: int,
    exclude_self_citations: bool,
) -> str:
    digest = hashlib.sha1()
    digest.update(cutoff.astimezone(UTC).isoformat().encode("utf-8"))
    digest.update(f"|{recent_window_days}|{int(exclude_self_citations)}|".encode("utf-8"))
    if allowed_doc_ids is None:
        digest.update(b"all_docs")
    else:
        for doc_id in sorted(allowed_doc_ids):
            digest.update(doc_id.encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()[:16]


def load_or_build_citation_feature_cache(
    path: str | Path,
    *,
    cutoff: datetime,
    allowed_doc_ids: set[str] | None = None,
    recent_window_days: int = 180,
    exclude_self_citations: bool = True,
    cache_root: str | Path | None = None,
) -> dict[str, CitationTemporalFeatures]:
    if cache_root is None:
        return aggregate_citation_features(
            path,
            cutoff=cutoff,
            allowed_doc_ids=allowed_doc_ids,
            recent_window_days=recent_window_days,
            exclude_self_citations=exclude_self_citations,
        )

    cache_dir = Path(cache_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"citation_features_{_cache_key(cutoff=cutoff, allowed_doc_ids=allowed_doc_ids, recent_window_days=recent_window_days, exclude_self_citations=exclude_self_citations)}.json"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return {
            doc_id: CitationTemporalFeatures(**values)
            for doc_id, values in payload.items()
        }

    features = aggregate_citation_features(
        path,
        cutoff=cutoff,
        allowed_doc_ids=allowed_doc_ids,
        recent_window_days=recent_window_days,
        exclude_self_citations=exclude_self_citations,
    )
    serializable = {
        doc_id: {
            "total_inbound_citations": feature.total_inbound_citations,
            "recent_inbound_citations": feature.recent_inbound_citations,
            "nonself_inbound_citations": feature.nonself_inbound_citations,
            "nonself_recent_inbound_citations": feature.nonself_recent_inbound_citations,
            "total_outbound_citations": feature.total_outbound_citations,
            "recent_outbound_citations": feature.recent_outbound_citations,
            "mean_inbound_citation_lag_days": feature.mean_inbound_citation_lag_days,
            "recent_inbound_ratio": feature.recent_inbound_ratio,
            "citation_velocity": feature.citation_velocity,
            "foundational_signal": feature.foundational_signal,
            "emerging_signal": feature.emerging_signal,
        }
        for doc_id, feature in features.items()
    }
    cache_path.write_text(json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8")
    return features
