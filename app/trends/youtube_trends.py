"""
YouTube "most popular" videos as a trend source — 100% official API, no
scraping risk at all. Uses the public videos.list(chart=mostPopular)
endpoint, which only needs an API key (no OAuth).
"""
from __future__ import annotations

from loguru import logger
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.trends.base import TrendObservation, TrendSource


class YouTubeTrendsSource(TrendSource):
    name = "youtube"

    def __init__(self, region_code: str = "EG"):
        self.region_code = region_code

    def fetch(self, seed_keywords: list[str] | None = None, limit: int = 10) -> list[TrendObservation]:
        if not settings.youtube_api_key:
            logger.warning("[youtube_trends] YOUTUBE_API_KEY not set — skipping this source")
            return []

        youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)
        observations: list[TrendObservation] = []

        try:
            request = youtube.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode=self.region_code,
                maxResults=min(limit, 50),
            )
            response = request.execute()
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                title = snippet.get("title", "")
                category_id = snippet.get("categoryId", "")
                view_count = float(stats.get("viewCount", 0) or 0)

                # Skip if seed_keywords given and title doesn't loosely match the niche.
                if seed_keywords and not any(kw.lower() in title.lower() for kw in seed_keywords):
                    continue

                observations.append(
                    TrendObservation(
                        source=self.name,
                        keyword=title,
                        score=view_count,
                        platform_hint="youtube",
                        raw={"video_id": item.get("id"), "category_id": category_id},
                    )
                )
        except HttpError as exc:
            logger.warning(f"[youtube_trends] API error: {exc}")

        observations.sort(key=lambda o: o.score, reverse=True)
        return observations[:limit]
