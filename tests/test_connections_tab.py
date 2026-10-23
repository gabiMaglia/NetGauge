"""Pestaña Conexiones (tabla, filtros, estado vacío) y barra de estado; offscreen."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from src.domain.models import Connection, Settings, TrafficSample  # noqa: E402
from src.presentation.qt.i18n import set_language, t  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402
from src.presentation.qt.theme import DARK  # noqa: E402
from src.presentation.qt.viewmodel import conn_status_kind, filter_connections  # noqa: E402
from src.version import APP_VERSION  # noqa: E402

CONNS = [
    Connection("Dropbox", 2, "162.125.1.1", 443, "ESTABLISHED"),
    Connection("Google Chrome", 1, "142.250.1.1", 443, "ESTABLISHED"),
    Connection("Slack", 3, "127.0.0.1", 8080, "LISTEN"),
    Connection("Zoom", 4, "3.3.3.3", 8801, "TIME_WAIT"),
]
GEO = {"162.125.1.1": ("US", "Dropbox, Inc."), "142.250.1.1": ("AR", "Google LLC")}


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(qapp):
    set_language("es")
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings(hide_localhost=False)), FakeNotifier())
    m._on_sample(TrafficSample(1, "Chrome", bytes_sent=10, bytes_recv=20))
    state = {"conns": list(CONNS)}
    m.connections = lambda: list(state["conns"])  # type: ignore[method-assign]
    m.geo_for = lambda ip: GEO.get(ip)  # type: ignore[method-assign]
    w = MainWindow(m, per_process=True)
    w._state = state  # type: ignore[attr-defined]
    w._tabs.setCurrentIndex(2)
    w._refresh_connections()
    yield w
    w._timer.stop()
    m.set_snapshot_listener(None)
    w.deleteLater()


def _visible_apps(w: MainWindow) -> set[str]:
    return {r._app.text() for r in w._conn_rows.values() if not r.isHidden()}


# ---- lógica pura ----------------------------------------------------------
@pytest.mark.parametrize("status,kind", [
    ("ESTABLISHED", "established"), ("LISTEN", "listening"),
    ("CLOSE_WAIT", "closing"), ("TIME_WAIT", "closing"), ("FIN_WAIT1", "closing"),
    ("FIN_WAIT2", "closing"), ("SYN_SENT", "other"), ("", "other")])
def test_conn_status_kind(status, kind):
    assert conn_status_kind(status) == kind


def test_filter_connections_matches_app_ip_country_and_org():
    geo = GEO.get
    assert [c.app_name for c in filter_connections(CONNS, "drop", geo)] == ["Dropbox"]
    assert [c.app_name for c in filter_connections(CONNS, "142.250", geo)] == ["Google Chrome"]
    assert [c.app_name for c in filter_connections(CONNS, "US", geo)] == ["Dropbox"]
    assert [c.app_name for c in filter_connections(CONNS, "google llc", geo)] == ["Google Chrome"]
    assert len(filter_connections(CONNS, "  ", geo)) == len(CONNS)


# ---- tabla y filtros ------------------------------------------------------
def test_text_filter_keeps_only_dropbox(win):
    win._conn_search.setText("drop")
    assert _visible_apps(win) == {"Dropbox"}


def test_empty_state_toggles_with_data(win):
    assert win._conn_empty.isHidden()
    win._state["conns"] = []
    win._refresh_connections()
    assert not win._conn_empty.isHidden()
    win._state["conns"] = list(CONNS)
    win._refresh_connections()
    assert win._conn_empty.isHidden()


def test_filter_without_matches_shows_empty_state(win):
    win._conn_search.setText("zzzz")
    assert not win._conn_empty.isHidden()
    assert _visible_apps(win) == set()


def test_status_chips_filter_exclusively(win):
    win._conn_chips["established"].click()
    assert _visible_apps(win) == {"Dropbox", "Google Chrome"}
    win._conn_chips["listening"].click()
    assert _visible_apps(win) == {"Slack"}
    win._conn_chips["all"].click()
    assert len(_visible_apps(win)) == 4


def test_all_chip_counts_before_status_filter_after_hide_localhost(win):
    assert win._conn_chips["all"].text() == t("conn.filter.all", n=4)
    win._conn_chips["established"].click()
    assert win._conn_chips["all"].text() == t("conn.filter.all", n=4)
    win._hide_local_cb.setChecked(True)          # Slack escucha en 127.0.0.1
    assert win._conn_chips["all"].text() == t("conn.filter.all", n=3)


def test_hide_localhost_persists_in_settings(win):
    assert win._monitor.settings.hide_localhost is False
    win._hide_local_cb.setChecked(True)
    assert win._monitor.settings.hide_localhost is True
    assert "Slack" not in _visible_apps(win)
    win._hide_local_cb.setChecked(False)
    assert win._monitor.settings.hide_localhost is False


def test_rows_are_reused_in_place_across_refreshes(win):
    before = dict(win._conn_rows)
    win._refresh_connections()
    assert {k: id(v) for k, v in before.items()} == {
        k: id(v) for k, v in win._conn_rows.items()}


def test_filter_text_and_chip_survive_refresh(win):
    win._conn_search.setText("drop")
    win._conn_chips["established"].click()
    win._refresh_connections()
    assert win._conn_search.text() == "drop"
    assert win._conn_chips["established"].isChecked()
    assert _visible_apps(win) == {"Dropbox"}


def test_row_columns_country_status_and_traffic(win):
    row = win._conn_rows["Dropbox|162.125.1.1:443|ESTABLISHED"]
    assert row._geo.text() == "US"
    assert row._status.text() == t("conn.status.established")
    assert row._status.property("kind") == "established"
    assert row._traffic.text() == "—"       # el modelo no tiene bytes por conexión
    assert row._endpoint.text() == "162.125.1.1:443"
    zoom = win._conn_rows["Zoom|3.3.3.3:8801|TIME_WAIT"]
    assert zoom._geo.text() == "—"
    assert zoom._status.property("kind") == "closing"


def test_switching_to_connections_tab_draws_table_without_spark_side_effects(win):
    win._tabs.setCurrentIndex(0)
    win._state["conns"] = [CONNS[0]]
    win._refresh()
    sparks = len(win._spark_total)
    win._tabs.setCurrentIndex(2)
    assert len(win._spark_total) == sparks
    assert _visible_apps(win) == {"Dropbox"}


def test_connections_not_requested_when_tab_hidden(win):
    calls = []
    win._monitor.connections = lambda: calls.append(1) or []  # type: ignore[method-assign]
    win._tabs.setCurrentIndex(0)
    win._refresh_connections()
    assert calls == []


# ---- checkbox con indicador propio ---------------------------------------
def _has_color(img, color: str, max_x: int) -> bool:
    want = QColor(color).rgb()
    return any(img.pixelColor(x, y).rgb() == want
               for x in range(max_x) for y in range(img.height()))


def _row_extent(img, color: str, max_x: int) -> int:
    """Ancho (px) que ocupa `color` en la fila central del indicador."""
    want = QColor(color).rgb()
    y = img.height() // 2
    xs = [x for x in range(max_x) if img.pixelColor(x, y).rgb() == want]
    return (max(xs) - min(xs) + 1) if xs else 0


def test_checked_indicator_is_painted_with_accent_and_20px(win):
    win.show()
    QApplication.processEvents()
    cb = win._hide_local_cb
    cb.setChecked(False)
    off = cb.grab().toImage()
    assert not _has_color(off, DARK["accent"], 24)
    # sin marcar: sólo el borde de 1px del token (borde izquierdo + derecho = 20px de ancho)
    assert _has_color(off, DARK["border"], 24)
    assert _row_extent(off, DARK["border"], 30) == 20
    cb.setChecked(True)
    on = cb.grab().toImage()
    assert _has_color(on, DARK["accent"], 24)
    assert _has_color(on, DARK["on_accent"], 24)    # la tilde
    assert _row_extent(on, DARK["accent"], 30) >= 18


def test_check_icon_url_is_quoted_and_file_has_requested_color():
    import re

    from src.presentation.qt.theme import app_qss, check_icon_url
    qss = app_qss(DARK)
    m = re.search(r'image: url\("([^"]+)"\)', qss)
    assert m, "el url() del tilde debe ir entre comillas"
    assert "\\" not in m.group(1)
    from pathlib import Path
    path = Path(check_icon_url("#123abc"))
    assert path.is_file() and 'stroke="#123abc"' in path.read_text(encoding="utf-8")
    assert check_icon_url("#123abc") == path.as_posix()   # cacheado: no re-crea


def test_elided_label_keeps_plaintext_and_tooltips_full_text_when_cut(qapp):
    from src.presentation.qt.widgets import ElidedLabel
    lbl = ElidedLabel("<b>" + "x" * 200 + "</b>")
    lbl.resize(60, 20)
    lbl.grab()
    assert lbl.textFormat() == Qt.TextFormat.PlainText
    # rich text escapado: el nombre se ve literal, sin interpretar <b>
    assert "&lt;b&gt;" in lbl.toolTip() and "<b>" not in lbl.toolTip()
    amp = ElidedLabel("A&B <i>" + "y" * 200)
    amp.resize(60, 20)
    amp.grab()
    assert "A&amp;B &lt;i&gt;" in amp.toolTip()
    short = ElidedLabel("ok")
    short.resize(200, 20)
    short.grab()
    assert short.toolTip() == ""


# ---- barra de estado ------------------------------------------------------
def test_statusbar_per_process_active(win):
    assert win._status_text.text() == t("status.capture_on")
    assert win._status_dot.property("state") == "on"
    assert DARK["upload"] in win._status_dot.styleSheet()
    assert win._status_right.text() == f"{t('period.session')} · v{APP_VERSION}"
    assert win._status_bar.minimumHeight() == win._status_bar.maximumHeight() == 30


def test_statusbar_global_mode_uses_warning_dot(qapp):
    set_language("es")
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(), FakeStore(Settings()),
                       FakeNotifier())
    w = MainWindow(m, per_process=False)
    try:
        assert w._status_text.text() == t("status.capture_off")
        assert w._status_dot.property("state") == "off"
        assert DARK["warning"] in w._status_dot.styleSheet()
        assert w._status_text.toolTip() == t("mode.global_tip")
    finally:
        w._timer.stop()
        m.set_snapshot_listener(None)
        w.deleteLater()


def test_statusbar_period_follows_selection(win):
    win._set_period("day")
    assert win._status_right.text() == f"{t('period.day')} · v{APP_VERSION}"


def test_light_theme_keeps_working_and_recolors_statusbar(win):
    from src.presentation.qt.theme import LIGHT
    win._toggle_theme()
    assert LIGHT["upload"] in win._status_dot.styleSheet()
    win.show()
    QApplication.processEvents()
    win._hide_local_cb.setChecked(True)
    assert _has_color(win._hide_local_cb.grab().toImage(), LIGHT["accent"], 24)
