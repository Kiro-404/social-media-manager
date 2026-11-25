from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.media_utils import media_url
from app.models import ContentPiece, PlatformAccount, PostResult, PostStatus, ScheduledPost
from app.schemas import ScheduledPostCreate, ScheduledPostDetailOut, ScheduledPostOut
from app.timeutil import to_utc_naive, utc_naive_to_iso

router = APIRouter(prefix="/schedule", tags=["schedule"])

# Allow "schedule for right now" without tripping over a few seconds of clock skew.
_PAST_TOLERANCE = dt.timedelta(seconds=60)


def _detail(post: ScheduledPost) -> ScheduledPostDetailOut:
    piece = post.content_piece
    result = post.result
    return ScheduledPostDetailOut(
        id=post.id,
        content_piece_id=post.content_piece_id,
        account_id=post.account_id,
        scheduled_for=post.scheduled_for,
        status=post.status,
        created_at=post.created_at,
        platform=post.account.platform,
        account_name=post.account.display_name,
        idea_title=piece.idea.title if piece and piece.idea else "",
        video_url=media_url(piece.video_path, settings.media_path) if piece else "",
        image_url=media_url(piece.image_path, settings.media_path) if piece else "",
        success=result.success if result else None,
        remote_post_id=result.remote_post_id if result else "",
        error_message=result.error_message if result else "",
    )


@router.post("", response_model=ScheduledPostOut)
def schedule_post(payload: ScheduledPostCreate, db: Session = Depends(get_db)) -> ScheduledPost:
    piece = db.get(ContentPiece, payload.content_piece_id)
    if not piece:
        raise HTTPException(status_code=404, detail="Content piece not found")

    account = db.get(PlatformAccount, payload.account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Active platform account not found")

    # Naive input = local wall-clock time in settings.timezone; stored as naive UTC.
    when_utc = to_utc_naive(payload.scheduled_for, settings.timezone)
    if when_utc < dt.datetime.utcnow() - _PAST_TOLERANCE:
        raise HTTPException(status_code=400, detail="scheduled_for is in the past")

    post = ScheduledPost(
        content_piece_id=payload.content_piece_id,
        account_id=payload.account_id,
        scheduled_for=when_utc,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("", response_model=list[ScheduledPostDetailOut])
def list_scheduled_posts(
    account_id: int | None = None,
    status: PostStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ScheduledPostDetailOut]:
    query = db.query(ScheduledPost).options(
        joinedload(ScheduledPost.account),
        joinedload(ScheduledPost.content_piece).joinedload(ContentPiece.idea),
        joinedload(ScheduledPost.result),
    )
    if account_id is not None:
        query = query.filter(ScheduledPost.account_id == account_id)
    if status is not None:
        query = query.filter(ScheduledPost.status == status)
    return [_detail(p) for p in query.order_by(ScheduledPost.scheduled_for.asc()).all()]


@router.delete("/{scheduled_post_id}")
def cancel_scheduled_post(scheduled_post_id: int, db: Session = Depends(get_db)) -> dict:
    post = db.get(ScheduledPost, scheduled_post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if post.status != PostStatus.QUEUED:
        raise HTTPException(status_code=409, detail=f"Cannot cancel a post with status '{post.status.value}'")
    post.status = PostStatus.CANCELLED
    db.commit()
    return {"ok": True}


@router.post("/{scheduled_post_id}/retry", response_model=ScheduledPostOut)
def retry_failed_post(scheduled_post_id: int, db: Session = Depends(get_db)) -> ScheduledPost:
    """Re-queue a FAILED post to be dispatched on the next scheduler tick."""
    post = db.get(ScheduledPost, scheduled_post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    if post.status != PostStatus.FAILED:
        raise HTTPException(status_code=409, detail=f"Only failed posts can be retried (status is '{post.status.value}')")

    # PostResult.scheduled_post_id is UNIQUE, so the old failure record must go
    # before the scheduler writes the outcome of the new attempt.
    if post.result is not None:
        db.delete(post.result)
    post.status = PostStatus.QUEUED
    post.scheduled_for = dt.datetime.utcnow()
    db.commit()
    db.refresh(post)
    return post


@router.get("/{scheduled_post_id}/result")
def get_post_result(scheduled_post_id: int, db: Session = Depends(get_db)) -> dict:
    result = db.query(PostResult).filter(PostResult.scheduled_post_id == scheduled_post_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="No result yet for this scheduled post")
    return {
        "success": result.success,
        "remote_post_id": result.remote_post_id,
        "error_message": result.error_message,
        "attempted_at": utc_naive_to_iso(result.attempted_at),
    }
