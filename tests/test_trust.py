"""Tests de seguridad de `trust.py`: límites de ruta y prototipos ctypes."""
from __future__ import annotations

import sys

import pytest

from src.infrastructure.capture import trust

win_only = pytest.mark.skipif(sys.platform != "win32", reason="ctypes/crypt32 solo en Windows")


# --- límites de ruta ---------------------------------------------------------

def test_is_under_requiere_separador():
    assert trust._is_under("C:\\Windows\\System32\\x.exe", "c:\\windows")
    assert trust._is_under("c:/windows/system32/x.exe", "C:\\Windows")  # / y mayúsculas
    assert trust._is_under("C:\\Windows", "c:\\windows\\")               # igual a la raíz
    assert not trust._is_under("C:\\Windows.old\\x.exe", "c:\\windows")
    assert not trust._is_under("C:\\Program Files-evil\\x.exe", "c:\\program files")
    assert not trust._is_under("C:\\Windowsx\\x.exe", "c:\\windows")


def test_location_ok_no_confia_en_prefijos_hermanos(monkeypatch):
    monkeypatch.setenv("ProgramFiles", "C:\\Program Files")
    monkeypatch.setenv("ProgramFiles(x86)", "C:\\Program Files (x86)")
    monkeypatch.setenv("SystemRoot", "C:\\Windows")
    assert trust._location_ok("C:\\Program Files\\App\\a.exe") == (True, False)
    assert trust._location_ok("C:\\Windows\\System32\\a.exe") == (True, False)
    assert trust._location_ok("C:\\Windows.old\\a.exe") == (False, False)
    assert trust._location_ok("C:\\Program Files-evil\\a.exe") == (False, False)
    assert trust._location_ok("C:\\Users\\x\\Downloads\\a.exe") == (False, True)
