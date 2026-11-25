from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PlatformAccount
from app.schemas import PlatformAccountCreate, PlatformAccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=PlatformAccountOut)
def create_account(payload: PlatformAccountCreate, db: Session = Depends(get_db)) -> PlatformAccount:
    account = PlatformAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[PlatformAccountOut])
def list_accounts(db: Session = Depends(get_db)) -> list[PlatformAccount]:
    return db.query(PlatformAccount).order_by(PlatformAccount.created_at.desc()).all()


@router.get("/{account_id}", response_model=PlatformAccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)) -> PlatformAccount:
    account = db.get(PlatformAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.delete("/{account_id}")
def deactivate_account(account_id: int, db: Session = Depends(get_db)) -> dict:
    account = db.get(PlatformAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    db.commit()
    return {"ok": True}
