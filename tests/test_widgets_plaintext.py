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


def test_plain_tooltip_is_literal_and_rich(qapp):
    from src.presentation.qt.widgets import plain_tooltip
    tip = plain_tooltip("AT&T <b>x</b>")
    assert tip.startswith("<span>")   # rich text: Qt no muestra "&amp;" literal
    assert "AT&amp;T &lt;b&gt;x&lt;/b&gt;" in tip and "<b>" not in tip


def test_geo_and_trust_tooltips_escape_remote_data(qapp):
    row = ConnRow("App", "1.2.3.4:443", "ESTABLISHED")
    row.set_geo("US", "AT&T <i>Corp</i>")
    assert "AT&amp;T &lt;i&gt;Corp&lt;/i&gt;" in row._geo.toolTip()
    assert "<i>" not in row._geo.toolTip()
    from src.domain.models import TRUST_CAUTION
    app_row = AppRow(DARK, "A&B <b>" + "x" * 300)
    app_row.set_trust(TRUST_CAUTION, "Firmado por <b>X</b> & Co")
    assert "&lt;b&gt;X&lt;/b&gt; &amp; Co" in app_row._trust.toolTip()
    app_row.resize(200, 60)
    app_row.show()
    QApplication.processEvents()
    app_row._nm.setFixedWidth(80)
    QApplication.processEvents()
    app_row._nm.grab()            # recortado -> tooltip con el nombre literal
    assert "A&amp;B &lt;b&gt;" in app_row._nm.toolTip()
