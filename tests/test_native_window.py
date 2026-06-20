"""Tests del chrome nativo de Windows (T-013).

Cubre el bug reportado: en máquinas con escalado de DPI fraccional
(125%/150%/175%, frecuente en notebooks) el header quedaba sin respuesta a
los botones y sin drag/resize, mientras el resto de la app funcionaba bien.
Causa raíz: WM_NCHITTEST llega en coordenadas FÍSICAS de pantalla y se
mapeaban a lógicas sin dividir por el factor de escala real del monitor.

Estos tests no requieren un HWND real ni QApplication: `_hit_test` solo
necesita un objeto con la interfaz mínima de QWidget que usa internamente
(mapFromGlobal, width, height, isMaximized, childAt, devicePixelRatioF).
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(__file__.rsplit("tests", 1)[0]))

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QPushButton

from src.presentation.qt import native_window as nw

pytestmark = pytest.mark.skipif(not nw.IS_WIN, reason="chrome nativo es solo Windows")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_msg(x: int, y: int):
    """Empaqueta (x, y) como vendrían en lParam de WM_NCHITTEST (16 bits c/u)."""
    lparam = (y & 0xFFFF) << 16 | (x & 0xFFFF)
    return SimpleNamespace(lParam=lparam)


class _FakeWindow:
    """Doble de MainWindow con superficie mínima para _hit_test."""

    def __init__(self, width: int, height: int, ratio: float,
                 child=None, maximized: bool = False) -> None:
        self._w = width
        self._h = height
        self._ratio = ratio
        self._child = child
        self._maximized = maximized
        self._native_caption_h = 52

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h

    def isMaximized(self) -> bool:
        return self._maximized

    def devicePixelRatioF(self) -> float:
        return self._ratio

    def mapFromGlobal(self, point: QPoint) -> QPoint:
        # Doble "identity": el fake ya recibe coordenadas lógicas porque
        # _hit_test es responsable de convertir antes de llamar a esto.
        return QPoint(point.x(), point.y())

    def childAt(self, _point: QPoint):
        return self._child


def test_hit_test_caption_area_at_100_percent_scale(qapp):
    """Sanity check: a escala 1:1 (caso PO) el caption se detecta normal."""
    window = _FakeWindow(width=800, height=600, ratio=1.0)
    msg = _make_msg(x=400, y=20)  # dentro de la barra de título (<=52)
    assert nw._hit_test(window, msg) == (True, nw._HTCAPTION)


def test_hit_test_button_click_at_100_percent_scale(qapp):
    btn = QPushButton()
    window = _FakeWindow(width=800, height=600, ratio=1.0, child=btn)
    msg = _make_msg(x=750, y=20)
    assert nw._hit_test(window, msg) == (True, nw._HTCLIENT)


def test_hit_test_button_click_survives_fractional_dpi_scale(qapp):
    """Reproduce el bug: notebook con escalado 150% (ratio=1.5).

    WM_NCHITTEST llega en físicos (ej. x=1125 a 150% == 750 lógico, que es
    donde está el botón). Sin la conversión por devicePixelRatioF, _hit_test
    le pasaría 1125 directo a mapFromGlobal y el botón nunca se encontraría
    -> el click cae fuera del widget -> header "muerto".
    """
    btn = QPushButton()
    window = _FakeWindow(width=800, height=600, ratio=1.5, child=btn)
    msg = _make_msg(x=1125, y=30)  # físico: 750,20 lógico tras dividir por 1.5
    assert nw._hit_test(window, msg) == (True, nw._HTCLIENT)


def test_hit_test_resize_border_survives_fractional_dpi_scale(qapp):
    """Mismo bug, pero para los bordes de resize (175%, común en notebooks)."""
    window = _FakeWindow(width=800, height=600, ratio=1.75)
    # Borde derecho lógico (lx >= w - BORDER): físico = 798*1.75 ~ 1396
    msg = _make_msg(x=1396, y=525)  # y físico: 300*1.75
    result = nw._hit_test(window, msg)
    assert result[0] is True
    assert result[1] in (nw._HTRIGHT, nw._HTBOTTOMRIGHT, nw._HTBOTTOM)


def test_handle_native_event_swallows_hit_test_exceptions(monkeypatch, qapp):
    """Si _hit_test explota por cualquier motivo, no debe tirar abajo el
    procesamiento nativo de mensajes (eso dejaría el header muerto sin pista
    de qué pasó). handle_native_event debe devolver None y dejar que Windows
    siga con su comportamiento default."""
    class _BoomWindow:
        def winId(self):
            return 1

    def _boom(*_args, **_kwargs):
        raise RuntimeError("config de DPI atípica simulada")

    monkeypatch.setattr(nw, "_hit_test", _boom)
    monkeypatch.setattr(nw.ctypes, "windll", SimpleNamespace(
        user32=SimpleNamespace()))

    msg_struct = SimpleNamespace(message=nw._WM_NCHITTEST, wParam=0,
                                  lParam=_make_msg(1, 1).lParam)
    monkeypatch.setattr(
        nw.wintypes.MSG, "from_address", staticmethod(lambda _addr: msg_struct))

    result = nw.handle_native_event(_BoomWindow(), 12345)
    assert result is None
