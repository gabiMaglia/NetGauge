# tests/test_window_geometry.py
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from src.presentation.qt.geometry import available_screen_rects, clamp_to_screens

PRIMARY = (0, 0, 1920, 1040)
SECOND = (1920, 0, 1920, 1040)


def test_dentro_de_pantalla_no_cambia():
    r = (100, 100, 786, 720)
    assert clamp_to_screens(r, [PRIMARY]) == r


def test_en_el_segundo_monitor_no_cambia():
    r = (2000, 50, 786, 720)
    assert clamp_to_screens(r, [PRIMARY, SECOND]) == r


def test_monitor_desconectado_centra_en_primaria():
    r = (2000, 50, 786, 720)           # vivía en el 2º monitor, ya no está
    x, y, w, h = clamp_to_screens(r, [PRIMARY])
    assert (w, h) == (786, 720)
    assert x == (1920 - 786) // 2 and y == (1040 - 720) // 2


def test_asomada_por_la_derecha_pero_alcanzable_no_cambia():
    r = (1920 - 200, 100, 786, 720)    # 200 px visibles
    assert clamp_to_screens(r, [PRIMARY]) == r


def test_casi_toda_fuera_por_la_izquierda_se_recentra():
    r = (-760, 100, 786, 720)          # solo 26 px visibles
    assert clamp_to_screens(r, [PRIMARY])[0] >= 0


def test_barra_de_titulo_fuera_por_arriba_se_recentra():
    r = (100, -300, 786, 720)
    assert clamp_to_screens(r, [PRIMARY])[1] >= 0


def test_barra_de_titulo_fuera_por_abajo_se_recentra():
    r = (100, 1030, 786, 720)
    assert clamp_to_screens(r, [PRIMARY])[1] < 1040 - 40


def test_mas_grande_que_la_pantalla_se_achica():
    x, y, w, h = clamp_to_screens((5000, 5000, 3000, 2000), [PRIMARY])
    assert w <= 1920 and h <= 1040
    assert 0 <= x and 0 <= y and x + w <= 1920 and y + h <= 1040


def test_sin_pantallas_devuelve_el_rect_original():
    r = (5, 5, 500, 500)
    assert clamp_to_screens(r, []) == r


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    yield QApplication.instance() or QApplication([])


def test_available_screen_rects_devuelve_tuplas_validas(qapp):
    rects = available_screen_rects()
    assert rects and all(len(r) == 4 and r[2] > 0 and r[3] > 0 for r in rects)
