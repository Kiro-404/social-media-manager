"""Maps a Platform enum value to its PlatformPublisher implementation."""
from __future__ import annotations

from app.models import Platform
from app.publishing.base import PlatformPublisher
from app.publishing.instagram_publisher import FacebookPagePublisher, InstagramPublisher
from app.publishing.tiktok_publisher import TikTokPublisher
from app.publishing.twitter_publisher import TwitterPublisher
from app.publishing.youtube_publisher import YouTubePublisher

_REGISTRY: dict[Platform, type[PlatformPublisher]] = {
    Platform.YOUTUBE: YouTubePublisher,
    Platform.INSTAGRAM: InstagramPublisher,
    Platform.FACEBOOK: FacebookPagePublisher,
    Platform.TIKTOK: TikTokPublisher,
    Platform.TWITTER: TwitterPublisher,
}


def get_publisher(platform: Platform) -> PlatformPublisher:
    publisher_cls = _REGISTRY.get(platform)
    if publisher_cls is None:
        raise ValueError(f"No publisher registered for platform '{platform}'")
    return publisher_cls()
