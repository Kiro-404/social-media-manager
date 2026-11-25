"""Common interface every trend source implements."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field


@dataclass
class TrendObservation:
    source: str
    keyword: str
    score: float
    platform_hint: str = ""
    raw: dict = field(default_factory=dict)


class TrendSource(abc.ABC):
    """A pluggable source of trend observations (Google Trends, YouTube, ...)."""

    name: str

    @abc.abstractmethod
    def fetch(self, seed_keywords: list[str] | None = None, limit: int = 10) -> list[TrendObservation]:
        """
        Return up to `limit` trend observations.

        `seed_keywords`, when given, scopes the lookup (e.g. related queries around
        the user's niche) instead of a generic "what's trending everywhere" pull.
        """
        raise NotImplementedError
