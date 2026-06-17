"""Resuelve el nombre 'amigable' de una app desde su ejecutable (Windows).

Lee el campo FileDescription de los metadatos de versión del .exe vía ctypes
(version.dll). Si no existe, cae al nombre del archivo sin extensión.
Cachea por PID y por ruta para no repetir la consulta.
"""
from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes

import psutil

_pid_cache: dict[int, str] = {}
_path_cache: dict[str, str] = {}


def _file_description(path: str) -> str | None:
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        ctypes.windll.version.GetFileVersionInfoW(path, 0, size, buf)

        ptr = ctypes.c_void_p()
        length = wintypes.UINT()
        if not ctypes.windll.version.VerQueryValueW(
            buf, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(length)
        ) or not length.value:
            return None
        lang, codepage = struct.unpack("HH", ctypes.string_at(ptr.value, 4))
        sub = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileDescription"

        if not ctypes.windll.version.VerQueryValueW(
            buf, sub, ctypes.byref(ptr), ctypes.byref(length)
        ) or not length.value:
            return None
        desc = ctypes.wstring_at(ptr.value, length.value).strip("\x00 ").strip()
        return desc or None
    except Exception:  # noqa: BLE001
        return None


def _from_path(path: str) -> str:
    if path in _path_cache:
        return _path_cache[path]
    desc = _file_description(path)
    if not desc:
        # Fallback: nombre del archivo sin extensión.
        base = path.replace("\\", "/").rsplit("/", 1)[-1]
        desc = base[:-4] if base.lower().endswith(".exe") else base
    _path_cache[path] = desc
    return desc


def friendly_name(pid: int) -> str:
    """Nombre amigable de la app dueña del PID; fallback al nombre del proceso."""
    if pid in _pid_cache:
        return _pid_cache[pid]
    try:
        proc = psutil.Process(pid)
        try:
            name = _from_path(proc.exe())
        except (psutil.AccessDenied, FileNotFoundError, OSError):
            name = proc.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        name = f"PID {pid}"
    _pid_cache[pid] = name
    return name
