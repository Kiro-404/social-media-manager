"""Map files saved under the media directory to the URL path they are served at."""
from __future__ import annotations

from pathlib import Path


def media_url(file_path: str, media_root: Path | str) -> str:
    """
    ``media/images/a.png`` -> ``/media/images/a.png``.
    Returns "" for empty paths or paths outside ``media_root``.
    """
    if not file_path:
        return ""
    try:
        relative = Path(file_path).resolve().relative_to(Path(media_root).resolve())
    except ValueError:
        return ""
    return "/media/" + relative.as_posix()
