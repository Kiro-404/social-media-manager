"""
YouTube publisher — uploads a video via the Data API v3 (resumable upload).

Auth: OAuth2 "installed app" flow. The first run opens a browser for
consent and caches the resulting token at YOUTUBE_TOKEN_FILE; subsequent
runs reuse (and silently refresh) that token — no browser needed again
until the refresh token itself is revoked.

Free quota: 10,000 units/day; one video upload costs ~1,600 units, so
roughly 6 uploads/day on the free tier.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from loguru import logger

from app.config import settings
from app.models import ContentPiece, PlatformAccount
from app.publishing.base import PlatformPublisher, PublishResult

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_credentials() -> Credentials:
    token_path = Path(settings.youtube_token_file)
    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secrets_path = Path(settings.youtube_client_secrets_file)
            if not secrets_path.exists():
                raise RuntimeError(
                    f"YouTube OAuth client secrets not found at {secrets_path}. "
                    "Download it from Google Cloud Console (APIs & Services > Credentials) "
                    "and point YOUTUBE_CLIENT_SECRETS_FILE at it."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return creds


class YouTubePublisher(PlatformPublisher):
    platform_name = "youtube"

    def publish(self, piece: ContentPiece, account: PlatformAccount, caption: str, hashtags: str) -> PublishResult:
        if not piece.video_path:
            return PublishResult(success=False, error_message="ContentPiece has no video_path to upload")

        try:
            creds = _get_credentials()
            youtube = build("youtube", "v3", credentials=creds)

            tags = [h.lstrip("#") for h in hashtags.split() if h.strip()]
            body = {
                "snippet": {
                    "title": caption[:95] or "New upload",
                    "description": f"{caption}\n\n{hashtags}".strip(),
                    "tags": tags,
                    "categoryId": "22",  # People & Blogs; adjust per niche if desired
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
            }

            media = MediaFileUpload(piece.video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"[youtube] upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id", "")
            return PublishResult(success=True, remote_post_id=video_id)

        except HttpError as exc:
            return PublishResult(success=False, error_message=f"YouTube API error: {exc}")
        except Exception as exc:
            return PublishResult(success=False, error_message=str(exc))
