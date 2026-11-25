"""
Image generation via Pollinations.ai — free, no API key required for basic
use. A simple GET against an image-generating endpoint; good enough for
story/cover backgrounds without running a local Stable Diffusion instance.

If the user later adds a GPU box, swap this module's implementation for a
local Stable Diffusion call — the function signature stays the same so
nothing else in the pipeline needs to change.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def generate_image(prompt: str, filename: str, width: int = 1080, height: int = 1920) -> str:
    """
    Generate an image for `prompt` (vertical by default, matching
    Reels/Shorts/Stories aspect ratio) and save it under the media
    directory. Returns the relative path to the written file.
    """
    url = f"{settings.pollinations_base_url}/{quote(prompt)}?width={width}&height={height}&nologo=true"

    out_path = settings.media_path / "images" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"[image_generator] requesting image for prompt: {prompt[:80]!r}")
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url)
        response.raise_for_status()
        out_path.write_bytes(response.content)

    return str(out_path)
