"""
Pillow/numpy helpers for the video stage.

Why this exists: moviepy 1.0.3's ``ImageClip.resize`` calls ``PIL.Image.ANTIALIAS``,
which Pillow >= 10 removed, so ``resize`` raises AttributeError. We do the
scaling ourselves with Pillow and hand moviepy a ready-made frame.
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def cover_crop(image_path: str, size: tuple[int, int]) -> np.ndarray:
    """Scale to fully cover ``size`` (width, height), then centre-crop. Returns an RGB array."""
    target_w, target_h = size
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        scale = max(target_w / img.width, target_h / img.height)
        new_w, new_h = max(round(img.width * scale), target_w), max(round(img.height * scale), target_h)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left, top = (new_w - target_w) // 2, (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
        return np.array(img)


def shape_arabic(text: str) -> str:
    """
    ImageMagick (used by moviepy's TextClip) does not join Arabic letters or
    reorder RTL text. If ``arabic-reshaper`` and ``python-bidi`` are installed,
    pre-shape the text so it renders correctly; otherwise return it unchanged.
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return text
    return "\n".join(get_display(arabic_reshaper.reshape(line)) for line in text.split("\n"))
