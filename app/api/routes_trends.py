from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TrendSignal
from app.schemas import TrendSignalOut
from app.trends.aggregator import collect_trends

router = APIRouter(prefix="/trends", tags=["trends"])


@router.post("/collect", response_model=list[TrendSignalOut])
def trigger_trend_collection(
    seed_keywords: list[str] | None = None,
    limit_per_source: int = 10,
    db: Session = Depends(get_db),
) -> list[TrendSignal]:
    """Fetch fresh trend signals right now from every configured source."""
    return collect_trends(db, seed_keywords=seed_keywords, limit_per_source=limit_per_source)


@router.get("", response_model=list[TrendSignalOut])
def list_recent_trends(limit: int = 50, db: Session = Depends(get_db)) -> list[TrendSignal]:
    return db.query(TrendSignal).order_by(TrendSignal.fetched_at.desc()).limit(limit).all()
