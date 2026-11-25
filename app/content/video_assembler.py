"""
Assembles a still image + a voiceover track (+ optional background music)
into a vertical Reels/Shorts/TikTok-ready video, with a simple animated
caption overlay. Built entirely on ffmpeg (via moviepy) — no paid service,
no cloud rendering.
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
)

from app.config import settings
from app.content.image_utils import cover_crop, shape_arabic

VERTICAL_SIZE = (1080, 1920)


def _wrap_caption(text: str, max_chars_per_line: int = 28) -> str:
    """Naive word-wrap so captions don't run off the vertical frame."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars_per_line:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def assemble_video(
    image_path: str,
    audio_path: str,
    filename: str,
    caption_text: str = "",
    music_path: str | None = None,
    music_volume: float = 0.12,
) -> str:
    """
    Combine a background image, a voiceover, optional music, and an optional
    caption overlay into one vertical MP4. Duration follows the voiceover
    track. Returns the relative path to the written file.
    """
    out_path = settings.media_path / "videos" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    voice_clip = AudioFileClip(audio_path)
    duration = voice_clip.duration

    # Pillow does the scaling/cropping (moviepy 1.0.3's resize breaks on Pillow >= 10).
    image_clip = ImageClip(cover_crop(image_path, VERTICAL_SIZE)).set_duration(duration)

    layers = [image_clip]

    if caption_text:
        try:
            wrapped = shape_arabic(_wrap_caption(caption_text))
            text_clip = (
                TextClip(
                    wrapped,
                    fontsize=54,
                    color="white",
                    font=settings.caption_font,
                    method="caption",
                    size=(int(VERTICAL_SIZE[0] * 0.85), None),
                    stroke_color="black",
                    stroke_width=2,
                    align="center",
                )
                .set_position(("center", "bottom"))
                .set_duration(duration)
                .margin(bottom=140, opacity=0)
            )
            layers.append(text_clip)
        except Exception as exc:
            # TextClip needs ImageMagick; degrade gracefully to image+audio only
            # rather than failing the whole pipeline over a missing system dep.
            logger.warning(
                f"[video_assembler] caption overlay skipped (ImageMagick likely missing): {exc}"
            )

    video = CompositeVideoClip(layers, size=VERTICAL_SIZE).set_duration(duration)

    if music_path and Path(music_path).exists():
        music_clip = AudioFileClip(music_path).volumex(music_volume)
        if music_clip.duration < duration:
            loops_needed = int(duration // music_clip.duration) + 1
            music_clip = CompositeAudioClip([music_clip] * loops_needed).set_duration(duration)
        else:
            music_clip = music_clip.subclip(0, duration)
        final_audio = CompositeAudioClip([voice_clip, music_clip])
    else:
        final_audio = voice_clip

    video = video.set_audio(final_audio)
    video.write_videofile(
        str(out_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,
    )

    voice_clip.close()
    video.close()
    if "music_clip" in locals():
        music_clip.close()

    return str(out_path)
