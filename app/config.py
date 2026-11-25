"""
Central application settings, loaded from environment variables / .env.

Every external integration is optional: the app boots fine with empty keys,
and each module checks for its own required settings before doing network
work, raising a clear, specific error instead of a blind KeyError.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_env: str = "development"
    app_secret_key: str = "change-me"
    # Set to require a login for the API + dashboard (recommended before exposing beyond localhost).
    app_password: str = ""
    database_url: str = "sqlite:///./data/app.db"
    media_dir: str = "./media"
    timezone: str = "Africa/Cairo"

    # --- LLM providers ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    llm_provider: str = "gemini"  # "gemini" | "ollama"

    # --- Trend detection ---
    youtube_api_key: str = ""

    # --- Image generation ---
    pollinations_base_url: str = "https://image.pollinations.ai/prompt"

    # --- Video captions ---
    # Must be a font that has Arabic glyphs (e.g. "Noto-Sans-Arabic", "DejaVu-Sans"); see `convert -list font`.
    caption_font: str = "DejaVu-Sans"

    # --- Music ---
    jamendo_client_id: str = ""

    # --- YouTube publishing (OAuth) ---
    youtube_client_secrets_file: str = "./secrets/youtube_client_secret.json"
    youtube_token_file: str = "./secrets/youtube_token.json"

    # --- Meta (Instagram/Facebook) ---
    meta_page_id: str = ""
    meta_ig_business_account_id: str = ""
    meta_page_access_token: str = ""
    # The Graph API requires a PUBLICLY REACHABLE url for the video/image, it
    # cannot accept a raw file upload for Reels/posts. Point this at wherever
    # your /media directory is served from (your own domain, or a tunnel like
    # ngrok/Cloudflare Tunnel during development) with NO trailing slash.
    media_public_base_url: str = ""

    # --- TikTok ---
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_access_token: str = ""

    # --- Twitter/X ---
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_secret: str = ""

    @property
    def media_path(self) -> Path:
        p = Path(self.media_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
