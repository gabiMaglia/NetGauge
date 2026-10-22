"""Ventana principal NetGauge (frameless, redondeada, con barra de título propia)."""
from __future__ import annotations

import html
import ipaddress
import sys

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...application.monitor_service import MonitorService
from .about_dialog import AboutDialog
from .geometry import available_screen_rects, clamp_to_screens
from .icons import svg_icon
from .i18n import fmt_number, loc_bytes, set_language, t
from .native_window import apply_native_chrome, handle_native_event
from .quota_dialog import QuotaDialog
from .settings_dialog import SettingsDialog
from .theme import DARK, LIGHT, app_qss
from .widgets import AppRow, BarsLogo, ConnRow, LiveChart, MetricCard, QuotaBar

_UNITS = {"Auto": None, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
_TITLEBAR_H = 56
_PERIOD_CODES = ["session", "day", "week", "month"]


def trust_tooltip_text(info, translate) -> str:
    """Tooltip de confianza como rich text: el signer/razones vienen de fuera
    (cert del ejecutable) y se escapan para que Qt no los interprete como HTML."""
    lines = [f"{translate('trust.title')}: {translate('trust.level.' + info.level)}"]
    for r in info.reasons:
        if r == "trust.signed_by":
            lines.append("• " + translate(r, signer=info.signer or "?"))
        elif r in ("trust.vt_clean", "trust.vt_detected"):
            lines.append("• " + translate(r, m=info.vt_malicious, n=info.vt_total))
        else:
            lines.append("• " + translate(r))
    return "<br>".join(html.escape(line) for line in lines)


def _is_loopback(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


def _fmt(num: float, unit: str) -> tuple[str, str]:
    """Devuelve (valor, unidad) según la unidad elegida, con formato por locale."""
    div = _UNITS.get(unit)
    if div is None:
        val, _, u = loc_bytes(num).partition(" ")
        return val, u or "B"
    return fmt_number(num / div, 1, group=True), unit


class MainWindow(QWidget):
    # Aviso del worker de MonitorService: "hay snapshot nuevo". Se emite desde
    # OTRO hilo; la conexión encolada garantiza que _refresh corre en el GUI.
    snapshot_ready = Signal()

    # Callback opcional (lo cablea app.run) tras guardar Ajustes.
    on_settings_saved = None

    def __init__(self, monitor: MonitorService, per_process: bool) -> None:
        super().__init__()
        self._monitor = monitor
        self._per_process = per_process
        set_language(monitor.settings.language)
        self._dark = True
        self._theme = DARK
        self._period = "session"
        self._unit = monitor.settings.preferred_unit
        if self._unit not in _UNITS:
            self._unit = "Auto"
        self._drag_pos: QPoint | None = None
        self._app_rows: dict[str, AppRow] = {}   # filas reutilizadas por nombre
        self._conn_rows: dict[str, ConnRow] = {}  # filas de conexión reutilizadas
        self._period_chips: list[tuple[QPushButton, str]] = []
        self._legends: list[tuple[QLabel, str]] = []
        self._maximized = False
        self._restore_geom = None
        self._native = False
        self._native_applied = False

        self.setWindowTitle("NetGauge")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(786, 720)
        self.setMinimumSize(420, 360)  # límite para que el resize no rompa el layout
        self._restore_geometry()

        self._build_ui()
        self._apply_theme()
        self._native = apply_native_chrome(self, caption_height=_TITLEBAR_H)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        # Los datos pesados (SQLite, psutil, firma de .exe) los calcula el
        # worker de MonitorService; acá sólo se repinta cuando avisa.
        self.snapshot_ready.connect(self._refresh, Qt.ConnectionType.QueuedConnection)
        monitor.set_snapshot_listener(self.snapshot_ready.emit)
        self._refresh()

    # ---- construcción --------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._root = QFrame()
        self._root.setObjectName("Root")
        outer.addWidget(self._root)

        root_lay = QVBoxLayout(self._root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        root_lay.addWidget(self._build_titlebar())

        body = QFrame()
        body.setObjectName("Body")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(20, 16, 20, 20)
        body_lay.setSpacing(18)
        body_lay.addLayout(self._build_toolbar())
        body_lay.addWidget(self._build_tabs(), 1)
        root_lay.addWidget(body, 1)

    def _build_titlebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(_TITLEBAR_H)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 14, 0)
        lay.setSpacing(10)

        self._logo = BarsLogo(26, 8)
        lay.addWidget(self._logo)
        brand = QLabel('Net<span style="color:#3b82f6;">Gauge</span>')
        brand.setObjectName("BrandName")
        lay.addWidget(brand)
        self._style_mode_badge()
        lay.addStretch()

        self._speed_down, self._unit_down = self._speed_group(lay, "SpeedDown", "↓")
        lay.addSpacing(10)
        self._speed_up, self._unit_up = self._speed_group(lay, "SpeedUp", "↑")
        lay.addSpacing(8)
        sep = QFrame()
        sep.setObjectName("TitleSep")
        sep.setFixedSize(1, 24)
        lay.addWidget(sep)
        lay.addSpacing(8)

        self._about_btn = self._icon_btn("info", "btn.about", self._open_about)
        self._settings_btn = self._icon_btn("settings", "btn.settings", self._open_settings)
        self._theme_btn = self._icon_btn("moon", "btn.theme", self._toggle_theme)
        for b in (self._about_btn, self._settings_btn, self._theme_btn):
            lay.addWidget(b)
        lay.addSpacing(6)

        self._min_btn = self._win_btn("minimize", self.showMinimized)
        self._max_btn = self._win_btn("maximize", self._toggle_maximize)
        self._close_btn = self._win_btn("close", self.hide)  # cerrar -> al tray
        self._close_btn.setProperty("class", "CloseBtn")
        for b in (self._min_btn, self._max_btn, self._close_btn):
            lay.addWidget(b)
        self._titlebar = bar
        return bar

    def _speed_group(self, lay: QHBoxLayout, name: str, arrow: str) -> tuple[QLabel, QLabel]:
        """Flecha + valor grande mono + unidad chica; devuelve (valor, unidad)."""
        arrow_lbl = QLabel(arrow)
        arrow_lbl.setObjectName(name)
        value = QLabel("0")
        value.setObjectName(name)
        unit = QLabel("B/s")
        unit.setObjectName("SpeedUnit")
        lay.addWidget(arrow_lbl)
        lay.addSpacing(-4)
        lay.addWidget(value)
        lay.addSpacing(-4)
        lay.addWidget(unit)
        return value, unit

    def _icon_btn(self, icon: str, tip_key: str, slot) -> QPushButton:
        b = QPushButton()
        b.setObjectName("IconBtn")
        b.setFixedSize(36, 36)
        b.setIconSize(QSize(18, 18))
        b.setProperty("icon_name", icon)
        b.setToolTip(t(tip_key))
        b.clicked.connect(slot)
        return b

    def _win_btn(self, icon: str, slot) -> QPushButton:
        b = QPushButton()
        b.setObjectName("WinBtn")
        b.setFixedSize(32, 32)
        b.setIconSize(QSize(16, 16))
        b.setProperty("icon_name", icon)
        b.clicked.connect(slot)
        return b

    def _recolor_icons(self) -> None:
        """Re-pinta los íconos de la barra con el color muted del tema activo."""
        color = self._theme["text_muted"]
        for b in (self._about_btn, self._settings_btn, self._theme_btn,
                  self._min_btn, self._max_btn, self._close_btn):
            b.setIcon(svg_icon(b.property("icon_name"), color, b.iconSize().width()))

    def _build_toolbar(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(12)

        seg = QFrame()
        seg.setObjectName("Segment")
        seg_lay = QHBoxLayout(seg)
        seg_lay.setContentsMargins(3, 3, 3, 3)
        seg_lay.setSpacing(3)
        self._seg_group = QButtonGroup(self)
        self._seg_group.setExclusive(True)
        for value in _PERIOD_CODES:
            chip = QPushButton(t("period." + value))
            chip.setObjectName("SegChip")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda _c, v=value: self._set_period(v))
            if value == self._period:
                chip.setChecked(True)
            self._seg_group.addButton(chip)
            seg_lay.addWidget(chip)
            self._period_chips.append((chip, value))
        lay.addWidget(seg)
        lay.addStretch()

        self._unit_box = QComboBox()
        self._unit_box.setObjectName("UnitBox")
        self._unit_box.addItems(list(_UNITS.keys()))
        self._unit_box.setCurrentText(self._unit)
        self._unit_box.currentTextChanged.connect(self._set_unit)
        lay.addWidget(self._unit_box)

        self._quota_btn = QPushButton(t("btn.quota"))
        self._quota_btn.setObjectName("QuotaBtn")
        self._quota_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._quota_btn.clicked.connect(self._open_quota)
        lay.addWidget(self._quota_btn)
        return lay

    def _build_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_global_tab(), t("tab.global"))
        self._tabs.addTab(self._build_apps_tab(), t("tab.apps"))
        self._tabs.addTab(self._build_connections_tab(), t("tab.connections"))
        return self._tabs

    def _build_global_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(14)

        cards = QGridLayout()
        cards.setSpacing(14)
        self._card_down = MetricCard(self._theme, "#3b82f6", t("card.download"))
        self._card_up = MetricCard(self._theme, "#10b981", t("card.upload"))
        self._card_total = MetricCard(self._theme, "", t("card.total"), is_total=True)
        cards.addWidget(self._card_down, 0, 0)
        cards.addWidget(self._card_up, 0, 1)
        cards.addWidget(self._card_total, 0, 2)
        lay.addLayout(cards)

        chart_card = QFrame()
        self._chart_card = chart_card
        chart_card.setObjectName("ChartCard")
        cc = QVBoxLayout(chart_card)
        cc.setContentsMargins(16, 14, 16, 14)
        cc.setSpacing(10)
        head = QHBoxLayout()
        self._chart_title = QLabel(t("chart.title"))
        self._chart_title.setObjectName("SectionTitle")
        head.addWidget(self._chart_title)
        head.addStretch()
        self._peak_chip = QLabel(t("chart.peak", v="0 B"))
        self._peak_chip.setObjectName("Chip")
        head.addWidget(self._peak_chip)
        head.addSpacing(8)
        head.addWidget(self._legend(t("legend.download"), self._theme["accent"]))
        head.addWidget(self._legend(t("legend.upload"), self._theme["upload"]))
        cc.addLayout(head)
        self._chart = LiveChart(self._theme)
        cc.addWidget(self._chart, 1)
        lay.addWidget(chart_card, 1)

        chart_card.setMinimumHeight(170)  # el gráfico no se aplasta a 0 en alto chico

        self._daily_lbl, self._daily_val, self._daily_bar = self._quota_row(lay)
        self._month_lbl, self._month_val, self._month_bar = self._quota_row(lay, warn=True)

        # Scrollable: si la ventana queda baja, no se corta el ancho de banda.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        return scroll

    def _legend(self, text: str, color: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        dash = QLabel()
        dash.setFixedSize(10, 3)
        dash.setStyleSheet(f"background:{color}; border-radius:1px;")
        lbl = QLabel(text)
        lbl.setObjectName("LegendText")
        lay.addWidget(dash)
        lay.addWidget(lbl)
        # recordamos la clave (download/upload) por orden de creación
        key = "legend.download" if not self._legends else "legend.upload"
        self._legends.append((lbl, key))
        return w

    def _quota_row(self, parent_lay, warn: bool = False):
        box = QVBoxLayout()
        box.setSpacing(6)
        head = QHBoxLayout()
        lbl = QLabel("")
        lbl.setObjectName("QuotaLabel")
        val = QLabel("")
        val.setObjectName("QuotaValue")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        head.addWidget(lbl)
        head.addStretch()
        head.addWidget(val)
        box.addLayout(head)
        bar = QuotaBar(self._theme, warn=warn)
        box.addWidget(bar)
        parent_lay.addLayout(box)
        return lbl, val, bar

    def _build_apps_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._apps_container = QWidget()
        self._apps_container.setObjectName("AppsContainer")
        self._apps_lay = QVBoxLayout(self._apps_container)
        self._apps_lay.setContentsMargins(0, 12, 0, 0)
        self._apps_lay.setSpacing(6)
        self._apps_lay.addStretch()
        scroll.setWidget(self._apps_container)
        return scroll

    def _build_connections_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(8)
        head = QHBoxLayout()
        self._conn_subtitle = QLabel(t("conn.subtitle"))
        self._conn_subtitle.setObjectName("AppSplit")
        head.addWidget(self._conn_subtitle)
        head.addStretch()
        self._hide_local_cb = QCheckBox(t("conn.hide_localhost"))
        self._hide_local_cb.setChecked(self._monitor.settings.hide_localhost)
        self._hide_local_cb.toggled.connect(self._toggle_hide_localhost)
        head.addWidget(self._hide_local_cb)
        lay.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._conn_container = QWidget()
        self._conn_container.setObjectName("AppsContainer")
        self._conn_lay = QVBoxLayout(self._conn_container)
        self._conn_lay.setContentsMargins(0, 0, 0, 0)
        self._conn_lay.setSpacing(2)
        self._conn_empty = QLabel(t("conn.empty"))
        self._conn_empty.setObjectName("AppSplit")
        self._conn_lay.addWidget(self._conn_empty)
        self._conn_lay.addStretch()
        scroll.setWidget(self._conn_container)
        lay.addWidget(scroll, 1)
        return page

    # ---- datos / refresco ---------------------------------------------
    def _rows(self):
        if self._period == "session":
            return [(u.app_name, u.bytes_sent, u.bytes_recv)
                    for u in self._monitor.session_usage()]
        recs = self._monitor.usage_for_period(self._period)
        if recs is None:        # período aún no calculado: esperar al snapshot
            return None
        return [(r.app_name, r.bytes_sent, r.bytes_recv) for r in recs]

    def _refresh(self) -> None:
        rows = self._rows()
        if rows is None:
            return
        tot_sent = sum(s for _, s, _ in rows)
        tot_recv = sum(r for _, _, r in rows)
        total = tot_sent + tot_recv

        v, u = _fmt(tot_recv, self._unit)
        pct_d = (tot_recv / total * 100) if total else 0
        self._card_down.set_values(v, u, t("card.pct_of_total", p=f"{pct_d:.0f}"))
        v, u = _fmt(tot_sent, self._unit)
        pct_u = (tot_sent / total * 100) if total else 0
        self._card_up.set_values(v, u, t("card.pct_of_total", p=f"{pct_u:.0f}"))
        v, u = _fmt(total, self._unit)
        self._card_total.set_values(v, u, t("card.period_usage"))

        # Barras de cuota
        d = self._monitor.daily_status()
        self._daily_lbl.setText(t("quota.daily"))
        if d.has_limit:
            self._daily_val.setText(
                f"{loc_bytes(d.used_bytes)} / {loc_bytes(d.limit_bytes)} "
                f"({d.percent:.0f}%)")
            self._daily_bar.set_percent(d.percent)
        else:
            self._daily_val.setText(f"{loc_bytes(d.used_bytes)} · {t('quota.no_limit')}")
            self._daily_bar.set_percent(0)
        m = self._monitor.quota_status()
        self._month_lbl.setText(t("quota.monthly"))
        if m.has_limit:
            self._month_val.setText(
                f"{loc_bytes(m.used_bytes)} / {loc_bytes(m.limit_bytes)} "
                f"({m.percent:.0f}%)")
            self._month_bar.set_percent(m.percent)
        else:
            self._month_val.setText(f"{loc_bytes(m.used_bytes)} · {t('quota.no_limit')}")
            self._month_bar.set_percent(0)

        self._rebuild_apps(rows, total)
        self._refresh_connections()

    def _rebuild_apps(self, rows, total) -> None:
        """Reconciliación in-place: reutiliza filas, no las recrea cada segundo."""
        wanted = [r[0] for r in rows]

        for name in list(self._app_rows):
            if name not in wanted:
                row = self._app_rows.pop(name)
                self._apps_lay.removeWidget(row)
                row.deleteLater()

        for i, (app, sent, recv) in enumerate(rows):
            tt = sent + recv
            pct = (tt / total * 100) if total else 0
            vt, ut = _fmt(tt, self._unit)
            vd, _ = _fmt(recv, self._unit)
            vu, _ = _fmt(sent, self._unit)
            row = self._app_rows.get(app)
            if row is None:
                row = AppRow(self._theme, app)
                self._app_rows[app] = row
            if self._apps_lay.indexOf(row) != i:
                self._apps_lay.removeWidget(row)
                self._apps_lay.insertWidget(i, row)
            row.update_data(f"{vt} {ut}", f"↓{vd} ↑{vu}", pct, active=(i == 0))
            info = self._monitor.trust_for(app)
            row.set_trust(info.level, self._trust_tooltip(info))
            row.set_vt_badge(info.vt_malicious, info.vt_total,
                             self._vt_badge_tooltip(info))

    def _trust_tooltip(self, info) -> str:
        return trust_tooltip_text(info, t)

    def _vt_badge_tooltip(self, info) -> str:
        if not info.vt_total:
            return ""
        key = "trust.vt_detected" if (info.vt_malicious or 0) > 0 else "trust.vt_clean"
        return t(key, m=info.vt_malicious, n=info.vt_total)

    def _refresh_connections(self) -> None:
        if self._tabs.currentIndex() != 2:  # solo si la pestaña está visible
            return
        conns = self._monitor.connections()
        if self._monitor.settings.hide_localhost:
            conns = [c for c in conns if not _is_loopback(c.raddr)]
        conns = sorted(conns, key=lambda c: c.app_name.lower())[:200]
        self._conn_empty.setVisible(not conns)

        wanted = {}
        for c in conns:
            key = f"{c.app_name}|{c.raddr}:{c.rport}|{c.status}"
            wanted[key] = c

        # 1) eliminar conexiones que ya no están
        for key in list(self._conn_rows):
            if key not in wanted:
                row = self._conn_rows.pop(key)
                self._conn_lay.removeWidget(row)
                row.deleteLater()

        # 2) crear/actualizar/reordenar in-place (no se recrea todo cada 2s)
        for i, (key, c) in enumerate(wanted.items()):
            row = self._conn_rows.get(key)
            if row is None:
                row = ConnRow(c.app_name, f"{c.raddr}:{c.rport}", c.status)
                self._conn_rows[key] = row
            if self._conn_lay.indexOf(row) != i:
                self._conn_lay.removeWidget(row)
                self._conn_lay.insertWidget(i, row)
            geo = self._monitor.geo_for(c.raddr)
            row.set_geo(f"{geo[0]} · {geo[1]}"[:40] if geo else "")

    def _tick(self) -> None:
        up, down = self._monitor.live_rate()
        self._chart.push(up, down)
        for val, unit, rate in ((self._speed_down, self._unit_down, down),
                                (self._speed_up, self._unit_up, up)):
            num, _, u = loc_bytes(rate).partition(" ")
            val.setText(num)
            unit.setText(f"{u or 'B'}/s")
        self._peak_chip.setText(t("chart.peak", v=loc_bytes(self._chart.peak())))

    # ---- acciones ------------------------------------------------------
    def _set_period(self, value: str) -> None:
        self._period = value
        self._refresh()

    def _set_unit(self, unit: str) -> None:
        self._unit = unit
        s = self._monitor.settings
        s.preferred_unit = unit
        self._monitor.update_settings(s)
        self._refresh()

    def _toggle_hide_localhost(self, checked: bool) -> None:
        s = self._monitor.settings
        s.hide_localhost = checked
        self._monitor.update_settings(s)
        self._refresh_connections()

    def _open_quota(self) -> None:
        dlg = QuotaDialog(self._monitor.settings, self)
        dlg.setStyleSheet(app_qss(self._theme))
        if dlg.exec():
            self._monitor.update_settings(dlg.result_settings())
            self._refresh()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._monitor.settings, self,
                             reputation=self._monitor.reputation_service)
        dlg.setStyleSheet(app_qss(self._theme))
        if dlg.exec():
            new = dlg.result_settings()
            self._monitor.update_settings(new)
            set_language(new.language)
            self._retranslate()
            self._refresh()
            if self.on_settings_saved is not None:
                self.on_settings_saved(new)

    def _open_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.setStyleSheet(app_qss(self._theme))
        dlg.exec()

    def _retranslate(self) -> None:
        """Re-aplica todos los textos tras un cambio de idioma."""
        self._style_mode_badge()
        self._about_btn.setToolTip(t("btn.about"))
        self._settings_btn.setToolTip(t("btn.settings"))
        self._theme_btn.setToolTip(t("btn.theme"))
        self._quota_btn.setText(t("btn.quota"))
        for chip, value in self._period_chips:
            chip.setText(t("period." + value))
        self._tabs.setTabText(0, t("tab.global"))
        self._tabs.setTabText(1, t("tab.apps"))
        self._tabs.setTabText(2, t("tab.connections"))
        self._card_down.set_name(t("card.download"))
        self._card_up.set_name(t("card.upload"))
        self._card_total.set_name(t("card.total"))
        self._chart_title.setText(t("chart.title"))
        for lbl, key in self._legends:
            lbl.setText(t(key))
        self._conn_subtitle.setText(t("conn.subtitle"))
        self._hide_local_cb.setText(t("conn.hide_localhost"))

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        self._theme = DARK if self._dark else LIGHT
        self._apply_theme()
        self._chart.set_theme(self._theme)
        for bar in (self._daily_bar, self._month_bar):
            bar.set_theme(self._theme)
        for row in self._app_rows.values():
            row.set_theme(self._theme)

    def _apply_theme(self) -> None:
        self.setStyleSheet(app_qss(self._theme))
        self._recolor_icons()
        self._sync_max_icon()

    # ---- gestión de ventana (maximizar / persistir geometría) ---------
    def _style_mode_badge(self) -> None:
        # El modo de captura vive por ahora en el tooltip del logo (Task 8: barra de estado).
        per_app = self._per_process
        if per_app and sys.platform == "darwin":
            tip_key = "mode.nettop_tip"
        elif per_app:
            tip_key = "mode.etw_tip"
        else:
            tip_key = "mode.global_tip"
        self._logo.setToolTip(t(tip_key))

    def _sync_max_icon(self) -> None:
        maximized = self.isMaximized() if self._native else self._maximized
        self._max_btn.setProperty("icon_name", "restore" if maximized else "maximize")
        self._max_btn.setIcon(svg_icon("restore" if maximized else "maximize",
                                       self._theme["text_muted"], 16))

    def _toggle_maximize(self) -> None:
        if self._native:  # el SO maneja maximizar/restaurar (con animación y snap)
            self.showNormal() if self.isMaximized() else self.showMaximized()
            return
        if self._maximized:
            if self._restore_geom is not None:
                self.setGeometry(self._restore_geom)
            self._maximized = False
            self._sync_max_icon()
        else:
            self._restore_geom = self.geometry()
            self.setGeometry(self.screen().availableGeometry())  # respeta taskbar
            self._maximized = True
            self._sync_max_icon()

    def _restore_geometry(self) -> None:
        raw = self._monitor.settings.window_geometry
        if not raw:
            return
        try:
            x, y, w, h = (int(v) for v in raw.split(","))
        except (ValueError, AttributeError):
            return
        if w > 200 and h > 200:
            # Si el monitor donde estaba ya no existe, no restaurar fuera de pantalla.
            x, y, w, h = clamp_to_screens((x, y, w, h), available_screen_rects())
            self.setGeometry(x, y, w, h)

    def _save_geometry(self) -> None:
        if self._native:
            g = self.normalGeometry() if self.isMaximized() else self.geometry()
        else:
            g = self._restore_geom if self._maximized else self.geometry()
        if g is None or g.width() <= 0:
            return
        s = self._monitor.settings
        s.window_geometry = f"{g.x()},{g.y()},{g.width()},{g.height()}"
        self._monitor.update_settings(s)

    def hideEvent(self, event) -> None:
        self._save_geometry()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        # Reaplica el chrome nativo en el primer show (Qt finaliza estilos al mostrar).
        if self._native and not self._native_applied:
            self._native_applied = True
            apply_native_chrome(self, caption_height=_TITLEBAR_H)
        super().showEvent(event)

    def resizeEvent(self, event) -> None:
        # Responsive: en alto chico se oculta el gráfico de ancho de banda
        # para que las tarjetas y cuotas entren sin scroll.
        if hasattr(self, "_chart_card"):
            self._chart_card.setVisible(self.height() >= 600)
        super().resizeEvent(event)

    def changeEvent(self, event) -> None:
        # Mantiene el glifo del botón en sync cuando el SO maximiza/restaura.
        from PySide6.QtCore import QEvent
        if self._native and event.type() == QEvent.Type.WindowStateChange:
            self._sync_max_icon()
        super().changeEvent(event)

    def nativeEvent(self, event_type, message):
        if self._native:
            res = handle_native_event(self, message)
            if res is not None:
                return res
        return super().nativeEvent(event_type, message)

    # ---- arrastre manual (solo si NO hay chrome nativo) ---------------
    def mouseDoubleClickEvent(self, event) -> None:
        if not self._native and event.position().y() <= _TITLEBAR_H:
            self._toggle_maximize()
            event.accept()

    def mousePressEvent(self, event) -> None:
        if not self._native and event.button() == Qt.MouseButton.LeftButton \
                and event.position().y() <= 70:
            self._drag_pos = event.globalPosition().toPoint() \
                - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if not self._native and self._drag_pos is not None \
                and event.buttons() & Qt.MouseButton.LeftButton:
            if self._maximized:
                self._toggle_maximize()
                self._drag_pos = event.globalPosition().toPoint() \
                    - self.frameGeometry().topLeft()
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, _event) -> None:
        self._drag_pos = None
