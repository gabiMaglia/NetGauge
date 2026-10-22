"""Cache de nombres amigables por PID (plan 04).

Bug original: `_pid_cache` nunca se invalidaba -> un PID reciclado heredaba el
nombre de la app anterior; el fallback "PID n" quedaba cacheado para siempre;
crecía sin límite y sin lock (ETW + worker lo tocan en paralelo).
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

import psutil
import pytest

from src.infrastructure.capture import app_names as an

_DESCS = {"C:/a/chrome.exe": "Google Chrome", "C:/b/evil.exe": "Evil Tool"}


def _fake_psutil(table: dict):
    """table: pid -> (create_time, exe | None, name). Ausente = NoSuchProcess.
    exe None = AccessDenied al pedir la ruta (proceso protegido)."""

    class Proc:
        def __init__(self, pid):
            if pid not in table:
                raise psutil.NoSuchProcess(pid)
            self._pid = pid

        def create_time(self):
            if self._pid not in table:
                raise psutil.NoSuchProcess(self._pid)
            return table[self._pid][0]

        def exe(self):
            exe = table[self._pid][1]
            if exe is None:
                raise psutil.AccessDenied(self._pid)
            return exe

        def name(self):
            return table[self._pid][2]

    return SimpleNamespace(Process=Proc, NoSuchProcess=psutil.NoSuchProcess,
                           AccessDenied=psutil.AccessDenied)


@pytest.fixture
def env(monkeypatch):
    table: dict = {}
    clock = [1000.0]
    monkeypatch.setattr(an, "psutil", _fake_psutil(table))
    monkeypatch.setattr(an, "_file_description", lambda path: _DESCS.get(path))
    monkeypatch.setattr(an, "_now", lambda: clock[0])
    an._reset_caches()
    yield table, clock
    an._reset_caches()


def test_recycled_pid_gets_new_name(env):
    table, clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    assert an.friendly_name(42) == "Google Chrome"
    table[42] = (2.0, "C:/b/evil.exe", "evil.exe")   # mismo PID, otro proceso
    clock[0] += an._REVALIDATE_S + 1
    assert an.friendly_name(42) == "Evil Tool"


def test_hit_within_window_does_not_touch_psutil(env):
    table, _clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    assert an.friendly_name(42) == "Google Chrome"
    del table[42]   # si tocara psutil, daría NoSuchProcess
    assert an.friendly_name(42) == "Google Chrome"


def test_same_process_keeps_name_after_revalidation(env):
    table, clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    an.friendly_name(42)
    clock[0] += an._REVALIDATE_S + 1
    assert an.friendly_name(42) == "Google Chrome"
    assert an._pid_cache[42][2] == clock[0]   # verificación renovada


def test_pid_fallback_is_not_cached(env):
    table, _clock = env
    assert an.friendly_name(7) == "PID 7"
    assert 7 not in an._pid_cache
    table[7] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    assert an.friendly_name(7) == "Google Chrome"   # sin esperar ventana


def test_dead_process_evicts_entry(env):
    table, clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    an.friendly_name(42)
    del table[42]
    clock[0] += an._REVALIDATE_S + 1
    assert an.friendly_name(42) == "PID 42"
    assert 42 not in an._pid_cache


def test_access_denied_exe_falls_back_to_process_name(env):
    table, _clock = env
    table[9] = (1.0, None, "svchost.exe")
    assert an.friendly_name(9) == "svchost.exe"


def test_pid_cache_is_bounded(env, monkeypatch):
    table, _clock = env
    monkeypatch.setattr(an, "_MAX_PIDS", 3)
    for pid in range(1, 6):
        table[pid] = (1.0, "C:/a/chrome.exe", "chrome.exe")
        an.friendly_name(pid)
    assert len(an._pid_cache) == 3
    assert list(an._pid_cache) == [3, 4, 5]   # se van los más viejos (LRU)


def test_path_cache_is_bounded(env, monkeypatch):
    monkeypatch.setattr(an, "_MAX_PATHS", 2)
    for i in range(5):
        an._from_path(f"C:/x/app{i}.exe")
    assert len(an._path_cache) == 2


def test_concurrent_access_is_safe(env):
    table, clock = env
    for pid in range(200):
        table[pid] = (float(pid), "C:/a/chrome.exe", "chrome.exe")
    errors: list[BaseException] = []

    def worker(offset):
        try:
            for i in range(2000):
                an.friendly_name((i + offset) % 250)   # incluye PIDs muertos
                if i % 97 == 0:
                    clock[0] += an._REVALIDATE_S + 1
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(k * 31,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(an._pid_cache) <= an._MAX_PIDS
