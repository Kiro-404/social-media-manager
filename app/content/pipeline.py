"""
Orchestrates the content-generation stage: takes a ContentIdea and produces
a ContentPiece (audio/image/video file paths), using only free tools.
"""
from __future__ import annotations

import re
import uuid

from loguru import logger
from sqlalchemy.orm import Session

from app.content.image_generator import generate_image
from app.content.tts_generator import generate_voiceover
from app.content.video_assembler import assemble_video
from app.models import ContentIdea, ContentPiece


def _safe_slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w؀-ۿ]+", "-", text.strip()).strip("-")
    return (slug or "idea")[:max_len]


def _image_prompt_from_idea(idea: ContentIdea) -> str:
    """
    Build a visual prompt from the idea's title/angle. Keeping it generic and
    descriptive (rather than literally the Arabic script) tends to produce
    better results from general-purpose image models.
    """
    return f"vertical social media cover image, {idea.title}, {idea.angle}, vibrant, high quality, no text"


def generate_content_piece(
    db: Session,
    idea: ContentIdea,
    with_audio: bool = True,
    with_image: bool = True,
    with_video: bool = True,
) -> ContentPiece:
    slug = _safe_slug(idea.title)
    uid = uuid.uuid4().hex[:8]

    audio_path = ""
    image_path = ""
    video_path = ""

    if with_audio and idea.script:
        logger.info(f"[pipeline] generating voiceover for idea #{idea.id}")
        audio_path = generate_voiceover(idea.script, filename=f"{slug}-{uid}.mp3")

    if with_image:
        logger.info(f"[pipeline] generating cover image for idea #{idea.id}")
        image_path = generate_image(_image_prompt_from_idea(idea), filename=f"{slug}-{uid}.png")

    if with_video and audio_path and image_path:
        logger.info(f"[pipeline] assembling video for idea #{idea.id}")
        video_path = assemble_video(
            image_path=image_path,
            audio_path=audio_path,
            filename=f"{slug}-{uid}.mp4",
            caption_text=idea.caption,
        )
    elif with_video:
        logger.warning(
            f"[pipeline] skipping video assembly for idea #{idea.id} — "
            f"needs both audio and image (audio={bool(audio_path)}, image={bool(image_path)})"
        )

    piece = ContentPiece(
        idea_id=idea.id,
        audio_path=audio_path,
        image_path=image_path,
        video_path=video_path,
    )
    db.add(piece)
    db.commit()
    db.refresh(piece)
    return piece
