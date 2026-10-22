# tests/test_qt_notifier.py
"""QtNotifier: el toast de update abre la release al hacer clic (offscreen)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from src.presentation.qt import app as app_mod

URL = "https://github.com/gabiMaglia/NetGauge/releases/tag/v2.0.2"


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


class _Sig:
    def __init__(self):
        self.slots = []

    def connect(self, f):
        self.slots.append(f)


class _FakeTray:
    def __init__(self):
        self.messageClicked = _Sig()
        self.shown = []

    def showMessage(self, *a):
        self.shown.append(a)


@pytest.fixture
def opened(monkeypatch):
    got = []
    monkeypatch.setattr(app_mod, "QDesktopServices",
                        SimpleNamespace(openUrl=lambda u: got.append(u.toString())))
    return got


def _notifier(qapp):
    n = app_mod.QtNotifier()
    tray = _FakeTray()
    n.bind_tray(tray)
    return n, tray


def test_clic_en_toast_de_update_abre_la_release(qapp, opened):
    n, tray = _notifier(qapp)
    n.notify_link("Hay una versión nueva", "NetGauge 2.0.2", URL)
    assert len(tray.shown) == 1
    tray.messageClicked.slots[0]()
    assert opened == [URL]


def test_clic_abre_una_sola_vez(qapp, opened):
    n, tray = _notifier(qapp)
    n.notify_link("t", "m", URL)
    tray.messageClicked.slots[0]()
    tray.messageClicked.slots[0]()
    assert opened == [URL]


def test_notify_comun_no_abre_nada(qapp, opened):
    n, tray = _notifier(qapp)
    n.notify_link("t", "m", URL)
    n.notify("Cuota", "superaste el límite")   # pisa el link anterior
    tray.messageClicked.slots[0]()
    assert opened == []


def test_url_no_https_se_ignora(qapp, opened):
    n, tray = _notifier(qapp)
    n.notify_link("t", "m", "file:///C:/Windows/System32/calc.exe")
    tray.messageClicked.slots[0]()
    assert opened == []


def test_intervalo_de_chequeo_es_24h():
    assert app_mod._UPDATE_CHECK_MS == 24 * 60 * 60 * 1000
