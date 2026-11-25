from pathlib import Path

from app.media_utils import media_url


def test_file_inside_media_root(tmp_path: Path):
    f = tmp_path / "images" / "a.png"
    f.parent.mkdir()
    f.write_bytes(b"x")
    assert media_url(str(f), tmp_path) == "/media/images/a.png"


def test_empty_path(tmp_path: Path):
    assert media_url("", tmp_path) == ""


def test_path_outside_media_root_is_not_exposed(tmp_path: Path):
    assert media_url("/etc/passwd", tmp_path) == ""
    assert media_url(str(tmp_path / ".." / "secret.txt"), tmp_path) == ""
