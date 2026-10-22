# tests/test_widgets_plaintext.py
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.presentation.qt.theme import DARK
from src.presentation.qt.widgets import AppRow, ConnRow


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_approw_nombre_en_texto_plano(qapp):
    row = AppRow(DARK, "<img src=x onerror=1>")
    assert row._nm.textFormat() == Qt.TextFormat.PlainText
    assert row._nm.text() == "<img src=x onerror=1>"


def test_connrow_nombre_y_geo_en_texto_plano(qapp):
    row = ConnRow("<b>evil</b>", "8.8.8.8:443", "ESTABLISHED")
    assert row._app.textFormat() == Qt.TextFormat.PlainText
    assert row._geo.textFormat() == Qt.TextFormat.PlainText
    row.set_geo("<a href='http://x'>US</a>")
    assert row._geo.text() == "<a href='http://x'>US</a>"
