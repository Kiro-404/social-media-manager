import numpy as np
from PIL import Image

from app.content.image_utils import cover_crop, shape_arabic


def test_cover_crop_returns_exact_size_for_wide_and_tall_inputs(tmp_path):
    for name, size in {"wide": (2000, 500), "tall": (300, 3000), "square": (800, 800)}.items():
        path = tmp_path / f"{name}.png"
        Image.new("RGB", size, (200, 10, 10)).save(path)
        frame = cover_crop(str(path), (1080, 1920))
        assert frame.shape == (1920, 1080, 3)
        assert frame.dtype == np.uint8


def test_cover_crop_handles_rgba_and_palette(tmp_path):
    path = tmp_path / "a.png"
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(path)
    assert cover_crop(str(path), (54, 96)).shape == (96, 54, 3)


def test_shape_arabic_never_fails_without_optional_libs():
    assert isinstance(shape_arabic("مرحبا بك\nسطر ثان"), str)
