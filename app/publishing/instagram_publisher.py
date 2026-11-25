"""
Instagram (and Facebook Page) publishing via the Meta Graph API.

Flow for Instagram Reels (the standard container-based publish flow):
  1. POST /{ig-user-id}/media       -> create a media container (video_url, caption)
  2. Poll  GET /{container-id}?fields=status_code  until FINISHED
  3. POST /{ig-user-id}/media_publish -> publish the finished container

Requirements (document in README too):
  - The IG account must be a Business/Creator account linked to a Facebook Page.
  - For a *personal* account used only by you, Development Mode is enough —
    no App Review needed as long as you are added as a tester in the Meta app.
  - The video must be reachable at a PUBLIC url (MEDIA_PUBLIC_BASE_URL + the
    file's path under /media) — Graph API cannot accept direct file uploads
    for this endpoint.
"""
from __future__ import annotations

import time

import httpx
from loguru import logger

from app.config import settings
from app.models import ContentPiece, PlatformAccount
from app.publishing.base import PlatformPublisher, PublishResult

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300


def _public_url_for(local_path: str) -> str:
    if not settings.media_public_base_url:
        raise RuntimeError(
            "MEDIA_PUBLIC_BASE_URL is not set. Instagram's Graph API needs a "
            "publicly reachable URL for the video — it cannot accept a raw "
            "file upload. Serve ./media publicly (your domain or a tunnel) "
            "and set MEDIA_PUBLIC_BASE_URL accordingly."
        )
    media_root = str(settings.media_path)
    relative = local_path.replace(media_root, "").lstrip("/\\")
    return f"{settings.media_public_base_url.rstrip('/')}/{relative}"


class InstagramPublisher(PlatformPublisher):
    platform_name = "instagram"

    def publish(self, piece: ContentPiece, account: PlatformAccount, caption: str, hashtags: str) -> PublishResult:
        if not settings.meta_ig_business_account_id or not settings.meta_page_access_token:
            return PublishResult(
                success=False,
                error_message="META_IG_BUSINESS_ACCOUNT_ID / META_PAGE_ACCESS_TOKEN not configured",
            )
        if not piece.video_path:
            return PublishResult(success=False, error_message="ContentPiece has no video_path to publish")

        try:
            video_url = _public_url_for(piece.video_path)
            full_caption = f"{caption}\n\n{hashtags}".strip()

            with httpx.Client(timeout=60.0) as client:
                create_resp = client.post(
                    f"{GRAPH_API_BASE}/{settings.meta_ig_business_account_id}/media",
                    data={
                        "media_type": "REELS",
                        "video_url": video_url,
                        "caption": full_caption,
                        "access_token": settings.meta_page_access_token,
                    },
                )
                create_resp.raise_for_status()
                container_id = create_resp.json()["id"]

                deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
                status_code = "IN_PROGRESS"
                while status_code not in ("FINISHED", "ERROR") and time.monotonic() < deadline:
                    time.sleep(POLL_INTERVAL_SECONDS)
                    status_resp = client.get(
                        f"{GRAPH_API_BASE}/{container_id}",
                        params={"fields": "status_code", "access_token": settings.meta_page_access_token},
                    )
                    status_resp.raise_for_status()
                    status_code = status_resp.json().get("status_code", "IN_PROGRESS")
                    logger.info(f"[instagram] container {container_id} status: {status_code}")

                if status_code != "FINISHED":
                    return PublishResult(
                        success=False,
                        error_message=f"Media container did not finish processing in time (last status: {status_code})",
                    )

                publish_resp = client.post(
                    f"{GRAPH_API_BASE}/{settings.meta_ig_business_account_id}/media_publish",
                    data={"creation_id": container_id, "access_token": settings.meta_page_access_token},
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json().get("id", "")

            return PublishResult(success=True, remote_post_id=media_id)

        except httpx.HTTPStatusError as exc:
            return PublishResult(success=False, error_message=f"Graph API error: {exc.response.text}")
        except Exception as exc:
            return PublishResult(success=False, error_message=str(exc))


class FacebookPagePublisher(PlatformPublisher):
    """Posts the same video to the linked Facebook Page feed."""

    platform_name = "facebook"

    def publish(self, piece: ContentPiece, account: PlatformAccount, caption: str, hashtags: str) -> PublishResult:
        if not settings.meta_page_id or not settings.meta_page_access_token:
            return PublishResult(
                success=False, error_message="META_PAGE_ID / META_PAGE_ACCESS_TOKEN not configured"
            )
        if not piece.video_path:
            return PublishResult(success=False, error_message="ContentPiece has no video_path to publish")

        try:
            video_url = _public_url_for(piece.video_path)
            full_caption = f"{caption}\n\n{hashtags}".strip()

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{GRAPH_API_BASE}/{settings.meta_page_id}/videos",
                    data={
                        "file_url": video_url,
                        "description": full_caption,
                        "access_token": settings.meta_page_access_token,
                    },
                )
                resp.raise_for_status()
                video_id = resp.json().get("id", "")

            return PublishResult(success=True, remote_post_id=video_id)

        except httpx.HTTPStatusError as exc:
            return PublishResult(success=False, error_message=f"Graph API error: {exc.response.text}")
        except Exception as exc:
            return PublishResult(success=False, error_message=str(exc))
