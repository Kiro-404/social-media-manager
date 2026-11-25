"""
Core database models for the pipeline:

Niche            -> the content context/topic the user manages this tool for
PlatformAccount  -> one connected social account (one row per platform)
TrendSignal      -> a trend observation pulled from a TrendSource
ContentIdea      -> an LLM-generated idea tying a TrendSignal to a Niche
ContentPiece     -> the generated assets (text/audio/image/video) for an idea
ScheduledPost    -> a ContentPiece queued for publishing on a PlatformAccount
PostResult       -> the outcome of an attempted publish
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    TWITTER = "twitter"


class PostStatus(str, enum.Enum):
    QUEUED = "queued"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Niche(Base):
    """The subject matter / brand voice the user wants content generated for."""

    __tablename__ = "niches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    tone_of_voice: Mapped[str] = mapped_column(String(255), default="")
    language: Mapped[str] = mapped_column(String(16), default="ar")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    ideas: Mapped[list["ContentIdea"]] = relationship(back_populates="niche")


class PlatformAccount(Base):
    """One connected social account that the tool is allowed to publish to."""

    __tablename__ = "platform_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    external_account_id: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship(back_populates="account")


class TrendSignal(Base):
    """A single trend observation, e.g. a rising search term or a trending video topic."""

    __tablename__ = "trend_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)  # "google_trends" | "youtube"
    platform_hint: Mapped[str] = mapped_column(String(32), default="")
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(default=0.0)
    raw_payload: Mapped[str] = mapped_column(Text, default="")  # JSON string for traceability
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    ideas: Mapped[list["ContentIdea"]] = relationship(back_populates="trend_signal")


class ContentIdea(Base):
    """An LLM-generated idea that ties a TrendSignal to a Niche."""

    __tablename__ = "content_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    niche_id: Mapped[int] = mapped_column(ForeignKey("niches.id"), nullable=False)
    trend_signal_id: Mapped[int | None] = mapped_column(ForeignKey("trend_signals.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    angle: Mapped[str] = mapped_column(Text, default="")  # why this idea fits the niche + trend
    script: Mapped[str] = mapped_column(Text, default="")  # the generated text/voiceover script
    caption: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[str] = mapped_column(Text, default="")  # space-separated
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    niche: Mapped[Niche] = relationship(back_populates="ideas")
    trend_signal: Mapped[TrendSignal | None] = relationship(back_populates="ideas")
    content_pieces: Mapped[list["ContentPiece"]] = relationship(back_populates="idea")


class ContentPiece(Base):
    """The generated media assets for a ContentIdea, ready to be scheduled."""

    __tablename__ = "content_pieces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("content_ideas.id"), nullable=False)
    audio_path: Mapped[str] = mapped_column(String(512), default="")
    image_path: Mapped[str] = mapped_column(String(512), default="")
    video_path: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    idea: Mapped[ContentIdea] = relationship(back_populates="content_pieces")
    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship(back_populates="content_piece")


class ScheduledPost(Base):
    """A ContentPiece queued for publishing to a specific PlatformAccount at a given time."""

    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_piece_id: Mapped[int] = mapped_column(ForeignKey("content_pieces.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("platform_accounts.id"), nullable=False)
    scheduled_for: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus), default=PostStatus.QUEUED)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    content_piece: Mapped[ContentPiece] = relationship(back_populates="scheduled_posts")
    account: Mapped[PlatformAccount] = relationship(back_populates="scheduled_posts")
    result: Mapped["PostResult | None"] = relationship(back_populates="scheduled_post", uselist=False)


class PostResult(Base):
    """The outcome of an attempted publish — success with the remote post id, or an error."""

    __tablename__ = "post_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheduled_post_id: Mapped[int] = mapped_column(ForeignKey("scheduled_posts.id"), unique=True, nullable=False)
    success: Mapped[bool] = mapped_column(default=False)
    remote_post_id: Mapped[str] = mapped_column(String(255), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    attempted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    scheduled_post: Mapped[ScheduledPost] = relationship(back_populates="result")
