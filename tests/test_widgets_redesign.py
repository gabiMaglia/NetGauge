"""Widgets de la pestaña Global (tarjetas, gráfico con ejes/tooltip, límites); offscreen."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from src.domain.models import Settings, TrafficSample  # noqa: E402
from src.presentation.qt.i18n import set_language  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402
from src.presentation.qt.theme import DARK  # noqa: E402
from src.presentation.qt.widgets import LimitCard, LiveChart, MetricCard, nice_ticks  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_nice_ticks_rounds_to_1_2_5():
    assert nice_ticks(18.6e6) == pytest.approx([0, 5e6, 10e6, 15e6, 20e6])


def test_nice_ticks_zero_peak_uses_1kb_floor():
    ticks = nice_ticks(0)
    assert len(ticks) == 5 and ticks[0] == 0
    assert ticks == sorted(ticks) and ticks[1] >= 1024 / 4


@pytest.mark.parametrize("pct,level", [(68, "ok"), (79.9, "ok"), (80, "warn"),
                                       (99, "warn"), (100, "danger"), (140, "danger")])
def test_limit_card_levels(qapp, pct, level):
    c = LimitCard(DARK)
    c.set_state("Límite diario · hoy", "6,8 / 10 GB · 68 %", pct, True, "Te avisamos")
    assert c.level() == level


def test_limit_card_empty_state_and_define_signal(qapp):
    c = LimitCard(DARK)
    c.set_state("Límite mensual", "", 0, False, "Aún sin límite definido")
    c.show()
    assert c.level() == "empty"
    btn = c.findChild(QPushButton, "LimitDefineBtn")
    assert btn is not None and btn.isVisible()
    hits = []
    c.define_clicked.connect(lambda: hits.append(1))
    btn.click()
    assert hits == [1]


def test_limit_card_with_limit_hides_define_button_and_offers_edit(qapp):
    c = LimitCard(DARK)
    c.set_state("Límite diario · hoy", "1 / 10 GB · 10 %", 10, True, "hint")
    c.show()
    assert not c.findChild(QPushButton, "LimitDefineBtn").isVisible()
    edit = c.findChild(QPushButton, "LimitEditBtn")
    assert edit.isVisible()
    hits = []
    c.define_clicked.connect(lambda: hits.append(1))
    edit.click()
    assert hits == [1]


def test_chart_value_at_returns_last_push(qapp):
    ch = LiveChart(DARK)
    for i in range(60):
        ch.push(up=float(i), down=float(i * 2))
    assert ch.value_at(59) == (118.0, 59.0)  # (down, up)
    assert ch.value_at(0) == (0.0, 0.0)


def _move(chart: LiveChart, x: float, y: float = 40) -> None:
    ev = QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(x, y), QPointF(x, y),
                     Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                     Qt.KeyboardModifier.NoModifier)
    chart.mouseMoveEvent(ev)


def test_chart_hover_with_zero_peak_does_not_break(qapp):
    ch = LiveChart(DARK)
    ch.resize(500, 200)
    assert ch.hasMouseTracking()
    assert ch.hover_index() is None
    _move(ch, 300)
    assert ch.hover_index() is not None
    ch.grab()  # pinta con tooltip y peak == 0
    ch.leaveEvent(None)
    assert ch.hover_index() is None
    ch.grab()


def test_chart_set_window_seconds_keeps_working(qapp):
    ch = LiveChart(DARK)
    ch.resize(500, 200)
    ch.set_window_seconds(120)
    _move(ch, 200)
    ch.grab()


def test_metric_card_trend_and_spark(qapp):
    c = MetricCard(DARK, "down", "Bajada")
    c.set_values("1,2", "GB", "82 % del total", "▲ 12 % vs ayer", "up", [1, 2, 3])
    assert c.trend_text() == "▲ 12 % vs ayer"
    c.set_values("1,2", "GB", "x")
    assert c.trend_text() == ""
    c.grab()


def _window(prev):
    QApplication.instance() or QApplication([])
    set_language("es")
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    m._on_sample(TrafficSample(1, "A", bytes_sent=0, bytes_recv=1120))
    m.previous_period_total = lambda period: prev  # type: ignore[method-assign]
    return MainWindow(m, per_process=True)


def test_window_total_card_shows_trend_for_period(qapp):
    w = _window(1000)
    w._set_period("day")
    # el período "day" aún no calculado puede devolver None: se fuerza el snapshot
    w._monitor.usage_for_period = lambda p: [type("R", (), dict(
        app_name="A", bytes_sent=0, bytes_recv=1120))()]  # type: ignore[method-assign]
    w._refresh()
    texts = [lb.text() for lb in w._card_total.findChildren(QLabel)]
    assert any(t.startswith("▲ 12 %") for t in texts)
    w.close()


def test_window_session_has_no_trend(qapp):
    w = _window(1000)
    w._refresh()
    assert w._card_total.trend_text() == "esta sesión"
    assert w._card_down.trend_text() == ""
    w.close()


def test_window_define_limit_opens_quota(qapp):
    w = _window(None)
    called = []
    w._open_quota = lambda: called.append(1)  # type: ignore[method-assign]
    w._daily_card.define_clicked.emit()
    w._month_card.define_clicked.emit()
    assert called == [1, 1]
    w.close()
