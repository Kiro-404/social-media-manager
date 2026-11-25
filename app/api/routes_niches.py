from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Niche
from app.schemas import NicheCreate, NicheOut

router = APIRouter(prefix="/niches", tags=["niches"])


@router.post("", response_model=NicheOut)
def create_niche(payload: NicheCreate, db: Session = Depends(get_db)) -> Niche:
    niche = Niche(**payload.model_dump())
    db.add(niche)
    db.commit()
    db.refresh(niche)
    return niche


@router.get("", response_model=list[NicheOut])
def list_niches(db: Session = Depends(get_db)) -> list[Niche]:
    return db.query(Niche).order_by(Niche.created_at.desc()).all()


@router.get("/{niche_id}", response_model=NicheOut)
def get_niche(niche_id: int, db: Session = Depends(get_db)) -> Niche:
    niche = db.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    return niche
