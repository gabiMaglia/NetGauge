"""Chrome nativo de Windows para una ventana frameless de Qt.

Le devuelve a una ventana sin marco las prestaciones del SO:
  - Resize desde bordes y esquinas.
  - Aero Snap (Win+flechas, arrastrar al borde, sacudir).
  - Maximizar/minimizar con animación y respetando la barra de tareas.

Técnica estándar: se mantienen los estilos WS_THICKFRAME/WS_CAPTION en el HWND
(para que Windows gestione resize/snap) pero se intercepta WM_NCCALCSIZE para que
el área cliente ocupe toda la ventana (sin marco visible), y WM_NCHITTEST para
marcar bordes (resize) y la barra de título (arrastre/snap nativo).

Todo es best-effort y solo Windows; si algo falla, la ventana sigue funcionando
con el arrastre manual de Qt.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QAbstractButton, QComboBox, QLineEdit

IS_WIN = sys.platform == "win32"

_GWL_STYLE = -16
_WS_THICKFRAME = 0x00040000
_WS_CAPTION = 0x00C00000
_WS_MAXIMIZEBOX = 0x00010000
_WS_MINIMIZEBOX = 0x00020000
_WS_SYSMENU = 0x00080000

_WM_NCCALCSIZE = 0x0083
_WM_NCHITTEST = 0x0084

_HTCLIENT, _HTCAPTION = 1, 2
_HTLEFT, _HTRIGHT, _HTTOP = 10, 11, 12
_HTTOPLEFT, _HTTOPRIGHT = 13, 14
_HTBOTTOM, _HTBOTTOMLEFT, _HTBOTTOMRIGHT = 15, 16, 17

_SM_CXFRAME, _SM_CYFRAME, _SM_CXPADDEDBORDER = 32, 33, 92
_BORDER = 6  # grosor (px) de la zona de resize


class _RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class _NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", _RECT * 3), ("lppos", ctypes.c_void_p)]


def apply_native_chrome(window, caption_height: int = 52) -> bool:
    """Activa el chrome nativo en la ventana. Devuelve True si pudo."""
    if not IS_WIN:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.GetWindowLongPtrW.restype = ctypes.c_longlong
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int,
                                             ctypes.c_longlong]
        hwnd = int(window.winId())
        style = user32.GetWindowLongPtrW(hwnd, _GWL_STYLE)
        style |= (_WS_THICKFRAME | _WS_CAPTION | _WS_MAXIMIZEBOX
                  | _WS_MINIMIZEBOX | _WS_SYSMENU)
        user32.SetWindowLongPtrW(hwnd, _GWL_STYLE, style)
        # SWP_FRAMECHANGED|NOMOVE|NOSIZE|NOZORDER|NOACTIVATE
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0037)
        window._native_caption_h = caption_height
        return True
    except Exception:  # noqa: BLE001
        return False


def handle_native_event(window, message):
    """Procesa WM_NCCALCSIZE / WM_NCHITTEST. Devuelve (True, code) o None."""
    if not IS_WIN:
        return None
    try:
        msg = wintypes.MSG.from_address(int(message))
    except Exception:  # noqa: BLE001
        return None

    if msg.message == _WM_NCCALCSIZE and msg.wParam:
        user32 = ctypes.windll.user32
        if user32.IsZoomed(int(window.winId())):
            # Maximizada: insetar por el marco para no cortar contra el monitor.
            cx = (user32.GetSystemMetrics(_SM_CXFRAME)
                  + user32.GetSystemMetrics(_SM_CXPADDEDBORDER))
            cy = (user32.GetSystemMetrics(_SM_CYFRAME)
                  + user32.GetSystemMetrics(_SM_CXPADDEDBORDER))
            params = _NCCALCSIZE_PARAMS.from_address(msg.lParam)
            params.rgrc[0].left += cx
            params.rgrc[0].top += cy
            params.rgrc[0].right -= cx
            params.rgrc[0].bottom -= cy
        return (True, 0)  # área cliente = toda la ventana (sin marco visible)

    if msg.message == _WM_NCHITTEST:
        return _hit_test(window, msg)
    return None


def _hit_test(window, msg):
    x = ctypes.c_short(msg.lParam & 0xFFFF).value
    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
    pt = window.mapFromGlobal(QPoint(x, y))
    lx, ly = pt.x(), pt.y()
    w, h = window.width(), window.height()
    b = _BORDER
    maximized = window.isMaximized()

    if not maximized:
        left, right = lx < b, lx >= w - b
        top, bottom = ly < b, ly >= h - b
        if top and left:
            return (True, _HTTOPLEFT)
        if top and right:
            return (True, _HTTOPRIGHT)
        if bottom and left:
            return (True, _HTBOTTOMLEFT)
        if bottom and right:
            return (True, _HTBOTTOMRIGHT)
        if left:
            return (True, _HTLEFT)
        if right:
            return (True, _HTRIGHT)
        if top:
            return (True, _HTTOP)
        if bottom:
            return (True, _HTBOTTOM)

    child = window.childAt(pt)
    if isinstance(child, (QAbstractButton, QComboBox, QLineEdit)):
        return (True, _HTCLIENT)  # botones/inputs reciben el click normal
    cap = getattr(window, "_native_caption_h", 52)
    if ly <= cap:
        return (True, _HTCAPTION)  # barra de título: arrastre/snap nativo
    return (True, _HTCLIENT)
