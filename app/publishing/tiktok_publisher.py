"""
TikTok publisher via the Content Posting API (Direct Post, v2).

IMPORTANT — unaudited-app limitation: until your TikTok developer app passes
TikTok's audit, videos posted through this endpoint can only use
privacy_level="SELF_ONLY" (i.e. they land as a private/draft post visible
only to the posting account, not publicly). This is documented behavior,
not a bug here — see TikTok's Content Posting API docs. Once your app is
audited you can widen PRIVACY_LEVEL in config.

Flow:
  1. POST /v2/post/publish/video/init/  -> get an upload_url + publish_id
  2. PUT the raw video bytes to that upload_url
  3. (optional) GET /v2/post/publish/status/fetch/ to confirm processing
"""
from __future__ import annotations

import os
import time

import httpx
from loguru import logger

from app.config import settings
from app.models import ContentPiece, PlatformAccount
from app.publishing.base import PlatformPublisher, PublishResult

API_BASE = "https://open.tiktokapis.com/v2"
PRIVACY_LEVEL = "SELF_ONLY"  # widen once your app is audited by TikTok
POLL_INTERVAL_SECONDS = 5
POLL_ATTEMPTS = 12


class TikTokPublisher(PlatformPublisher):
    platform_name = "tiktok"

    def publish(self, piece: ContentPiece, account: PlatformAccount, caption: str, hashtags: str) -> PublishResult:
        if not settings.tiktok_access_token:
            return PublishResult(success=False, error_message="TIKTOK_ACCESS_TOKEN not configured")
        if not piece.video_path or not os.path.exists(piece.video_path):
            return PublishResult(success=False, error_message="ContentPiece has no valid video_path")

        headers = {
            "Authorization": f"Bearer {settings.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        video_size = os.path.getsize(piece.video_path)
        full_caption = f"{caption} {hashtags}".strip()

        try:
            with httpx.Client(timeout=60.0) as client:
                init_resp = client.post(
                    f"{API_BASE}/post/publish/video/init/",
                    headers=headers,
                    json={
                        "post_info": {
                            "title": full_caption[:150],
                            "privacy_level": PRIVACY_LEVEL,
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False,
                        },
                        "source_info": {
                            "source": "FILE_UPLOAD",
                            "video_size": video_size,
                            "chunk_size": video_size,
                            "total_chunk_count": 1,
                        },
                    },
                )
                init_resp.raise_for_status()
                init_data = init_resp.json().get("data", {})
                upload_url = init_data.get("upload_url")
                publish_id = init_data.get("publish_id", "")

                if not upload_url:
                    return PublishResult(
                        success=False, error_message=f"No upload_url returned: {init_resp.text}"
                    )

                with open(piece.video_path, "rb") as f:
                    video_bytes = f.read()

                upload_resp = client.put(
                    upload_url,
                    content=video_bytes,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
                    },
                )
                upload_resp.raise_for_status()

                # Best-effort status poll; TikTok processes async.
                for _ in range(POLL_ATTEMPTS):
                    time.sleep(POLL_INTERVAL_SECONDS)
                    status_resp = client.post(
                        f"{API_BASE}/post/publish/status/fetch/",
                        headers=headers,
                        json={"publish_id": publish_id},
                    )
                    if status_resp.status_code == 200:
                        status = status_resp.json().get("data", {}).get("status", "")
                        logger.info(f"[tiktok] publish {publish_id} status: {status}")
                        if status in ("PUBLISH_COMPLETE", "FAILED"):
                            break

            return PublishResult(success=True, remote_post_id=publish_id)

        except httpx.HTTPStatusError as exc:
            return PublishResult(success=False, error_message=f"TikTok API error: {exc.response.text}")
        except Exception as exc:
            return PublishResult(success=False, error_message=str(exc))
