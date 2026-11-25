"""
Twitter/X publisher via tweepy.

Media upload still goes through the v1.1 endpoint (v2 has no native media
upload yet), then the tweet itself is created through v2. The free tier
(as of writing) allows a limited number of posts per month — plenty for a
personal-scale posting cadence.
"""
from __future__ import annotations

import os

import tweepy
from loguru import logger

from app.config import settings
from app.models import ContentPiece, PlatformAccount
from app.publishing.base import PlatformPublisher, PublishResult


def _build_clients() -> tuple[tweepy.API, tweepy.Client]:
    auth = tweepy.OAuth1UserHandler(
        settings.twitter_api_key,
        settings.twitter_api_secret,
        settings.twitter_access_token,
        settings.twitter_access_secret,
    )
    api_v1 = tweepy.API(auth)

    client_v2 = tweepy.Client(
        consumer_key=settings.twitter_api_key,
        consumer_secret=settings.twitter_api_secret,
        access_token=settings.twitter_access_token,
        access_token_secret=settings.twitter_access_secret,
    )
    return api_v1, client_v2


class TwitterPublisher(PlatformPublisher):
    platform_name = "twitter"

    def publish(self, piece: ContentPiece, account: PlatformAccount, caption: str, hashtags: str) -> PublishResult:
        required = [
            settings.twitter_api_key,
            settings.twitter_api_secret,
            settings.twitter_access_token,
            settings.twitter_access_secret,
        ]
        if not all(required):
            return PublishResult(success=False, error_message="Twitter/X API credentials not fully configured")

        media_path = piece.video_path or piece.image_path
        if not media_path or not os.path.exists(media_path):
            return PublishResult(success=False, error_message="ContentPiece has no media file to attach")

        full_text = f"{caption}\n\n{hashtags}".strip()
        # Twitter/X character limit for non-premium accounts.
        if len(full_text) > 280:
            full_text = full_text[:277] + "..."

        try:
            api_v1, client_v2 = _build_clients()

            logger.info(f"[twitter] uploading media: {media_path}")
            media = api_v1.media_upload(filename=media_path, media_category="tweet_video" if piece.video_path else "tweet_image")

            response = client_v2.create_tweet(text=full_text, media_ids=[media.media_id])
            tweet_id = str(response.data.get("id", ""))

            return PublishResult(success=True, remote_post_id=tweet_id)

        except tweepy.TweepyException as exc:
            return PublishResult(success=False, error_message=f"Twitter API error: {exc}")
        except Exception as exc:
            return PublishResult(success=False, error_message=str(exc))
