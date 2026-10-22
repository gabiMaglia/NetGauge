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
from src.presentation.qt.widgets import (  # noqa: E402
    AppRow, LimitCard, LiveChart, MetricCard, nice_ticks)


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
    """prev: (sent, recv) del período previo o None."""
    QApplication.instance() or QApplication([])
    set_language("es")
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    m._on_sample(TrafficSample(1, "A", bytes_sent=0, bytes_recv=1120))
    m.previous_period_breakdown = lambda period: prev  # type: ignore[method-assign]
    m.previous_period_total = lambda period: sum(prev) if prev else None  # type: ignore[method-assign]
    return MainWindow(m, per_process=True)


def test_window_cards_show_per_direction_trend(qapp):
    w = _window((100, 200))
    w._period = "day"
    w._monitor.usage_for_period = lambda p: [type("R", (), dict(
        app_name="A", bytes_sent=96, bytes_recv=224))()]  # type: ignore[method-assign]
    w._refresh()
    assert w._card_down.trend_text() == "▲ 12 % vs ayer"
    assert w._card_up.trend_text() == "▼ 4 % vs ayer"
    assert w._card_total.trend_text().startswith("▲ 7 %")  # 320 vs 300
    w.close()


def test_window_no_previous_hides_card_trends(qapp):
    w = _window(None)
    w._period = "day"
    w._monitor.usage_for_period = lambda p: [type("R", (), dict(
        app_name="A", bytes_sent=96, bytes_recv=224))()]  # type: ignore[method-assign]
    w._refresh()
    assert w._card_down.trend_text() == "" and w._card_up.trend_text() == ""
    w.close()


@pytest.mark.parametrize("pct,key", [(50, "limit.hint_80"), (85, "limit.hint_over"),
                                     (100, "limit.hint_reached")])
def test_limit_hint_depends_on_state(qapp, pct, key):
    from src.presentation.qt.i18n import t
    set_language("es")
    w = _window(None)
    status = type("S", (), dict(has_limit=True, used_bytes=pct, limit_bytes=100,
                                percent=float(pct)))()
    w._set_limit(w._daily_card, status, "quota.daily", "limit.daily")
    assert w._daily_card._hint.text() == t(key)
    w.close()


def test_window_session_has_no_trend(qapp):
    w = _window((500, 500))
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


# ---- pestaña Por aplicación ------------------------------------------------
def _apps_window(apps=(("Google Chrome", 100, 900), ("Dropbox", 50, 300), ("Slack", 5, 20))):
    QApplication.instance() or QApplication([])
    set_language("es")
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    for i, (name, sent, recv) in enumerate(apps, start=1):
        m._on_sample(TrafficSample(i, name, bytes_sent=sent, bytes_recv=recv))
    w = MainWindow(m, per_process=True)
    w.show()
    w._tabs.setCurrentIndex(1)
    w._refresh()
    return w


def _order(w):
    """Nombres de las filas visibles, de arriba a abajo."""
    lay = w._apps_lay
    items = [lay.itemAt(i).widget() for i in range(lay.count())]
    by_row = {id(r): n for n, r in w._app_rows.items()}
    return [by_row[id(x)] for x in items if x is not None and id(x) in by_row
            and not x.isHidden()]


def test_app_row_update_data_texts(qapp):
    row = AppRow(DARK, "Chrome")
    row.update_data("655,5 MB", "↓ 8,1 MB/s\n↑ 640 KB/s", "52 %", 100.0, "3 conexiones", True)
    assert row._tot.text() == "655,5 MB"
    assert row._share.text() == "52 %"
    assert row._conns.text() == "3 conexiones"
    assert "8,1 MB/s" in row._rate.text() and "640 KB/s" in row._rate.text()
    assert row._nm.text() == "Chrome"
    row.update_data("1 MB", "↓ 0 B/s\n↑ 0 B/s", "1 %", 10.0, "", False)
    assert row._conns.text() == ""


def test_app_row_icon_refreshes_only_when_path_changes(qapp):
    import sys
    row = AppRow(DARK, "Python")
    first = row._badge.pixmap().toImage()
    row.set_icon(None)
    assert row._badge.pixmap().toImage() == first
    row.set_icon(sys.executable)  # la ruta aparece en un repintado posterior
    assert row._icon_path == sys.executable
    row.set_icon(sys.executable)  # sin cambio: no se vuelve a pedir
    assert row._icon_path == sys.executable


def test_apps_tab_orders_by_total_and_highlights_first(qapp):
    w = _apps_window()
    assert _order(w) == ["Google Chrome", "Dropbox", "Slack"]
    assert w._app_rows["Google Chrome"].objectName() == "AppRowActive"
    assert w._app_rows["Dropbox"].objectName() == "AppRow"
    assert w._app_rows["Google Chrome"]._share.text() == "73 %"  # 1000 de 1375
    w.close()


