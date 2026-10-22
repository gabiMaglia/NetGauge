"""Resuelve el nombre 'amigable' de una app desde su ejecutable (Windows).

Lee el campo FileDescription de los metadatos de versión del .exe vía ctypes
(version.dll). Si no existe, cae al nombre del archivo sin extensión.
Cachea por PID (validado con create_time: un PID reciclado NO hereda el nombre
anterior) y por ruta. Ambos caches están acotados y protegidos por un lock:
los usan en paralelo el hilo de ETW y el worker del snapshot.
"""
from __future__ import annotations

import ctypes
import struct
import threading
import time
from collections import OrderedDict
from ctypes import wintypes

import psutil

_MAX_PIDS = 4096
_MAX_PATHS = 2048
# Cada cuánto se re-verifica que un PID cacheado siga siendo el MISMO proceso
# (create_time). Entre verificaciones el hit es O(1) y sin syscalls: el
# callback de ETW llama a friendly_name() por cada evento de red.
_REVALIDATE_S = 5.0

_lock = threading.Lock()
# pid -> (create_time, nombre, instante monotónico de la última verificación)
_pid_cache: "OrderedDict[int, tuple[float, str, float]]" = OrderedDict()
_path_cache: "OrderedDict[str, str]" = OrderedDict()
_now = time.monotonic


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


def _remember(cache: OrderedDict, key, value, limit: int) -> None:
    """Inserta como más reciente y descarta los más viejos (LRU). Llamar con _lock."""
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > limit:
        cache.popitem(last=False)


def _from_path(path: str) -> str:
    with _lock:
        hit = _path_cache.get(path)
        if hit is not None:
            _path_cache.move_to_end(path)
            return hit
    desc = _file_description(path)   # IO de disco FUERA del lock
    if not desc:
        # Fallback: nombre del archivo sin extensión.
        base = path.replace("\\", "/").rsplit("/", 1)[-1]
        desc = base[:-4] if base.lower().endswith(".exe") else base
    with _lock:
        _remember(_path_cache, path, desc, _MAX_PATHS)
    return desc


def friendly_name(pid: int) -> str:
    """Nombre amigable de la app dueña del PID; fallback al nombre del proceso."""
    now = _now()
    with _lock:
        hit = _pid_cache.get(pid)
        if hit is not None and now - hit[2] < _REVALIDATE_S:
            _pid_cache.move_to_end(pid)
            return hit[1]
    try:
        proc = psutil.Process(pid)
        created = proc.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
        # Proceso muerto/inaccesible: fallback SIN cachear. El PID se recicla
        # y el próximo dueño no debe heredar "PID n".
        with _lock:
            _pid_cache.pop(pid, None)
        return f"PID {pid}"
    if hit is not None and hit[0] == created:
        name = hit[1]   # mismo proceso: sólo se renueva la verificación
    else:
        try:
            name = _from_path(proc.exe())
        except (psutil.AccessDenied, psutil.NoSuchProcess, FileNotFoundError, OSError):
            try:
                name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                return f"PID {pid}"
    with _lock:
        _remember(_pid_cache, pid, (created, name, now), _MAX_PIDS)
    return name


def _reset_caches() -> None:
    """Sólo para tests: vacía ambos caches."""
    with _lock:
        _pid_cache.clear()
        _path_cache.clear()
