"""Ventana principal trafficMe (frameless, redondeada, con barra de título propia)."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
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
from ...domain.models import human_bytes
from .about_dialog import AboutDialog
from .i18n import set_language, t
from .quota_dialog import QuotaDialog
from .settings_dialog import SettingsDialog
from .theme import DARK, LIGHT, app_qss
from .widgets import AppRow, BarsLogo, LiveChart, MetricCard, QuotaBar

_UNITS = {"Auto": None, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
_PERIOD_CODES = ["session", "day", "week", "month"]


def _fmt(num: float, unit: str) -> tuple[str, str]:
    """Devuelve (valor, unidad) según la unidad elegida."""
    div = _UNITS.get(unit)
    if div is None:
        txt = human_bytes(num)
        parts = txt.split(" ")
        return parts[0], parts[1] if len(parts) > 1 else "B"
    return f"{num / div:,.1f}", unit


class MainWindow(QWidget):
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
        self._data_ticks = 0
        self._period_chips: list[tuple[QPushButton, str]] = []
        self._legends: list[tuple[QLabel, str]] = []

        self.setWindowTitle("trafficMe")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(786, 720)

        self._build_ui()
        self._apply_theme()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
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
        bar.setFixedHeight(52)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 14, 0)
        lay.setSpacing(10)

        lay.addWidget(BarsLogo(26, 8))

        brand = QLabel('traffic<span style="color:#3b82f6;">Me</span>')
        brand.setObjectName("BrandName")
        lay.addWidget(brand)
        self._sub = QLabel(t("brand.sub"))
        self._sub.setObjectName("BrandSub")
        lay.addWidget(self._sub)
        lay.addStretch()

        self._speed_down = QLabel("↓ 0 B/s")
        self._speed_down.setObjectName("SpeedDown")
        self._speed_up = QLabel("↑ 0 B/s")
        self._speed_up.setObjectName("SpeedUp")
        lay.addWidget(self._speed_down)
        lay.addWidget(self._speed_up)
        lay.addSpacing(8)

        self._about_btn = QPushButton("ⓘ")
        self._about_btn.setObjectName("WinBtn")
        self._about_btn.setToolTip(t("btn.about"))
        self._about_btn.clicked.connect(self._open_about)
        lay.addWidget(self._about_btn)

        self._settings_btn = QPushButton("⚙︎")  # engranaje monocromo
        self._settings_btn.setObjectName("WinBtn")
        self._settings_btn.setToolTip(t("btn.settings"))
        self._settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(self._settings_btn)

        theme_btn = QPushButton("◐")
        theme_btn.setObjectName("WinBtn")
        theme_btn.clicked.connect(self._toggle_theme)
        mini = QPushButton("—")
        mini.setObjectName("WinBtn")
        mini.clicked.connect(self.showMinimized)
        close = QPushButton("✕")
        close.setObjectName("WinBtn")
        close.setProperty("class", "CloseBtn")
        close.clicked.connect(self.hide)  # cerrar -> al tray
        for b in (theme_btn, mini, close):
            lay.addWidget(b)
        self._titlebar = bar
        return bar

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

        self._daily_lbl, self._daily_val, self._daily_bar = self._quota_row(lay)
        self._month_lbl, self._month_val, self._month_bar = self._quota_row(lay, warn=True)
        return page

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
        self._conn_subtitle = QLabel(t("conn.subtitle"))
        self._conn_subtitle.setObjectName("AppSplit")
        lay.addWidget(self._conn_subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._conn_container = QWidget()
        self._conn_container.setObjectName("AppsContainer")
        self._conn_lay = QVBoxLayout(self._conn_container)
        self._conn_lay.setContentsMargins(0, 0, 0, 0)
        self._conn_lay.setSpacing(2)
        self._conn_lay.addStretch()
        scroll.setWidget(self._conn_container)
        lay.addWidget(scroll, 1)
        return page

    # ---- datos / refresco ---------------------------------------------
    def _rows(self):
        if self._period == "session":
            return [(u.app_name, u.bytes_sent, u.bytes_recv)
                    for u in self._monitor.session_usage()]
        return [(r.app_name, r.bytes_sent, r.bytes_recv)
                for r in self._monitor.usage_for_period(self._period)]

    def _refresh(self) -> None:
        rows = self._rows()
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
                f"{human_bytes(d.used_bytes)} / {human_bytes(d.limit_bytes)}")
            self._daily_bar.set_percent(d.percent)
        else:
            self._daily_val.setText(f"{human_bytes(d.used_bytes)} · {t('quota.no_limit')}")
            self._daily_bar.set_percent(0)
        m = self._monitor.quota_status()
        self._month_lbl.setText(t("quota.monthly"))
        if m.has_limit:
            self._month_val.setText(
                f"{human_bytes(m.used_bytes)} / {human_bytes(m.limit_bytes)}")
            self._month_bar.set_percent(m.percent)
        else:
            self._month_val.setText(f"{human_bytes(m.used_bytes)} · {t('quota.no_limit')}")
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

    def _trust_tooltip(self, info) -> str:
        lines = [f"{t('trust.title')}: {t('trust.level.' + info.level)}"]
        for r in info.reasons:
            if r == "trust.signed_by":
                lines.append("• " + t(r, signer=info.signer or "?"))
            elif r in ("trust.vt_clean", "trust.vt_detected"):
                lines.append("• " + t(r, m=info.vt_malicious, n=info.vt_total))
            else:
                lines.append("• " + t(r))
        return "\n".join(lines)

    def _refresh_connections(self) -> None:
        if self._tabs.currentIndex() != 2:  # solo si la pestaña está visible
            return
        while self._conn_lay.count() > 1:
            item = self._conn_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        conns = sorted(self._monitor.connections(), key=lambda c: c.app_name.lower())
        if not conns:
            empty = QLabel(t("conn.empty"))
            empty.setObjectName("AppSplit")
            self._conn_lay.insertWidget(0, empty)
            return
        for c in conns[:200]:
            self._conn_lay.insertWidget(self._conn_lay.count() - 1,
                                        self._conn_row(c))

    def _conn_row(self, c) -> QWidget:
        row = QFrame()
        row.setObjectName("AppRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(10)
        name = QLabel(c.app_name)
        name.setObjectName("AppName")
        lay.addWidget(name)
        geo = self._monitor.geo_for(c.raddr)
        if geo:
            cc, org = geo
            geo_lbl = QLabel(f"{cc} · {org}"[:40])
            geo_lbl.setObjectName("AppSplit")
            lay.addWidget(geo_lbl)
        lay.addStretch()
        remote = QLabel(f"{c.raddr}:{c.rport}")
        remote.setObjectName("AppTotal")
        lay.addWidget(remote)
        status = QLabel(c.status)
        status.setObjectName("Chip")
        lay.addWidget(status)
        return row

    def _tick(self) -> None:
        up, down = self._monitor.live_rate()
        self._chart.push(up, down)
        self._speed_down.setText(f"↓ {human_bytes(down)}/s")
        self._speed_up.setText(f"↑ {human_bytes(up)}/s")
        self._peak_chip.setText(t("chart.peak", v=human_bytes(self._chart.peak())))
        self._data_ticks += 1
        if self._data_ticks % 2 == 0:
            self._refresh()

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

    def _open_quota(self) -> None:
        dlg = QuotaDialog(self._monitor.settings, self)
        dlg.setStyleSheet(app_qss(self._theme))
        if dlg.exec():
            self._monitor.update_settings(dlg.result_settings())
            self._refresh()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._monitor.settings, self)
        dlg.setStyleSheet(app_qss(self._theme))
        if dlg.exec():
            new = dlg.result_settings()
            self._monitor.update_settings(new)
            set_language(new.language)
            self._retranslate()
            self._refresh()

    def _open_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.setStyleSheet(app_qss(self._theme))
        dlg.exec()

    def _retranslate(self) -> None:
        """Re-aplica todos los textos tras un cambio de idioma."""
        self._sub.setText(t("brand.sub"))
        self._about_btn.setToolTip(t("btn.about"))
        self._settings_btn.setToolTip(t("btn.settings"))
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

    # ---- arrastre de ventana sin marco --------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton \
                and event.position().y() <= 70:
            self._drag_pos = event.globalPosition().toPoint() \
                - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None \
                and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, _event) -> None:
        self._drag_pos = None
