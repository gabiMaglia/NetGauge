"""Ícono de cada app: el real del SO si hay ruta, o un chip de color estable con la inicial."""
from __future__ import annotations

import plistlib
import sys
import zlib
from pathlib import Path
from pathlib import PurePosixPath

from PySide6.QtCore import QFileInfo, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QFileIconProvider

# 8 tonos fijos del diseño; el tema no los cambia (son identidad de la app, no UI).
PALETTE = ("#458bf8", "#34d5a3", "#f5b942", "#f0716b",
           "#a78bfa", "#f27ab8", "#2cc4d8", "#f59a4a")
_CHIP_INK = "#0b0f17"
_DPR = 2  # nitidez en pantallas HiDPI
_cache: dict[tuple[str, str | None, int], QPixmap] = {}
_provider: QFileIconProvider | None = None


def chip_color(app_name: str) -> str:
    # crc32 y no hash(): hash() de str varía entre ejecuciones y el color debe ser estable.
    return PALETTE[zlib.crc32(app_name.encode("utf-8")) % len(PALETTE)]


def _chip(app_name: str, size: int) -> QPixmap:
    pm = QPixmap(size * _DPR, size * _DPR)
    pm.setDevicePixelRatio(_DPR)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    radius = size / 4  # 11 px para 44
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.fillPath(path, QColor(chip_color(app_name)))
    font = QFont()
    font.setPixelSize(round(size * 0.42))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor(_CHIP_INK))
    letter = (app_name.strip()[:1] or "?").upper()
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
    p.end()
    return pm


def _icon_source(exe_path: str) -> str | None:
    """Ruta de la que sale el ícono. En macOS el proceso es el binario suelto dentro del
    bundle (o un ejecutable sin bundle): para el binario Qt devuelve el ícono genérico
    "exec", así que se usa el .app más externo (el de la app, no el de sus helpers) y,
    si no hay bundle, nada (cae al chip con la inicial)."""
    if sys.platform != "darwin":
        return exe_path
    parts = PurePosixPath(exe_path).parts
    for i, part in enumerate(parts):
        if part.endswith(".app"):
            return str(PurePosixPath(*parts[: i + 1]))
    return None


def _bundle_icns(bundle: str) -> str | None:
    """Ruta del .icns de un .app según su Info.plist. QFileIconProvider devuelve una
    carpeta genérica para los bundles, así que el ícono real se lee del archivo."""
    try:
        with open(Path(bundle, "Contents", "Info.plist"), "rb") as fh:
            name = plistlib.load(fh).get("CFBundleIconFile")
    except (OSError, plistlib.InvalidFileException, ValueError):
        return None
    if not name:
        return None
    if not name.lower().endswith(".icns"):
        name += ".icns"
    path = Path(bundle, "Contents", "Resources", name)
    return str(path) if path.is_file() else None


def _system_icon(exe_path: str, size: int) -> QPixmap | None:
    global _provider
    source = _icon_source(exe_path)
    if source is None:
        return None
    if source.endswith(".app"):
        icns = _bundle_icns(source)
        if icns is None:
            return None
        pm = QIcon(icns).pixmap(size * _DPR, size * _DPR)
        if pm.isNull():
            return None
        pm.setDevicePixelRatio(_DPR)
        return pm
    info = QFileInfo(source)
    if not info.exists():
        return None
    if _provider is None:
        _provider = QFileIconProvider()
    icon = _provider.icon(info)
    if icon.isNull():
        return None
    pm = icon.pixmap(size * _DPR, size * _DPR)
    if pm.isNull():
        return None
    pm.setDevicePixelRatio(_DPR)
    return pm


def icon_for(app_name: str, exe_path: str | None, size: int = 44) -> QPixmap:
    """Pixmap no nulo para la app; cacheado por (nombre, ruta, tamaño)."""
    key = (app_name, exe_path, size)
    pm = _cache.get(key)
    if pm is None:
        real = _system_icon(exe_path, size) if exe_path else None
        pm = real if real is not None else _chip(app_name, size)
        _cache[key] = pm
    return pm


def clear_cache() -> None:
    """Libera pixmaps y proveedor. Debe correr ANTES de que muera la QApplication:
    destruir un QPixmap en el cierre del intérprete (sin app) puede abortar el proceso."""
    global _provider
    _cache.clear()
    _provider = None
