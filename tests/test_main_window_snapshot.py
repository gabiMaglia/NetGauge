"""Smoke test (plan 04): MainWindow._refresh corre en el hilo GUI y NO debe
hacer IO (SQLite, psutil, evaluación de firma). Todo eso es del worker."""
from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32",
                                reason="widgets Qt reales: sólo en Windows")

from PySide6.QtWidgets import QApplication  # noqa: E402

from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from src.domain.models import Settings, TrafficSample  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402


class _NoIoRepo(FakeRepo):
    def __init__(self) -> None:
        super().__init__()
        self.queries = 0

    def totals_by_app(self, start, end):
        self.queries += 1
        return []


class _ExplodingEvaluator:
    def evaluate(self, path):
        raise AssertionError("evaluate() en el hilo GUI")


class _ExplodingProvider:
    def exe_paths(self):
        raise AssertionError("process_iter en el hilo GUI")

    def connections(self):
        raise AssertionError("net_connections en el hilo GUI")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_refresh_does_no_io_on_gui_thread(qapp):
    repo = _NoIoRepo()
    m = MonitorService(FakeCapture(), repo, FakeReporter(), FakeStore(Settings()),
                       FakeNotifier(), trust_evaluator=_ExplodingEvaluator(),
                       connection_provider=_ExplodingProvider())
    m._on_sample(TrafficSample(1, "Chrome", bytes_sent=10, bytes_recv=20))
    w = MainWindow(m, per_process=True)
    try:
        for period in ("session", "day", "week", "month"):
            w._set_period(period)
        w._tabs.setCurrentIndex(2)      # pestaña de conexiones visible
        w._refresh()
        assert repo.queries == 0
        assert m._refresher._on_refreshed is not None   # listener enganchado
    finally:
        w._timer.stop()
        m.set_snapshot_listener(None)
        w.deleteLater()


def test_period_change_keeps_frame_until_snapshot_arrives(qapp):
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    m._on_sample(TrafficSample(1, "Chrome", bytes_sent=10, bytes_recv=20))
    w = MainWindow(m, per_process=True)
    try:
        w._set_period("session")
        assert "Chrome" in w._app_rows
        w._set_period("week")           # snapshot de 'week' aún no calculado
        assert "Chrome" in w._app_rows  # no se vacía el frame
    finally:
        w._timer.stop()
        m.set_snapshot_listener(None)
        w.deleteLater()


class _Info:
    level = "suspicious"
    signer = "<b>Evil</b> & Co"
    reasons = ["trust.signed_by"]
    vt_malicious = None
    vt_total = None


def test_trust_tooltip_escapa_html():
    from src.presentation.qt.main_window import trust_tooltip_text
    txt = trust_tooltip_text(_Info(), lambda k, **kw: kw.get("signer", k))
    assert "<b>" not in txt
    assert "&lt;b&gt;Evil&lt;/b&gt; &amp; Co" in txt


def test_tick_does_not_refresh_data(qapp, monkeypatch):
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    w = MainWindow(m, per_process=True)
    try:
        calls: list[int] = []
        monkeypatch.setattr(w, "_refresh", lambda: calls.append(1))
        for _ in range(4):
            w._tick()
        assert calls == []              # el repintado de datos lo marca el worker
    finally:
        w._timer.stop()
        m.set_snapshot_listener(None)
        w.deleteLater()
