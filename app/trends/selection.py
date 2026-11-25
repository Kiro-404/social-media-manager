"""
Choosing a default trend when the user doesn't pick one.

Raw scores aren't comparable across sources (YouTube = view counts in the
millions, Google Trends = a small rank-based number), so a plain "highest
score" would always pick YouTube. We take the latest collection batch and
rank by score relative to the best score *within the same source*.
"""
from __future__ import annotations

import datetime as dt
from typing import Sequence, TypeVar

T = TypeVar("T")  # anything with .source, .score, .fetched_at (a TrendSignal, or a test double)

BATCH_WINDOW = dt.timedelta(minutes=10)


def pick_default_trend(trends: Sequence[T]) -> T | None:
    if not trends:
        return None
    newest = max(t.fetched_at for t in trends)
    batch = [t for t in trends if newest - t.fetched_at <= BATCH_WINDOW]

    best_per_source: dict[str, float] = {}
    for t in batch:
        best_per_source[t.source] = max(best_per_source.get(t.source, 0.0), t.score)

    def relative(t: T) -> float:
        top = best_per_source[t.source]
        return t.score / top if top > 0 else 0.0

    return max(batch, key=lambda t: (relative(t), t.score))
