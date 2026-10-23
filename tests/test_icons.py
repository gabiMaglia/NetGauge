import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.presentation.qt import icons  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_all_icons_render(qapp):
    for name in icons.NAMES:
        ic = icons.svg_icon(name, "#93a6c1", 18)
        assert not ic.pixmap(18, 18).isNull(), name


def _opaque_pixels(name: str, color: str):
    img = icons.svg_icon(name, color, 18).pixmap(18, 18).toImage()
    px = [img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())
          if img.pixelColor(x, y).alpha() > 0]
    return sorted(px, key=lambda c: -c.alpha())   # el más opaco primero


def test_icons_draw_something_in_the_requested_colour(qapp):
    for name in icons.NAMES:
        red = _opaque_pixels(name, "#ff0000")
        blue = _opaque_pixels(name, "#0000ff")
        assert red and blue, name   # al menos un píxel con alpha > 0
        assert red[0].red() > 200 and red[0].blue() < 60, name
        assert blue[0].blue() > 200 and blue[0].red() < 60, name


def test_unknown_icon_raises(qapp):
    with pytest.raises(KeyError):
        icons.svg_icon("nope", "#fff")