def test_apps_search_filters_rows_and_survives_refresh(qapp):
    w = _apps_window()
    w._apps_search.setText("chr")
    w._refresh()
    # Reconciliación: las filas filtradas quedan ocultas (siguen en _app_rows).
    assert _order(w) == ["Google Chrome"]
    assert w._app_rows["Dropbox"].isHidden() and w._app_rows["Slack"].isHidden()
    w._refresh()
    w._refresh()
    assert w._apps_search.text() == "chr"
    assert _order(w) == ["Google Chrome"]
    w._apps_search.setText("")
    w._refresh()
    assert _order(w) == ["Google Chrome", "Dropbox", "Slack"]
    w.close()


def test_apps_empty_result_label(qapp):
    w = _apps_window()
    assert w._apps_empty.isHidden()
    w._apps_search.setText("zzz")
    w._refresh()
    assert not w._apps_empty.isHidden()
    assert w._apps_empty.text() == "Sin resultados para «zzz»"
    w._apps_search.setText("slack")
    w._refresh()
    assert w._apps_empty.isHidden()
    w.close()


def test_sort_chips_change_order(qapp):
    # Chrome: más total y bajada; Dropbox: más subida.
    w = _apps_window((("Chrome", 10, 900), ("Dropbox", 500, 100), ("Slack", 1, 1)))
    assert w._apps_sort == "total" and _order(w)[0] == "Chrome"
    w._sort_chips["up"].click()
    assert w._apps_sort == "up" and _order(w)[0] == "Dropbox"
    w._sort_chips["down"].click()
    assert w._apps_sort == "down" and _order(w)[0] == "Chrome"
    assert w._app_rows["Chrome"].objectName() == "AppRowActive"
    assert w._app_rows["Dropbox"].objectName() == "AppRow"
    assert sum(1 for c in w._sort_chips.values() if c.isChecked()) == 1
    w.close()


def test_sort_by_now_uses_live_rate(qapp):
    w = _apps_window((("Chrome", 0, 1000), ("Dropbox", 0, 10)))
    now = [100.0]
    w._clock = lambda: now[0]  # reloj inyectable: tasas deterministas
    w._tick()  # primera lectura: tasas 0
    w._monitor._on_sample(TrafficSample(2, "Dropbox", bytes_sent=0, bytes_recv=900_000))
    now[0] = 101.0
    w._tick()
    w._refresh()
    w._sort_chips["now"].click()
    assert _order(w)[0] == "Dropbox"
    assert "↓" in w._app_rows["Dropbox"]._rate.text()
    w.close()


def test_apps_connections_count_text(qapp):
    from src.domain.models import Connection
    w = _apps_window()
    conns = [Connection("Slack", 3, "1.1.1.1", 443, "ESTABLISHED"),
             Connection("Google Chrome", 1, "8.8.8.8", 443, "ESTABLISHED"),
             Connection("Google Chrome", 1, "8.8.4.4", 443, "ESTABLISHED")]
    w._monitor.connections = lambda: conns  # type: ignore[method-assign]
    w._refresh()
    assert w._app_rows["Google Chrome"]._conns.text() == "2 conexiones"
    assert w._app_rows["Slack"]._conns.text() == "1 conexión"
    assert w._app_rows["Dropbox"]._conns.text() == ""
    w.close()


def test_search_and_sort_do_not_advance_sparklines(qapp):
    w = _apps_window()
    n = len(w._spark_total)
    for text in ("c", "ch", "chr", ""):
        w._apps_search.setText(text)
    for code in ("up", "down", "now", "total"):
        w._sort_chips[code].click()
    assert len(w._spark_total) == len(w._spark_down) == len(w._spark_up) == n
    w._refresh()
    assert len(w._spark_total) == n + 1
    w.close()


def test_trust_for_called_for_every_visible_row(qapp):
    w = _apps_window()
    seen = []
    real = w._monitor.trust_for
    w._monitor.trust_for = lambda app: (seen.append(app), real(app))[1]  # type: ignore[method-assign]
    w._refresh()
    assert set(seen) == {"Google Chrome", "Dropbox", "Slack"}
    seen.clear()
    w._apps_search.setText("slack")
    assert set(seen) == {"Slack"}
    w.close()


def test_switching_to_apps_tab_shows_connection_counts_at_once(qapp):
    from src.domain.models import Connection
    w = _apps_window()
    w._tabs.setCurrentIndex(0)
    w._monitor.connections = lambda: [Connection("Slack", 3, "1.1.1.1", 443, "E")]  # type: ignore[method-assign]
    w._refresh()
    assert w._app_rows["Slack"]._conns.text() == ""
    w._tabs.setCurrentIndex(1)
    assert w._app_rows["Slack"]._conns.text() == "1 conexión"
    w.close()
