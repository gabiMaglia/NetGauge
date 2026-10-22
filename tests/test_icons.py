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


def test_unknown_icon_raises(qapp):
    with pytest.raises(KeyError):
        icons.svg_icon("nope", "#fff")
