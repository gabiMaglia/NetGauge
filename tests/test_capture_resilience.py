"""Resiliencia de los backends de captura (plan 03): los loops sobreviven a
errores por iteración y la captura nativa degrada a psutil si muere."""
from __future__ import annotations

import threading
from types import SimpleNamespace


def test_psutil_loop_survives_on_sample_error(monkeypatch):
    import src.infrastructure.capture.psutil_fallback as mod

    counters = {"n": 0}

    def fake_counters():
        counters["n"] += 100
        return SimpleNamespace(bytes_sent=counters["n"], bytes_recv=counters["n"])

    monkeypatch.setattr(mod.psutil, "net_io_counters", fake_counters)
    calls = []
    second = threading.Event()

    def on_sample(sample):
        calls.append(sample)
        if len(calls) == 1:
            raise RuntimeError("UI caída")
        second.set()

    svc = mod.PsutilCaptureService(interval=0.01)
    svc.start(on_sample)
    try:
        assert second.wait(2), "el loop murió tras el primer error"
    finally:
        svc.stop()
    assert calls[1].bytes_sent == 100   # delta normal, sin re-contar el fallido
