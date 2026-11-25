"""
Text-to-speech via edge-tts: free, no API key, good Arabic voice coverage.

Arabic voices available as of writing include ar-EG-SalmaNeural (Egyptian,
female) and ar-EG-ShakirNeural (Egyptian, male) — picked by default since
most of this project's content is Arabic, but overridable per call.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from app.config import settings

DEFAULT_VOICE = "ar-EG-SalmaNeural"


async def _synthesize(text: str, voice: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def generate_voiceover(text: str, filename: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Synthesize `text` to an mp3 under the media directory and return the
    relative path to the written file.
    """
    out_path = settings.media_path / "audio" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(_synthesize(text, voice, out_path))
    return str(out_path)


async def list_arabic_voices() -> list[dict]:
    """Helper for exploring available Arabic voices (ar-EG, ar-SA, etc.)."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith("ar-")]
