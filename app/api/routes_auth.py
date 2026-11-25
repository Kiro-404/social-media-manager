from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth import SESSION_TTL_SECONDS, create_token, password_ok, verify_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "smm_session"


class LoginRequest(BaseModel):
    password: str


@router.get("/status")
def status(request: Request) -> dict:
    required = bool(settings.app_password)
    ok = (not required) or verify_token(request.cookies.get(COOKIE), settings.app_secret_key, settings.app_password)
    return {"required": required, "authenticated": ok}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    if not settings.app_password:
        return {"ok": True}
    if not password_ok(payload.password, settings.app_password):
        time.sleep(1)  # cheap brute-force slowdown for a single-user tool
        raise HTTPException(status_code=401, detail="Wrong password")
    response.set_cookie(
        COOKIE,
        create_token(settings.app_secret_key, settings.app_password),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE)
    return {"ok": True}
