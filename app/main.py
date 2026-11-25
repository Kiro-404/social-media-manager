"""
FastAPI entrypoint. Run with:

    uvicorn app.main:app --reload

On startup: creates DB tables if missing, and starts the background
scheduler that dispatches due ScheduledPost rows to the right publisher.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import routes_auth, routes_accounts, routes_content, routes_niches, routes_schedule, routes_stats, routes_trends
from app.auth import is_public_path, verify_token
from app.config import settings
from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting scheduler...")
    start_scheduler()
    yield
    logger.info("Shutting down scheduler...")
    stop_scheduler()


app = FastAPI(
    title="Social Media Manager",
    description="Open-source personal social media content & publishing assistant.",
    version="0.1.0",
    lifespan=lifespan,
)

if settings.app_password and settings.app_secret_key == "change-me":
    logger.warning("APP_PASSWORD is set but APP_SECRET_KEY is still the default — set a random APP_SECRET_KEY.")

# Local-first tool: permissive CORS so a local React dashboard can talk to it
# during development. Tighten this before exposing the API beyond localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def require_login(request: Request, call_next):
    if settings.app_password and request.method != "OPTIONS" and not is_public_path(request.url.path):
        token = request.cookies.get(routes_auth.COOKIE)
        if not verify_token(token, settings.app_secret_key, settings.app_password):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return await call_next(request)


app.include_router(routes_auth.router)
app.include_router(routes_niches.router)
app.include_router(routes_accounts.router)
app.include_router(routes_trends.router)
app.include_router(routes_content.router)
app.include_router(routes_schedule.router)
app.include_router(routes_stats.router)

# Generated media (needed for dashboard previews, and as the public source URL
# the Instagram/Facebook Graph API pulls videos from — see MEDIA_PUBLIC_BASE_URL).
app.mount("/media", StaticFiles(directory=str(settings.media_path)), name="media")

# Zero-build dashboard (plain HTML/JS). Mounted last so API routes win.
_DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
if _DASHBOARD_DIR.is_dir():
    app.mount("/dashboard", StaticFiles(directory=str(_DASHBOARD_DIR), html=True), name="dashboard")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/")


@app.get("/health")
def health() -> dict:
    # timezone lets the dashboard display times in the same zone the API interprets them in
    return {"status": "ok", "timezone": settings.timezone}
