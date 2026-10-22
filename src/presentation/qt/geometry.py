"""Geometría de ventana: que una posición guardada nunca deje la ventana inalcanzable.

Si el usuario desconecta un monitor (o cambia la resolución), la geometría
guardada puede quedar fuera de todas las pantallas. Lógica pura, sin Qt.
"""
from __future__ import annotations

from typing import Sequence

Rect = tuple[int, int, int, int]  # x, y, ancho, alto

_MIN_VISIBLE_W = 120   # ancho horizontal mínimo de la barra de título visible
_MIN_BELOW_TOP = 40    # el borde superior debe dejar al menos esto dentro de la pantalla


def _title_bar_reachable(rect: Rect, screen: Rect) -> bool:
    x, y, w, _h = rect
    sx, sy, sw, sh = screen
    overlap_w = min(x + w, sx + sw) - max(x, sx)
    return overlap_w >= min(_MIN_VISIBLE_W, w) and sy <= y <= sy + sh - _MIN_BELOW_TOP


def clamp_to_screens(rect: Rect, screens: Sequence[Rect]) -> Rect:
    """`rect` si su barra de título es alcanzable en alguna pantalla; si no, lo
    centra en `screens[0]` (la primaria), achicándolo si no entra."""
    if not screens:
        return rect
    if any(_title_bar_reachable(rect, s) for s in screens):
        return rect
    sx, sy, sw, sh = screens[0]
    w = min(rect[2], sw)
    h = min(rect[3], sh)
    return (sx + (sw - w) // 2, sy + (sh - h) // 2, w, h)


def available_screen_rects() -> list[Rect]:
    """`availableGeometry()` de cada pantalla (excluye taskbar), primaria primero."""
    from PySide6.QtGui import QGuiApplication

    primary = QGuiApplication.primaryScreen()
    screens = sorted(QGuiApplication.screens(), key=lambda s: s is not primary)
    out: list[Rect] = []
    for s in screens:
        g = s.availableGeometry()
        out.append((g.x(), g.y(), g.width(), g.height()))
    return out
