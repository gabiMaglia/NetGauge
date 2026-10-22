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


class FakeBackend:
    def __init__(self, fail_on_start: bool = False) -> None:
        self.on_failure = None
        self.fail_on_start = fail_on_start
        self.started_with = None
        self.stopped = 0

    def start(self, on_sample):
        if self.fail_on_start:
            raise RuntimeError("sin sesión")
        self.started_with = on_sample

    def stop(self):
        self.stopped += 1


def _wrap(primary):
    from src.infrastructure.capture.fallback import FallbackCaptureService

    made = []

    def make_fallback():
        made.append(FakeBackend())
        return made[-1]

    return FallbackCaptureService(primary, make_fallback), made


def test_fallback_switches_once_when_primary_fails():
    primary = FakeBackend()
    svc, made = _wrap(primary)
    cb = lambda sample: None
    svc.start(cb)
    assert svc.degraded is False
    primary.on_failure()                # el hilo nativo murió
    primary.on_failure()                # un segundo aviso no duplica
    assert svc.degraded is True and len(made) == 1
    assert made[0].started_with is cb and primary.stopped == 1
    svc.stop()
    assert made[0].stopped == 1


def test_fallback_when_primary_start_raises():
    svc, made = _wrap(FakeBackend(fail_on_start=True))
    svc.start(lambda sample: None)
    assert svc.degraded is True and len(made) == 1


def test_failure_after_stop_is_ignored():
    primary = FakeBackend()
    svc, made = _wrap(primary)
    svc.start(lambda sample: None)
    svc.stop()
    primary.on_failure()
    assert made == [] and svc.degraded is False
