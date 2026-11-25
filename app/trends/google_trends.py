"""
Google Trends source via pytrends (unofficial but widely used, free, no API key).

This is the safest free trend signal available: it reads Google's own public
trends UI data, not a social platform's private endpoints, so it carries none
of the account-ban risk that scraping TikTok/Instagram directly would.
"""
from __future__ import annotations

from loguru import logger
from pytrends.request import TrendReq

from app.trends.base import TrendObservation, TrendSource


class GoogleTrendsSource(TrendSource):
    name = "google_trends"

    def __init__(self, hl: str = "ar", tz: int = 120, geo: str = "EG"):
        """
        hl  : interface language for trend labels (ar = Arabic)
        tz  : timezone offset in minutes (Africa/Cairo = UTC+2 -> 120)
        geo : two-letter country code to scope "trending now" results
        """
        self.hl = hl
        self.tz = tz
        self.geo = geo

    def _client(self) -> TrendReq:
        return TrendReq(hl=self.hl, tz=self.tz)

    def fetch(self, seed_keywords: list[str] | None = None, limit: int = 10) -> list[TrendObservation]:
        pytrends = self._client()
        observations: list[TrendObservation] = []

        if seed_keywords:
            # Scoped mode: rising related queries for the user's own niche keywords.
            try:
                pytrends.build_payload(seed_keywords[:5], timeframe="now 7-d", geo=self.geo)
                related = pytrends.related_queries()
                for kw, payload in related.items():
                    rising = payload.get("rising")
                    if rising is None:
                        continue
                    for _, row in rising.iterrows():
                        observations.append(
                            TrendObservation(
                                source=self.name,
                                keyword=str(row["query"]),
                                score=float(row.get("value", 0) or 0),
                                platform_hint="general",
                                raw={"seed": kw, "row": row.to_dict()},
                            )
                        )
            except Exception as exc:  # pytrends raises assorted errors on rate limiting/empty data
                logger.warning(f"[google_trends] scoped fetch failed: {exc}")
        else:
            # Unscoped mode: today's broad trending searches for the configured country.
            try:
                df = pytrends.trending_searches(pn="egypt" if self.geo == "EG" else "united_states")
                for rank, row in df.iterrows():
                    observations.append(
                        TrendObservation(
                            source=self.name,
                            keyword=str(row[0]),
                            score=float(max(limit - rank, 1)),
                            platform_hint="general",
                            raw={"rank": int(rank)},
                        )
                    )
            except Exception as exc:
                logger.warning(f"[google_trends] trending_searches failed: {exc}")

        observations.sort(key=lambda o: o.score, reverse=True)
        return observations[:limit]
