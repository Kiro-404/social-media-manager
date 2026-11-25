"""
Combines every configured TrendSource into one ranked list, and persists the
results as TrendSignal rows so the ideation stage can pick from history too
(not just the latest live pull).
"""
from __future__ import annotations

import json

from loguru import logger
from sqlalchemy.orm import Session

from app.models import TrendSignal
from app.trends.base import TrendObservation, TrendSource
from app.trends.google_trends import GoogleTrendsSource
from app.trends.youtube_trends import YouTubeTrendsSource


def default_sources() -> list[TrendSource]:
    return [GoogleTrendsSource(), YouTubeTrendsSource()]


def collect_trends(
    db: Session,
    seed_keywords: list[str] | None = None,
    limit_per_source: int = 10,
    sources: list[TrendSource] | None = None,
) -> list[TrendSignal]:
    """
    Fetch from every source, persist each observation as a TrendSignal, and
    return the newly created rows ordered by score (highest first).
    """
    sources = sources or default_sources()
    created: list[TrendSignal] = []

    for source in sources:
        try:
            observations: list[TrendObservation] = source.fetch(
                seed_keywords=seed_keywords, limit=limit_per_source
            )
        except Exception as exc:  # a single source failing must not break the whole aggregation
            logger.error(f"[aggregator] source '{source.name}' raised: {exc}")
            continue

        for obs in observations:
            row = TrendSignal(
                source=obs.source,
                platform_hint=obs.platform_hint,
                keyword=obs.keyword,
                score=obs.score,
                raw_payload=json.dumps(obs.raw, ensure_ascii=False, default=str),
            )
            db.add(row)
            created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    created.sort(key=lambda r: r.score, reverse=True)
    return created
