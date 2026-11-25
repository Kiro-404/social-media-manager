"""
APScheduler setup. A single background job runs every minute, picks up any
ScheduledPost whose scheduled_for time has arrived and is still QUEUED,
and dispatches it to the right platform publisher.

Zero infra cost: this runs in-process alongside the FastAPI app (no Redis,
no separate worker). Fine for a personal-scale posting cadence; swap for
Celery + Redis later if the queue grows large enough to need it.
"""
from __future__ import annotations

import datetime as dt

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import PostResult, PostStatus, ScheduledPost
from app.publishing.publisher_factory import get_publisher

_scheduler: BackgroundScheduler | None = None


def _dispatch_due_posts() -> None:
    db: Session = SessionLocal()
    try:
        now = dt.datetime.utcnow()
        due_posts = (
            db.query(ScheduledPost)
            .filter(ScheduledPost.status == PostStatus.QUEUED, ScheduledPost.scheduled_for <= now)
            .all()
        )

        for post in due_posts:
            post.status = PostStatus.PUBLISHING
            db.commit()

            account = post.account
            piece = post.content_piece
            idea = piece.idea

            logger.info(f"[scheduler] publishing scheduled_post #{post.id} to {account.platform.value}")

            try:
                publisher = get_publisher(account.platform)
                result = publisher.publish(
                    piece=piece,
                    account=account,
                    caption=idea.caption,
                    hashtags=idea.hashtags,
                )
            except Exception as exc:  # a publisher bug must not crash the whole dispatch loop
                logger.error(f"[scheduler] publisher raised for scheduled_post #{post.id}: {exc}")
                from app.publishing.base import PublishResult

                result = PublishResult(success=False, error_message=str(exc))

            post.status = PostStatus.PUBLISHED if result.success else PostStatus.FAILED
            db.add(
                PostResult(
                    scheduled_post_id=post.id,
                    success=result.success,
                    remote_post_id=result.remote_post_id,
                    error_message=result.error_message,
                )
            )
            db.commit()

            if result.success:
                logger.info(f"[scheduler] scheduled_post #{post.id} published: {result.remote_post_id}")
            else:
                logger.warning(f"[scheduler] scheduled_post #{post.id} failed: {result.error_message}")

    finally:
        db.close()


def recover_interrupted_posts() -> int:
    """
    A post left in PUBLISHING means the process died mid-publish. We cannot know
    whether the platform accepted it, so re-sending automatically could post a
    duplicate. Mark it FAILED with an explanation; the user can check the
    platform and hit "retry" in the dashboard if it really did not go out.
    """
    db: Session = SessionLocal()
    try:
        stuck = db.query(ScheduledPost).filter(ScheduledPost.status == PostStatus.PUBLISHING).all()
        for post in stuck:
            post.status = PostStatus.FAILED
            if post.result is None:
                db.add(
                    PostResult(
                        scheduled_post_id=post.id,
                        success=False,
                        error_message="Interrupted while publishing (app stopped). Check the platform before retrying to avoid a duplicate.",
                    )
                )
        db.commit()
        if stuck:
            logger.warning(f"[scheduler] marked {len(stuck)} interrupted post(s) as failed")
        return len(stuck)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    recover_interrupted_posts()

    _scheduler = BackgroundScheduler(timezone=settings.timezone)
    _scheduler.add_job(_dispatch_due_posts, "interval", minutes=1, id="dispatch_due_posts")
    _scheduler.start()
    logger.info("[scheduler] started — checking for due posts every minute")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
