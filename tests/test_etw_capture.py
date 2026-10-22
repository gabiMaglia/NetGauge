"""Resiliencia de la captura ETW (plan 03) con sesiones falsas: sin admin ni pywintrace."""
from __future__ import annotations

import sys
import threading

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="ETW es solo Windows")

if sys.platform == "win32":
    from src.infrastructure.capture.etw_capture import EtwCaptureService


class _FakeSession:
    """Doble de la sesión pywintrace: start() bloquea hasta stop() o falla."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.stopped = threading.Event()

    def start(self) -> None:
        if self.fail:
            raise RuntimeError("StartTrace falló")
        self.stopped.wait(5)

    def stop(self) -> None:
        self.stopped.set()


def test_etw_session_failure_sets_failed_and_calls_on_failure(monkeypatch):
    svc = EtwCaptureService()
    monkeypatch.setattr(svc, "_build_session", lambda: _FakeSession(fail=True))
    fired = threading.Event()
    svc.on_failure = fired.set
    svc.start(lambda sample: None)
    try:
        assert fired.wait(2), "la falla del hilo ETW no se notificó"
        assert svc.failed is True
    finally:
        svc.stop()


def test_etw_on_event_swallows_on_sample_errors(monkeypatch):
    svc = EtwCaptureService()
    monkeypatch.setattr(svc, "_resolve_name", lambda pid: "App")

    def boom(sample):
        raise RuntimeError("UI caída")

    svc._on_sample = boom
    svc._on_event((10, {"PID": 4, "size": 100}))   # no debe propagar a pywintrace


def test_etw_stop_joins_thread_and_clears_callback(monkeypatch):
    svc = EtwCaptureService()
    session = _FakeSession()
    monkeypatch.setattr(svc, "_build_session", lambda: session)
    svc.start(lambda sample: None)
    thread = svc._thread
    svc.stop()
    assert session.stopped.is_set()
    assert thread is not None and not thread.is_alive()
    assert svc._thread is None and svc._on_sample is None


def test_factory_wraps_etw_with_psutil_fallback(monkeypatch):
    import src.infrastructure.capture.factory as factory_mod
    from src.infrastructure.capture.fallback import FallbackCaptureService

    monkeypatch.setattr(factory_mod.sys, "platform", "win32")
    monkeypatch.setattr(factory_mod, "_is_admin", lambda: True)
    monkeypatch.setattr(EtwCaptureService, "_build_session",
                        lambda self: _FakeSession())
    service, per_process = factory_mod.create_capture_service()
    assert isinstance(service, FallbackCaptureService)
    assert isinstance(service.primary, EtwCaptureService)
    assert per_process is True
