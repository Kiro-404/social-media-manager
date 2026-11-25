from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.content.pipeline import generate_content_piece
from app.database import get_db
from app.ideation.idea_generator import generate_idea
from app.models import ContentIdea, ContentPiece, Niche, TrendSignal
from app.trends.selection import pick_default_trend
from app.schemas import (
    ContentIdeaOut,
    ContentIdeaUpdate,
    ContentPieceGenerateRequest,
    ContentPieceOut,
    IdeaGenerateRequest,
)

router = APIRouter(prefix="/content", tags=["content"])


@router.post("/ideas", response_model=ContentIdeaOut)
def create_idea(payload: IdeaGenerateRequest, db: Session = Depends(get_db)) -> ContentIdea:
    niche = db.get(Niche, payload.niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    trend: TrendSignal | None = None
    if payload.trend_signal_id is not None:
        trend = db.get(TrendSignal, payload.trend_signal_id)
        if not trend:
            raise HTTPException(status_code=404, detail="Trend signal not found")
    else:
        recent = db.query(TrendSignal).order_by(TrendSignal.fetched_at.desc()).limit(200).all()
        trend = pick_default_trend(recent)

    try:
        return generate_idea(db, niche=niche, trend=trend)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Idea generation failed: {exc}") from exc


@router.get("/ideas", response_model=list[ContentIdeaOut])
def list_ideas(niche_id: int | None = None, db: Session = Depends(get_db)) -> list[ContentIdea]:
    query = db.query(ContentIdea)
    if niche_id is not None:
        query = query.filter(ContentIdea.niche_id == niche_id)
    return query.order_by(ContentIdea.created_at.desc()).all()


@router.patch("/ideas/{idea_id}", response_model=ContentIdeaOut)
def update_idea(idea_id: int, payload: ContentIdeaUpdate, db: Session = Depends(get_db)) -> ContentIdea:
    """Edit an idea's text before generating media — the 'review before it goes out' step."""
    idea = db.get(ContentIdea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Content idea not found")
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(idea, field, value)
    db.commit()
    db.refresh(idea)
    return idea


@router.delete("/ideas/{idea_id}")
def delete_idea(idea_id: int, db: Session = Depends(get_db)) -> dict:
    idea = db.get(ContentIdea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Content idea not found")
    if idea.content_pieces:
        raise HTTPException(status_code=409, detail="Idea already has generated content pieces and cannot be deleted")
    db.delete(idea)
    db.commit()
    return {"ok": True}


@router.post("/pieces", response_model=ContentPieceOut)
def create_content_piece(payload: ContentPieceGenerateRequest, db: Session = Depends(get_db)) -> ContentPiece:
    idea = db.get(ContentIdea, payload.idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Content idea not found")

    try:
        return generate_content_piece(
            db,
            idea=idea,
            with_audio=payload.with_audio,
            with_image=payload.with_image,
            with_video=payload.with_video,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Content generation failed: {exc}") from exc


@router.get("/pieces", response_model=list[ContentPieceOut])
def list_content_pieces(idea_id: int | None = None, db: Session = Depends(get_db)) -> list[ContentPiece]:
    query = db.query(ContentPiece)
    if idea_id is not None:
        query = query.filter(ContentPiece.idea_id == idea_id)
    return query.order_by(ContentPiece.created_at.desc()).all()
