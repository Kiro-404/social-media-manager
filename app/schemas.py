"""Pydantic request/response schemas for the API layer."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, computed_field, field_serializer

from app.config import settings
from app.media_utils import media_url
from app.models import Platform, PostStatus
from app.timeutil import utc_naive_to_iso


# --- Niche ---
class NicheCreate(BaseModel):
    name: str
    description: str = ""
    target_audience: str = ""
    tone_of_voice: str = ""
    language: str = "ar"


class NicheOut(NicheCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: dt.datetime


# --- Platform account ---
class PlatformAccountCreate(BaseModel):
    platform: Platform
    display_name: str = ""
    external_account_id: str = ""


class PlatformAccountOut(PlatformAccountCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: dt.datetime


# --- Trend signal ---
class TrendSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    platform_hint: str
    keyword: str
    score: float
    fetched_at: dt.datetime

    @field_serializer("fetched_at")
    def _ser_fetched_at(self, v: dt.datetime) -> str:
        return utc_naive_to_iso(v)


# --- Content idea ---
class IdeaGenerateRequest(BaseModel):
    niche_id: int
    trend_signal_id: int | None = None
    """If omitted, the freshest unfiltered trend signal is used."""


class ContentIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    niche_id: int
    trend_signal_id: int | None
    title: str
    angle: str
    script: str
    caption: str
    hashtags: str
    created_at: dt.datetime


class ContentIdeaUpdate(BaseModel):
    """Partial update used when reviewing/editing a generated idea before producing media."""

    title: str | None = None
    angle: str | None = None
    script: str | None = None
    caption: str | None = None
    hashtags: str | None = None


# --- Content piece ---
class ContentPieceGenerateRequest(BaseModel):
    idea_id: int
    with_audio: bool = True
    with_image: bool = True
    with_video: bool = True


class ContentPieceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    idea_id: int
    audio_path: str
    image_path: str
    video_path: str
    created_at: dt.datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def audio_url(self) -> str:
        return media_url(self.audio_path, settings.media_path)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> str:
        return media_url(self.image_path, settings.media_path)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def video_url(self) -> str:
        return media_url(self.video_path, settings.media_path)


# --- Scheduled post ---
class ScheduledPostCreate(BaseModel):
    content_piece_id: int
    account_id: int
    scheduled_for: dt.datetime


class ScheduledPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content_piece_id: int
    account_id: int
    scheduled_for: dt.datetime
    status: PostStatus
    created_at: dt.datetime

    @field_serializer("scheduled_for", "created_at")
    def _ser_dt(self, v: dt.datetime) -> str:
        return utc_naive_to_iso(v)


class ScheduledPostDetailOut(ScheduledPostOut):
    """Scheduled post joined with everything the dashboard needs to render a row."""

    platform: Platform
    account_name: str = ""
    idea_title: str = ""
    video_url: str = ""
    image_url: str = ""
    success: bool | None = None
    remote_post_id: str = ""
    error_message: str = ""


# --- Dashboard stats ---
class StatsOut(BaseModel):
    niches: int
    accounts: int
    trends: int
    ideas: int
    pieces: int
    queued: int
    published: int
    failed: int
