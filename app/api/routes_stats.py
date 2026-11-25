from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ContentIdea,
    ContentPiece,
    Niche,
    PlatformAccount,
    PostStatus,
    ScheduledPost,
    TrendSignal,
)
from app.schemas import StatsOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)) -> StatsOut:
    def count(model) -> int:
        return db.query(func.count(model.id)).scalar() or 0

    by_status = dict(db.query(ScheduledPost.status, func.count(ScheduledPost.id)).group_by(ScheduledPost.status).all())
    return StatsOut(
        niches=count(Niche),
        accounts=db.query(func.count(PlatformAccount.id)).filter(PlatformAccount.is_active.is_(True)).scalar() or 0,
        trends=count(TrendSignal),
        ideas=count(ContentIdea),
        pieces=count(ContentPiece),
        queued=by_status.get(PostStatus.QUEUED, 0),
        published=by_status.get(PostStatus.PUBLISHED, 0),
        failed=by_status.get(PostStatus.FAILED, 0),
    )
