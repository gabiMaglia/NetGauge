"""Íconos de app: ícono real del SO o chip de color estable con la inicial; offscreen."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.presentation.qt import app_icons  # noqa: E402
from src.presentation.qt.app_icons import chip_color, icon_for  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_icon_for_without_path_is_non_null_chip(qapp):
    pm = icon_for("Foo", None)
    assert not pm.isNull()
    assert pm.width() >= 44


def test_icon_for_with_real_path_is_non_null(qapp):
    assert not icon_for("Python", sys.executable).isNull()


def test_chip_color_is_deterministic_and_from_palette(qapp):
    assert chip_color("Foo") == chip_color("Foo")
    assert chip_color("Foo") in app_icons.PALETTE
    assert len(app_icons.PALETTE) == 8
    # Con 30 nombres distintos se usa más de un tono.
    assert len({chip_color(f"app{i}") for i in range(30)}) > 1


def test_chip_pixmap_uses_the_stable_color(qapp):
    img = icon_for("Foo", None).toImage()
    px = img.pixelColor(img.width() // 2, 3)  # borde superior, lejos de la inicial
    assert px.name() == chip_color("Foo")


def test_missing_path_falls_back_to_chip_without_raising(qapp):
    pm = icon_for("Foo", "/ruta/que/no/existe")
    assert not pm.isNull()
    assert pm.toImage() == icon_for("Foo", None).toImage()


def test_icon_for_is_cached_by_name_and_path(qapp):
    assert icon_for("Cache", None) is icon_for("Cache", None)
    assert icon_for("Cache", None) is not icon_for("Cache2", None)


def test_clear_cache_empties_pixmaps_and_provider(qapp):
    from src.presentation.qt import app_icons
    app_icons.icon_for("Chrome", None, 20)
    assert app_icons._cache
    app_icons.clear_cache()
    assert not app_icons._cache and app_icons._provider is None
    assert not app_icons.icon_for("Chrome", None, 20).isNull()   # se repuebla
