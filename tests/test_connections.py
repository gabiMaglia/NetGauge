"""PsutilConnectionProvider.exe_paths (plan 04): el nombre visible
(FileDescription) es spoofeable, así que se devuelven TODAS las rutas."""
from __future__ import annotations

from types import SimpleNamespace

from src.infrastructure.capture import connections as cx

REAL = "C:/Program Files/Google/Chrome/chrome.exe"
FAKE = "C:/Users/x/AppData/Local/Temp/chrome.exe"


def test_exe_paths_keeps_every_path_per_name(monkeypatch):
    procs = [
        SimpleNamespace(info={"pid": 1, "exe": REAL}),
        SimpleNamespace(info={"pid": 2, "exe": FAKE}),
        SimpleNamespace(info={"pid": 3, "exe": REAL}),     # duplicado
        SimpleNamespace(info={"pid": 4, "exe": None}),     # sin ruta: se ignora
        SimpleNamespace(info={"pid": 5, "exe": "C:/w/notepad.exe"}),
    ]
    names = {1: "Google Chrome", 2: "Google Chrome", 3: "Google Chrome",
             4: "System", 5: "Notepad"}
    monkeypatch.setattr(cx.psutil, "process_iter", lambda attrs: iter(procs))
    monkeypatch.setattr(cx, "friendly_name", lambda pid: names[pid])
    out = cx.PsutilConnectionProvider().exe_paths()
    assert out == {"Google Chrome": frozenset({REAL, FAKE}),
                   "Notepad": frozenset({"C:/w/notepad.exe"})}
