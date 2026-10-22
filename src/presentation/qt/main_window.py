"""Ventana principal NetGauge (frameless, redondeada, con barra de título propia)."""
from __future__ import annotations

import html
import ipaddress
import sys
import time
from collections import deque

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
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
from .viewmodel import (
    AppRateTracker, AppRowData, filter_sort_apps, share_pct, trend_label, trend_pct)
from .widgets import (
    APP_COL_GAP, APP_COL_RATE, APP_COL_TOTAL, APP_ICON_PX, APP_ROW_BORDER, APP_ROW_PAD_X,
    AppRow, BarsLogo, ConnRow, LimitCard, LiveChart, MetricCard)

_UNITS = {"Auto": None, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
_TITLEBAR_H = 56
_PERIOD_CODES = ["session", "day", "week", "month"]
_SPARK_POINTS = 24
_SORT_CODES = ["total", "down", "up", "now"]


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


class NavTabs:
    """QTabBar suelto (vive en la fila de navegación) + QStackedWidget sincronizados.

    QTabWidget re-posiciona su barra en cada resize, así que no sirve para
    sacarla de su layout; esta API mínima cubre lo que usa MainWindow.
    """

    def __init__(self) -> None:
        self.bar = QTabBar()
        self.stack = QStackedWidget()
        self.bar.currentChanged.connect(self.stack.setCurrentIndex)

    def addTab(self, page: QWidget, text: str) -> None:
        self.stack.addWidget(page)
        self.bar.addTab(text)

    def currentIndex(self) -> int:
        return self.bar.currentIndex()

    def setCurrentIndex(self, i: int) -> None:
        self.bar.setCurrentIndex(i)

    def setTabText(self, i: int, text: str) -> None:
        self.bar.setTabText(i, text)


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
        self._apps_sort = "total"
        # Dos trackers (bajada/subida) sobre los acumulados de la sesión; se
        # alimentan sólo desde _tick (1 Hz) para que dt no dependa de cuántos
        # _refresh haya (búsqueda, orden, snapshots).
        self._recv_tracker = AppRateTracker()
        self._sent_tracker = AppRateTracker()
        self._rates_down: dict[str, float] = {}
        self._rates_up: dict[str, float] = {}
        self._clock = time.monotonic
        self._period_chips: list[tuple[QPushButton, str]] = []
        self._legends: list[tuple[QLabel, str]] = []
        self._legend_dashes: list[QLabel] = []
        # Un punto por refresco para las mini curvas de las tarjetas.
        self._spark_down: deque[float] = deque(maxlen=_SPARK_POINTS)
        self._spark_up: deque[float] = deque(maxlen=_SPARK_POINTS)
        self._spark_total: deque[float] = deque(maxlen=_SPARK_POINTS)
        self._maximized = False
        self._restore_geom = None
        self._native = False
        self._native_applied = False

        self.setWindowTitle("NetGauge")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(786, 720)
        # 680 = ancho que necesita la fila de navegación (pestañas + período +
        # unidad) sin solaparse; Qt sube a este mínimo cualquier geometría guardada menor.
        self.setMinimumSize(680, 360)
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
        body_lay.setContentsMargins(0, 14, 0, 0)
        body_lay.setSpacing(0)
        self._build_tabs()
        body_lay.addLayout(self._build_toolbar())
        rule = QFrame()
        rule.setObjectName("NavRule")
        rule.setFixedHeight(1)
        rule_lay = QHBoxLayout()
        rule_lay.setContentsMargins(20, 0, 20, 0)
        rule_lay.addWidget(rule)
        body_lay.addLayout(rule_lay)
        pages_lay = QVBoxLayout()
        pages_lay.setContentsMargins(20, 0, 20, 20)
        pages_lay.addWidget(self._tabs.stack)
        body_lay.addLayout(pages_lay, 1)
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
        if hasattr(self, "_search_action"):
            self._search_action.setIcon(svg_icon("search", color, 16))
        if hasattr(self, "_unit_chevron"):
            self._unit_chevron.setPixmap(
                svg_icon("chevron-down", color, 16).pixmap(16, 16))

    def _build_toolbar(self) -> QHBoxLayout:
        """Fila única: pestañas a la izquierda, período y unidad a la derecha."""
        lay = QHBoxLayout()
        self._nav_row = lay
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(8)

        bar = self._tabs.bar
        bar.setDrawBase(False)
        bar.setExpanding(False)
        bar.setUsesScrollButtons(False)
        bar.setFixedHeight(40)
        bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        lay.addWidget(bar, 0, Qt.AlignmentFlag.AlignBottom)
        lay.addStretch()

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
        lay.addWidget(seg, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(6)

        self._unit_caption = QLabel(t("unit.caption"))
        self._unit_caption.setObjectName("UnitCaption")
        lay.addWidget(self._unit_caption, 0, Qt.AlignmentFlag.AlignVCenter)

        self._unit_box = QComboBox()
        self._unit_box.setObjectName("UnitBox")
        self._unit_box.addItems(list(_UNITS.keys()))
        self._unit_box.setCurrentText(self._unit)
        self._unit_box.currentTextChanged.connect(self._set_unit)
        # El chevron es una capa sobre el combo: el QSS no dibuja SVG recoloreables.
        unit_wrap = QWidget()
        unit_grid = QGridLayout(unit_wrap)
        unit_grid.setContentsMargins(0, 0, 0, 0)
        unit_grid.addWidget(self._unit_box, 0, 0)
        self._unit_chevron = QLabel()
        self._unit_chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._unit_chevron.setFixedSize(16, 16)
        unit_grid.addWidget(self._unit_chevron, 0, 0,
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        unit_grid.setColumnMinimumWidth(0, 0)
        self._unit_box.setMinimumWidth(84)
        lay.addWidget(unit_wrap, 0, Qt.AlignmentFlag.AlignVCenter)
        return lay

    def _build_tabs(self) -> NavTabs:
        self._tabs = NavTabs()
        self._tabs.addTab(self._build_global_tab(), t("tab.global"))
        self._tabs.addTab(self._build_apps_tab(), t("tab.apps"))
        self._tabs.addTab(self._build_connections_tab(), t("tab.connections"))
        return self._tabs

    def _build_global_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(14)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self._card_down = MetricCard(self._theme, "down", t("card.download"))
        self._card_up = MetricCard(self._theme, "upload", t("card.upload"))
        self._card_total = MetricCard(self._theme, "total_fg", t("card.total"),
                                      is_total=True)
        for card in (self._card_down, self._card_up, self._card_total):
            cards.addWidget(card, 1)
        lay.addLayout(cards)

        chart_card = QFrame()
        self._chart_card = chart_card
        chart_card.setObjectName("ChartCard")
        cc = QVBoxLayout(chart_card)
        cc.setContentsMargins(14, 14, 14, 14)
        cc.setSpacing(10)
        head = QHBoxLayout()
        self._chart_title = QLabel(t("chart.title"))
        self._chart_title.setObjectName("SectionTitle")
        head.addWidget(self._chart_title)
        head.addSpacing(10)
        self._peak_chip = QLabel(t("chart.peak", v="0 B"))
        self._peak_chip.setObjectName("Chip")
        head.addWidget(self._peak_chip)
        head.addStretch()
        head.addWidget(self._legend(t("legend.download"), "down"))
        head.addSpacing(8)
        head.addWidget(self._legend(t("legend.upload"), "upload"))
        cc.addLayout(head)
        self._chart = LiveChart(self._theme)
        cc.addWidget(self._chart, 1)
        lay.addWidget(chart_card, 1)

        chart_card.setMinimumHeight(170)  # el gráfico no se aplasta a 0 en alto chico

        limits = QHBoxLayout()
        limits.setSpacing(14)
        self._daily_card = LimitCard(self._theme)
        self._month_card = LimitCard(self._theme)
        for card in (self._daily_card, self._month_card):
            card.define_clicked.connect(lambda: self._open_quota())
            limits.addWidget(card, 1)
        lay.addLayout(limits)

        # Scrollable: si la ventana queda baja, no se corta el ancho de banda.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        return scroll

    def _legend(self, text: str, color_key: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        dash = QLabel()
        dash.setFixedSize(14, 3)
        dash.setProperty("color_key", color_key)
        dash.setStyleSheet(f"background:{self._theme[color_key]}; border-radius:1px;")
        lbl = QLabel(text)
        lbl.setObjectName("LegendText")
        lay.addWidget(dash)
        lay.addWidget(lbl)
        # recordamos la clave (download/upload) por orden de creación
        key = "legend.download" if not self._legends else "legend.upload"
        self._legends.append((lbl, key))
        self._legend_dashes.append(dash)
        return w

    def _build_apps_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        tools = QHBoxLayout()
        tools.setContentsMargins(0, 14, 0, 8)
        tools.setSpacing(8)
        self._apps_search = QLineEdit()
        self._apps_search.setObjectName("AppsSearch")
        self._apps_search.setPlaceholderText(t("apps.search"))
        self._apps_search.setFixedHeight(38)
        self._search_action = self._apps_search.addAction(
            svg_icon("search", self._theme["text_muted"], 16),
            QLineEdit.ActionPosition.LeadingPosition)
        self._apps_search.textChanged.connect(lambda _t: self._refresh())
        tools.addWidget(self._apps_search, 1)
        tools.addSpacing(6)
        self._sort_caption = QLabel(t("apps.sort"))
        self._sort_caption.setObjectName("SortCaption")
        tools.addWidget(self._sort_caption)
        self._sort_group = QButtonGroup(self)
        self._sort_group.setExclusive(True)
        self._sort_chips: dict[str, QPushButton] = {}
        for code in _SORT_CODES:
            chip = QPushButton(t("apps.sort." + code))
            chip.setObjectName("SortChip")
            chip.setCheckable(True)
            chip.setFixedHeight(32)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setChecked(code == self._apps_sort)
            chip.clicked.connect(lambda _c, c=code: self._set_apps_sort(c))
            self._sort_group.addButton(chip)
            self._sort_chips[code] = chip
            tools.addWidget(chip)
        outer.addLayout(tools)

        # Cabecera alineada con las columnas de AppRow (mismos anchos y márgenes).
        self._apps_header = QWidget()
        self._apps_header.setObjectName("AppsHeader")
        self._header_lay = QHBoxLayout(self._apps_header)
        self._header_pad = APP_ROW_BORDER + APP_ROW_PAD_X
        self._header_lay.setContentsMargins(self._header_pad, 0, self._header_pad, 4)
        self._header_lay.setSpacing(APP_COL_GAP)
        self._col_app = QLabel(t("apps.col.app"))
        self._col_now = QLabel(t("apps.col.now"))
        self._col_total = QLabel(t("apps.col.total"))
        spacer = QWidget()
        spacer.setFixedWidth(APP_ICON_PX)
        self._header_lay.addWidget(spacer)
        self._header_lay.addWidget(self._col_app, 1)
        for lbl, width in ((self._col_now, APP_COL_RATE), (self._col_total, APP_COL_TOTAL)):
            lbl.setFixedWidth(width)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            self._header_lay.addWidget(lbl)
        outer.addWidget(self._apps_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._apps_scroll = scroll
        self._apps_container = QWidget()
        self._apps_container.setObjectName("AppsContainer")
        self._apps_lay = QVBoxLayout(self._apps_container)
        self._apps_lay.setContentsMargins(0, 0, 0, 0)
        self._apps_lay.setSpacing(4)
        self._apps_empty = QLabel("")
        self._apps_empty.setObjectName("AppsEmpty")
        self._apps_empty.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._apps_empty.setTextFormat(Qt.TextFormat.PlainText)  # contiene lo que tipeó el usuario
        self._apps_empty.setContentsMargins(0, 40, 0, 0)
        self._apps_empty.hide()
        self._apps_lay.addWidget(self._apps_empty)
        self._apps_lay.addStretch()
        scroll.setWidget(self._apps_container)
        # La barra de scroll come ancho sólo de las filas: la cabecera lo compensa.
        scroll.verticalScrollBar().rangeChanged.connect(lambda *_: self._sync_header_pad())
        outer.addWidget(scroll, 1)
        return page

    def _sync_header_pad(self) -> None:
        sb = self._apps_scroll.verticalScrollBar()
        extra = sb.sizeHint().width() if sb.maximum() > 0 else 0
        self._header_lay.setContentsMargins(self._header_pad, 0, self._header_pad + extra, 4)

    def _set_apps_sort(self, code: str) -> None:
        self._apps_sort = code
        self._refresh()

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

        self._spark_down.append(tot_recv)
        self._spark_up.append(tot_sent)
        self._spark_total.append(total)

        prev = (None if self._period == "session"
                else self._monitor.previous_period_breakdown(self._period))
        prev_sent, prev_recv = prev if prev else (None, None)

        v, u = _fmt(tot_recv, self._unit)
        self._card_down.set_values(
            v, u, t("card.pct_of_total", p=f"{share_pct(tot_recv, total):.0f}"),
            *self._trend_text(tot_recv, prev_recv), spark=list(self._spark_down))
        v, u = _fmt(tot_sent, self._unit)
        self._card_up.set_values(
            v, u, t("card.pct_of_total", p=f"{share_pct(tot_sent, total):.0f}"),
            *self._trend_text(tot_sent, prev_sent), spark=list(self._spark_up))
        v, u = _fmt(total, self._unit)
        label, level = self._period_trend(total)
        self._card_total.set_values(
            v, u, t("card.peak", v=loc_bytes(self._chart.peak())),
            label, level, list(self._spark_total))

        self._set_limit(self._daily_card, self._monitor.daily_status(),
                        "quota.daily", "limit.daily")
        self._set_limit(self._month_card, self._monitor.quota_status(),
                        "quota.monthly", "limit.monthly")

        self._rebuild_apps(rows, total)
        self._refresh_connections()

    def _trend_text(self, current: float, previous: float | None) -> tuple[str, str]:
        """Rótulo de tendencia vs el período previo; ("", "none") si no hay."""
        text, level = trend_label(trend_pct(current, previous))
        if not text:
            return "", "none"
        return t("card.vs_prev", p=text, prev=t("card.prev." + self._period)), level

    def _period_trend(self, total: float) -> tuple[str, str]:
        """(texto, nivel) del rótulo derecho de la tarjeta Total: tendencia contra
        el período previo, o el nombre del período si no hay con qué comparar."""
        if self._period == "session":
            return t("card.this_session"), "flat"
        prev = self._monitor.previous_period_total(self._period)
        text, level = self._trend_text(total, prev)
        return (text, level) if text else (t("period." + self._period), "flat")

    @staticmethod
    def _set_limit(card: LimitCard, status, title_key: str, empty_key: str) -> None:
        if status.has_limit:
            used = (f"{loc_bytes(status.used_bytes)} / {loc_bytes(status.limit_bytes)}"
                    f" · {status.percent:.0f} %")
            hint = ("limit.hint_reached" if status.percent >= 100
                    else "limit.hint_over" if status.percent >= 80 else "limit.hint_80")
            card.set_state(t(title_key), used, status.percent, True, t(hint))
        else:
            card.set_state(t(empty_key), "", 0, False, t("limit.none"))

    def _connection_counts(self) -> dict[str, int]:
        """Conexiones por app desde el snapshot (sin I/O); sólo con la pestaña visible,
        porque connections() marca demanda y despierta la enumeración del worker."""
        if self._tabs.currentIndex() != 1:
            return {}
        counts: dict[str, int] = {}
        for c in self._monitor.connections():
            counts[c.app_name] = counts.get(c.app_name, 0) + 1
        return counts

    def _conns_text(self, n: int) -> str:
        if n <= 0:
            return ""
        return t("apps.conn_one") if n == 1 else t("apps.conns", n=n)

    def _rebuild_apps(self, rows, total) -> None:
        """Reconciliación in-place: reutiliza filas, no las recrea cada segundo.

        Las apps que ya no existen se destruyen; las que sólo no pasan el filtro
        de búsqueda se OCULTAN (siguen en _app_rows) y quedan tras las visibles.
        """
        data = [AppRowData(name, sent, recv,
                           self._rates_down.get(name, 0.0) + self._rates_up.get(name, 0.0))
                for name, sent, recv in rows]
        shown = filter_sort_apps(data, self._apps_search.text(), self._apps_sort)
        existing = {r.name for r in data}

        for name in list(self._app_rows):
            if name not in existing:
                row = self._app_rows.pop(name)
                self._apps_lay.removeWidget(row)
                row.deleteLater()

        query = self._apps_search.text().strip()
        self._apps_empty.setText(t("apps.no_results", q=query) if query else "")
        self._apps_empty.setVisible(bool(query) and not shown and bool(data))

        counts = self._connection_counts()
        top_total = max((r.total for r in shown), default=0)
        for i, r in enumerate(shown):
            row = self._app_rows.get(r.name)
            if row is None:
                row = AppRow(self._theme, r.name)
                self._app_rows[r.name] = row
            if self._apps_lay.indexOf(row) != i:
                self._apps_lay.removeWidget(row)
                self._apps_lay.insertWidget(i, row)
            if row.isHidden():
                row.show()
            vt, ut = _fmt(r.total, self._unit)
            rate_text = (f"↓ {loc_bytes(self._rates_down.get(r.name, 0.0))}/s\n"
                         f"↑ {loc_bytes(self._rates_up.get(r.name, 0.0))}/s")
            row.update_data(
                f"{vt} {ut}", rate_text, f"{share_pct(r.total, total):.0f} %",
                (r.total / top_total * 100) if top_total else 0,
                self._conns_text(counts.get(r.name, 0)), active=(i == 0))
            row.set_icon(self._monitor.exe_path_for(r.name))
            info = self._monitor.trust_for(r.name)
            row.set_trust(info.level, self._trust_tooltip(info))
            row.set_vt_badge(info.vt_malicious, info.vt_total,
                             self._vt_badge_tooltip(info))
        shown_names = {r.name for r in shown}
        for name, row in self._app_rows.items():
            if name not in shown_names and not row.isHidden():
                row.hide()

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
        self._update_app_rates()

    def _update_app_rates(self) -> None:
        """Velocidad por app: delta de los acumulados de sesión entre ticks (1 Hz)."""
        usage = self._monitor.session_usage()
        now = self._clock()
        self._rates_down = self._recv_tracker.update({u.app_name: u.bytes_recv for u in usage}, now)
        self._rates_up = self._sent_tracker.update({u.app_name: u.bytes_sent for u in usage}, now)

    # ---- acciones ------------------------------------------------------
    def _set_period(self, value: str) -> None:
        self._period = value
        for spark in (self._spark_down, self._spark_up, self._spark_total):
            spark.clear()  # escalas distintas por período: no mezclar curvas
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
        self._unit_caption.setText(t("unit.caption"))
        for chip, value in self._period_chips:
            chip.setText(t("period." + value))
        self._tabs.setTabText(0, t("tab.global"))
        self._tabs.setTabText(1, t("tab.apps"))
        self._tabs.setTabText(2, t("tab.connections"))
        self._card_down.set_name(t("card.download"))
        self._card_up.set_name(t("card.upload"))
        self._card_total.set_name(t("card.total"))
        self._chart_title.setText(t("chart.title"))
        for card in (self._daily_card, self._month_card):
            card.retranslate()
        for lbl, key in self._legends:
            lbl.setText(t(key))
        self._apps_search.setPlaceholderText(t("apps.search"))
        self._sort_caption.setText(t("apps.sort"))
        for code, chip in self._sort_chips.items():
            chip.setText(t("apps.sort." + code))
        self._col_app.setText(t("apps.col.app"))
        self._col_now.setText(t("apps.col.now"))
        self._col_total.setText(t("apps.col.total"))
        self._conn_subtitle.setText(t("conn.subtitle"))
        self._hide_local_cb.setText(t("conn.hide_localhost"))

    def _toggle_theme(self) -> None:
        self._dark = not self._dark
        self._theme = DARK if self._dark else LIGHT
        self._apply_theme()
        self._chart.set_theme(self._theme)
        for card in (self._card_down, self._card_up, self._card_total):
            card.set_theme(self._theme)
        for card in (self._daily_card, self._month_card):
            card.set_theme(self._theme)
        for dash in self._legend_dashes:
            dash.setStyleSheet(
                f"background:{self._theme[dash.property('color_key')]}; border-radius:1px;")
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
