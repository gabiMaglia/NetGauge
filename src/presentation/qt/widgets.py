"""Widgets custom dibujados con QPainter para fidelidad pixel-perfect."""
from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...domain.models import (
    TRUST_CAUTION,
    TRUST_SUSPICIOUS,
    TRUST_TRUSTED,
    human_bytes,
)
from .i18n import fmt_number, loc_bytes, t
from .theme import MONO_FAMILY

_GRAPH_POINTS = 60
_AXIS_UNITS = ((1024**3, "GB"), (1024**2, "MB"), (1024, "KB"), (1, "B"))


def _nice_step(x: float) -> float:
    """Menor paso 1/2/5 x 10^n que es >= x."""
    if x <= 0:
        return 1.0
    base = 10.0 ** math.floor(math.log10(x))
    for mult in (1, 2, 5, 10):
        if mult * base >= x:
            return mult * base
    return 10 * base


def nice_ticks(peak: float) -> list[float]:
    """Cinco marcas del eje Y (0, 1/4, 1/2, 3/4, tope) con paso 1/2/5 x 10^n."""
    step = _nice_step(max(peak, 1024.0) / 4)
    return [k * step for k in range(5)]


def _mono_font(px: int, bold: bool = False) -> QFont:
    f = QFont()
    f.setFamilies([n.strip().strip('"') for n in MONO_FAMILY.split(",")])
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def _axis(peak: float) -> tuple[list[float], list[str]]:
    """Marcas en bytes y sus etiquetas; la unidad va sólo en la etiqueta superior."""
    top = max(peak, 1024.0)
    div, unit = next((d, u) for d, u in _AXIS_UNITS if top >= d)
    step_u = _nice_step(top / div / 4)
    decimals = 0 if step_u >= 1 and float(step_u).is_integer() else 1
    ticks, labels = [], []
    for k in range(5):
        ticks.append(k * step_u * div)
        text = "0" if k == 0 else fmt_number(k * step_u, decimals, group=False)
        labels.append(f"{text} {unit}" if k == 4 else text)
    return ticks, labels


class LiveChart(QWidget):
    """Gráfico en vivo con ejes, degradé bajo la bajada y tooltip al pasar el mouse."""

    _PAD_TOP = 8
    _PAD_BOTTOM = 24
    _PAD_RIGHT = 8

    def __init__(self, theme: dict) -> None:
        super().__init__()
        self._t = theme
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._down = deque([0.0] * _GRAPH_POINTS, maxlen=_GRAPH_POINTS)
        self._up = deque([0.0] * _GRAPH_POINTS, maxlen=_GRAPH_POINTS)
        self._window_s = _GRAPH_POINTS
        self._hover: int | None = None

    def set_theme(self, theme: dict) -> None:
        self._t = theme
        self.update()

    def set_window_seconds(self, n: int) -> None:
        self._window_s = max(1, int(n))
        self.update()

    def push(self, up: float, down: float) -> None:
        self._up.append(up)
        self._down.append(down)
        self.update()

    def peak(self) -> float:
        return max(max(self._up), max(self._down))

    def hover_index(self) -> int | None:
        return self._hover

    def value_at(self, i: int) -> tuple[float, float]:
        """(bajada, subida) del punto i (0 = el más viejo, 59 = el último push)."""
        return self._down[i], self._up[i]

    # ---- geometría ----------------------------------------------------
    def _plot_rect(self, label_w: float) -> QRectF:
        left = max(52.0, label_w + 12)
        return QRectF(left, self._PAD_TOP,
                      max(1.0, self.width() - left - self._PAD_RIGHT),
                      max(1.0, self.height() - self._PAD_TOP - self._PAD_BOTTOM))

    def _label_width(self) -> float:
        _, labels = _axis(self.peak())
        fm = QFontMetrics(_mono_font(12))
        return float(max(fm.horizontalAdvance(s) for s in labels))

    def mouseMoveEvent(self, event) -> None:
        plot = self._plot_rect(self._label_width())
        x = event.position().x()
        if x < plot.left() or x > plot.right():
            idx = None
        else:
            n = len(self._down)
            idx = round((x - plot.left()) / plot.width() * (n - 1))
            idx = max(0, min(n - 1, idx))
        if idx != self._hover:
            self._hover = idx
            self.update()

    def leaveEvent(self, _event) -> None:
        if self._hover is not None:
            self._hover = None
            self.update()

    # ---- pintado --------------------------------------------------------
    def _points(self, data, plot: QRectF, top: float) -> list[QPointF]:
        n = len(data)
        return [QPointF(plot.left() + i * plot.width() / (n - 1),
                        plot.bottom() - min(v / top, 1.0) * plot.height())
                for i, v in enumerate(data)]

    @staticmethod
    def _poly(pts: list[QPointF]) -> QPainterPath:
        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        return path

    def _time_labels(self) -> tuple[str, str, str]:
        w = self._window_s

        def fmt(sec: int) -> str:
            if sec >= 60 and sec % 60 == 0:
                return t("chart.axis.minutes", n=sec // 60)
            return t("chart.axis.seconds", n=sec)
        return fmt(w), fmt(w // 2), t("chart.axis.now")

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ticks, labels = _axis(self.peak())
        top = ticks[-1]
        mono = _mono_font(12)
        fm = QFontMetrics(mono)
        plot = self._plot_rect(float(max(fm.horizontalAdvance(s) for s in labels)))

        # Grilla + etiquetas del eje Y
        p.setFont(mono)
        for tick, label in zip(ticks, labels):
            y = round(plot.bottom() - tick / top * plot.height()) + 0.5
            p.setPen(QPen(QColor(self._t["grid_line"]), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(self._t["text_muted"]))
            p.drawText(QRectF(0, y - 9, plot.left() - 8, 18),
                       int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                       label)

        # Etiquetas de tiempo
        left_t, mid_t, right_t = self._time_labels()
        ty = plot.bottom() + 5
        p.drawText(QRectF(plot.left(), ty, 90, 16),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), left_t)
        p.drawText(QRectF(plot.center().x() - 45, ty, 90, 16),
                   int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter), mid_t)
        p.drawText(QRectF(plot.right() - 90, ty, 90, 16),
                   int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), right_t)

        down_pts = self._points(self._down, plot, top)
        up_pts = self._points(self._up, plot, top)

        # Degradé sólo bajo la bajada
        area = self._poly(down_pts)
        area.lineTo(plot.right(), plot.bottom())
        area.lineTo(plot.left(), plot.bottom())
        area.closeSubpath()
        grad = QLinearGradient(0, plot.top(), 0, plot.bottom())
        fill = QColor(self._t["down"])
        fill.setAlphaF(0.35)
        grad.setColorAt(0.0, fill)
        fill.setAlpha(0)
        grad.setColorAt(1.0, fill)
        p.fillPath(area, QBrush(grad))

        for pts, key in ((down_pts, "down"), (up_pts, "upload")):
            pen = QPen(QColor(self._t[key]), 2.4)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawPath(self._poly(pts))

        if self._hover is not None:
            self._paint_tooltip(p, plot, down_pts[self._hover], self._hover)
        p.end()

    def _paint_tooltip(self, p: QPainter, plot: QRectF, pt: QPointF, i: int) -> None:
        guide = QPen(QColor(self._t["dashed_bd"]), 1, Qt.PenStyle.DashLine)
        p.setPen(guide)
        p.drawLine(QPointF(pt.x(), plot.top()), QPointF(pt.x(), plot.bottom()))
        p.setPen(QPen(QColor(self._t["window_bg"]), 2))
        p.setBrush(QColor(self._t["down"]))
        p.drawEllipse(pt, 4.0, 4.0)

        down, up = self.value_at(i)
        n = len(self._down)
        ago = round((n - 1 - i) * self._window_s / (n - 1))
        lines = (t("chart.hover.ago", n=ago),
                 f"↓ {loc_bytes(down)}/s   ↑ {loc_bytes(up)}/s")
        font = _mono_font(12)
        fm = QFontMetrics(font)
        w = max(fm.horizontalAdvance(s) for s in lines) + 20
        h = 2 * fm.height() + 14
        x = pt.x() + 12
        if x + w > self.width() - 4:
            x = pt.x() - 12 - w
        x = max(4.0, x)
        y = min(max(plot.top(), pt.y() - h / 2), self.height() - h - 4)
        box = QRectF(x, y, w, h)
        p.setPen(QPen(QColor(self._t["dashed_bd"]), 1))
        p.setBrush(QColor(self._t["track"]))
        p.drawRoundedRect(box, 8, 8)
        p.setFont(font)
        p.setPen(QColor(self._t["text_muted"]))
        p.drawText(QRectF(x + 10, y + 6, w - 20, fm.height()),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), lines[0])
        p.setPen(QColor(self._t["text"]))
        p.drawText(QRectF(x + 10, y + 6 + fm.height(), w - 20, fm.height()),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), lines[1])


class QuotaBar(QWidget):
    """Track + chunk con gradiente (azul o ámbar/rojo según %)."""

    def __init__(self, theme: dict, warn: bool = False) -> None:
        super().__init__()
        self._t = theme
        self._warn = warn
        self._pct = 0.0
        self.setFixedHeight(9)

    def set_theme(self, theme: dict) -> None:
        self._t = theme
        self.update()

    def set_percent(self, pct: float) -> None:
        self._pct = max(0.0, pct)
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        r = h / 2

        track = QPainterPath()
        track.addRoundedRect(QRectF(0, 0, w, h), r, r)
        p.fillPath(track, QColor(self._t["track"]))

        if self._pct <= 0:
            p.end()
            return
        fw = w * min(self._pct, 100) / 100
        chunk = QPainterPath()
        chunk.addRoundedRect(QRectF(0, 0, max(fw, h), h), r, r)
        grad = QLinearGradient(0, 0, fw, 0)
        if self._pct >= 100:
            grad.setColorAt(0, QColor(self._t["danger"]))
            grad.setColorAt(1, QColor("#f87171"))
        elif self._warn or self._pct >= 80:
            grad.setColorAt(0, QColor(self._t["warning"]))
            grad.setColorAt(1, QColor(self._t["warning_2"]))
        else:
            grad.setColorAt(0, QColor(self._t["accent_strong"]))
            grad.setColorAt(1, QColor(self._t["accent"]))
        p.fillPath(chunk, QBrush(grad))
        p.end()


class _Spark(QWidget):
    """Mini curva (polilínea de 2 px) a todo el ancho de la tarjeta."""

    def __init__(self, color: str) -> None:
        super().__init__()
        self._color = color
        self._vals: list[float] = []
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def set_values(self, vals: list[float] | None) -> None:
        self._vals = list(vals or [])[-24:]
        self.update()

    def paintEvent(self, _event) -> None:
        if len(self._vals) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        lo, hi = min(self._vals), max(self._vals)
        span = hi - lo
        step = w / (len(self._vals) - 1)
        path = QPainterPath()
        for i, v in enumerate(self._vals):
            frac = (v - lo) / span if span > 0 else 0.5  # serie plana: línea al medio
            pt = QPointF(i * step, h - 2 - frac * (h - 4))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        pen = QPen(QColor(self._color), 2)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(path)
        p.end()


class MetricCard(QFrame):
    """Tarjeta de métrica: punto + nombre + tendencia, número hero + unidad,
    mini curva y subtexto."""

    def __init__(self, theme: dict, color_key: str, name: str,
                 is_total: bool = False) -> None:
        super().__init__()
        self.setObjectName("TotalCard" if is_total else "Card")
        self._t = theme
        self._color_key = color_key
        self._is_total = is_total
        self._trend_level = "none"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(7)
        self._dot: QLabel | None = None
        if not is_total:
            self._dot = QLabel()
            self._dot.setFixedSize(9, 9)
            top.addWidget(self._dot)
        self._name = QLabel(name)
        self._name.setObjectName("TotalName" if is_total else "MetricName")
        top.addWidget(self._name)
        top.addStretch()
        self._trend = QLabel("")
        self._trend.setObjectName("MetricTrend")
        self._trend.setProperty("level", "none")
        top.addWidget(self._trend)
        lay.addLayout(top)

        hero = QHBoxLayout()
        hero.setSpacing(5)
        hero.setContentsMargins(0, 0, 0, 0)
        self._value = QLabel("0.0")
        self._value.setObjectName("MetricHero")
        self._unit = QLabel("B")
        self._unit.setObjectName("TotalUnit" if is_total else "MetricUnit")
        hero.addWidget(self._value)
        hero.addWidget(self._unit, 0, Qt.AlignmentFlag.AlignBottom)
        hero.addStretch()
        lay.addLayout(hero)

        self._spark = _Spark(theme[color_key])
        lay.addWidget(self._spark)

        self._sub = QLabel("")
        self._sub.setObjectName("TotalSub" if is_total else "MetricSub")
        lay.addWidget(self._sub)
        self.set_theme(theme)

    def set_theme(self, theme: dict) -> None:
        self._t = theme
        color = theme[self._color_key]
        if self._dot is not None:
            self._dot.setStyleSheet(f"background:{color}; border-radius:4px;")
        self._spark.set_color(color)

    def set_values(self, value_text: str, unit_text: str, sub: str,
                   trend_text: str = "", trend_level: str = "none",
                   spark: list[float] | None = None) -> None:
        self._value.setText(value_text)
        self._unit.setText(unit_text)
        self._sub.setText(sub)
        self._trend.setText(trend_text)
        if trend_level != self._trend_level:
            self._trend_level = trend_level
            self._trend.setProperty("level", trend_level)
            self._trend.style().unpolish(self._trend)
            self._trend.style().polish(self._trend)
        self._spark.set_values(spark)

    def trend_text(self) -> str:
        return self._trend.text()

    def set_name(self, name: str) -> None:
        self._name.setText(name)


class _LevelBar(QWidget):
    """Barra de 8 px: pista oscura y trozo del color del nivel (ok/warn/danger)."""

    def __init__(self, theme: dict) -> None:
        super().__init__()
        self._t = theme
        self._pct = 0.0
        self._level = "ok"
        self.setFixedHeight(8)

    def set_theme(self, theme: dict) -> None:
        self._t = theme
        self.update()

    def set_state(self, pct: float, level: str) -> None:
        self._pct = max(0.0, pct)
        self._level = level
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        track = QPainterPath()
        track.addRoundedRect(QRectF(0, 0, w, h), 5, 5)
        p.fillPath(track, QColor(self._t["track"]))
        if self._pct > 0:
            key = {"ok": "accent", "warn": "warning", "danger": "danger"}.get(
                self._level, "accent")
            chunk = QPainterPath()
            chunk.addRoundedRect(QRectF(0, 0, max(w * min(self._pct, 100) / 100, h), h), 5, 5)
            p.fillPath(chunk, QColor(self._t[key]))
        p.end()


class LimitCard(QFrame):
    """Límite de consumo: con límite muestra valor, barra por nivel y aviso;
    sin límite, borde punteado y botón para definirlo."""

    define_clicked = Signal()

    def __init__(self, theme: dict) -> None:
        super().__init__()
        self.setObjectName("LimitCard")
        self._level = "empty"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        self._title = QLabel("")
        self._title.setObjectName("LimitTitle")
        head.addWidget(self._title)
        head.addStretch()
        self._value = QLabel("")
        self._value.setObjectName("LimitValue")
        self._value.setProperty("level", "ok")
        head.addWidget(self._value)
        lay.addLayout(head)

        self._bar = _LevelBar(theme)
        lay.addWidget(self._bar)

        foot = QHBoxLayout()
        self._hint = QLabel("")
        self._hint.setObjectName("LimitHint")
        self._hint.setWordWrap(True)
        foot.addWidget(self._hint, 1)
        self._edit = QPushButton(t("limit.edit"))
        self._edit.setObjectName("LimitEditBtn")
        self._edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit.clicked.connect(self.define_clicked)
        foot.addWidget(self._edit)
        lay.addLayout(foot)

        self._define = QPushButton(t("limit.define"))
        self._define.setObjectName("LimitDefineBtn")
        self._define.setCursor(Qt.CursorShape.PointingHandCursor)
        self._define.setFixedHeight(36)
        self._define.clicked.connect(self.define_clicked)
        lay.addWidget(self._define)
        self.setProperty("state", "empty")

    def retranslate(self) -> None:
        self._edit.setText(t("limit.edit"))
        self._define.setText(t("limit.define"))

    def set_theme(self, theme: dict) -> None:
        self._bar.set_theme(theme)

    def level(self) -> str:
        return self._level

    @staticmethod
    def _level_for(percent: float) -> str:
        return "danger" if percent >= 100 else "warn" if percent >= 80 else "ok"

    def set_state(self, label: str, used_text: str, percent: float,
                  has_limit: bool, hint: str) -> None:
        level = self._level_for(percent) if has_limit else "empty"
        self._title.setText(label)
        self._hint.setText(hint)
        self._value.setText(used_text)
        self._value.setVisible(has_limit)
        self._bar.setVisible(has_limit)
        self._edit.setVisible(has_limit)
        self._define.setVisible(not has_limit)
        self._bar.set_state(percent, level)
        if level != self._level:
            self._level = level
            for w, name in ((self, "state"), (self._value, "level")):
                w.setProperty(name, level)
                w.style().unpolish(w)
                w.style().polish(w)


class AppRow(QFrame):
    """Fila de la vista Por aplicación: ícono + nombre + barra + totales.

    Se REUTILIZA: en vez de recrear la fila en cada refresco, se actualiza
    in-place con update_data(). Esto evita churn de widgets/memoria por segundo.
    """

    def __init__(self, theme: dict, name: str) -> None:
        super().__init__()
        self._t = theme
        self._name = name
        self.setObjectName("AppRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 14, 9)
        lay.setSpacing(13)

        self._badge = QLabel()
        self._badge.setFixedSize(36, 36)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._style_badge()
        lay.addWidget(self._badge)

        center = QVBoxLayout()
        center.setSpacing(6)
        self._nm = QLabel(name)
        self._nm.setTextFormat(Qt.TextFormat.PlainText)  # el nombre viene del SO
        self._nm.setObjectName("AppName")
        center.addWidget(self._nm)
        self._bar = QuotaBar(theme)
        self._bar.setFixedHeight(6)
        center.addWidget(self._bar)
        lay.addLayout(center, 1)

        # Slot de confianza: SIEMPRE reserva 22px (aunque no haya badge) para
        # que la columna quede alineada entre filas.
        self._trust = QLabel()
        self._trust.setFixedSize(22, 22)
        self._trust.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._trust)

        # Badge ADICIONAL específico de VirusTotal: independiente del de
        # confianza local. Solo se pinta cuando VT efectivamente analizó la
        # app (vt_total truthy); si está deshabilitado/sin key queda vacío.
        self._vt_badge = QLabel()
        self._vt_badge.setFixedSize(16, 16)
        self._vt_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._vt_badge)

        # Columna de totales de ancho FIJO: así la barra mide igual en todas las
        # filas (no depende del largo del número) y todo queda en escuadra.
        right_w = QWidget()
        right_w.setFixedWidth(128)
        right = QVBoxLayout(right_w)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(3)
        self._tot = QLabel("")
        self._tot.setObjectName("AppTotal")
        self._tot.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._sp = QLabel("")
        self._sp.setObjectName("AppSplit")
        self._sp.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self._tot)
        right.addWidget(self._sp)
        lay.addWidget(right_w)

    def update_data(self, total: str, split: str, pct: float,
                    active: bool = False) -> None:
        self._tot.setText(total)
        self._sp.setText(split)
        self._bar.set_percent(pct)
        name = "AppRowActive" if active else "AppRow"
        if self.objectName() != name:
            self.setObjectName(name)
            self.style().unpolish(self)
            self.style().polish(self)

    _TRUST_STYLE = {
        TRUST_TRUSTED: ("#10b981", "✓"),
        TRUST_CAUTION: ("#f59e0b", "!"),
        TRUST_SUSPICIOUS: ("#ef4444", "⚠"),
    }

    def set_trust(self, level: str, tooltip: str) -> None:
        style = self._TRUST_STYLE.get(level)
        if style is None:  # sin dato: slot vacío pero el espacio queda reservado
            self._trust.setText("")
            self._trust.setToolTip("")
            self._trust.setStyleSheet("background:transparent; border:none;")
            return
        color, sym = style
        self._trust.setText(sym)
        self._trust.setToolTip(tooltip)
        self._trust.setStyleSheet(
            f"color:{color}; background:rgba(0,0,0,0); border:1.5px solid {color};"
            f"border-radius:11px; font-size:12px; font-weight:800;")

    def set_vt_badge(self, vt_malicious: int | None, vt_total: int | None,
                     tooltip: str = "") -> None:
        """Badge de "analizado por VT": verde=limpio, rojo=detectado,
        sin pintar si VT no analizó esta app (deshabilitado o sin key)."""
        if not vt_total:
            self._vt_badge.setText("")
            self._vt_badge.setToolTip("")
            self._vt_badge.setStyleSheet("background:transparent; border:none;")
            return
        malicious = vt_malicious or 0
        color = "#ef4444" if malicious > 0 else "#10b981"
        self._vt_badge.setText("V")
        self._vt_badge.setToolTip(tooltip)
        self._vt_badge.setStyleSheet(
            f"color:white; background:{color}; border-radius:8px;"
            f"font-size:8px; font-weight:800;")

    def _style_badge(self) -> None:
        icon = _app_icon(self._name, self._t)
        self._badge.setText(icon["letter"])
        self._badge.setStyleSheet(
            f"background:{icon['bg']}; color:{icon['fg']}; border-radius:11px;"
            f"font-size:16px; font-weight:800;")

    def set_theme(self, theme: dict) -> None:
        self._t = theme
        self._bar.set_theme(theme)
        self._style_badge()


class ConnRow(QFrame):
    """Fila de conexión reutilizable: app · (geo) · ip:puerto · estado."""

    def __init__(self, app_name: str, remote: str, status: str) -> None:
        super().__init__()
        self.setObjectName("AppRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(10)
        self._app = QLabel(app_name)
        self._app.setTextFormat(Qt.TextFormat.PlainText)  # el nombre viene del SO
        self._app.setObjectName("AppName")
        lay.addWidget(self._app)
        self._geo = QLabel("")
        self._geo.setTextFormat(Qt.TextFormat.PlainText)  # texto de ip-api: no confiable
        self._geo.setObjectName("AppSplit")
        lay.addWidget(self._geo)
        lay.addStretch()
        rem = QLabel(remote)
        rem.setObjectName("AppTotal")
        lay.addWidget(rem)
        st = QLabel(status)
        st.setObjectName("Chip")
        lay.addWidget(st)

    def set_geo(self, text: str) -> None:
        self._geo.setText(text)


def _paint_bars(p: QPainter, w: float, h: float, radius: float) -> None:
    """Dibuja el logo de marca (cuadrado azul + 3 barras blancas) en (0,0,w,h)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QPainterPath()
    bg.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    bgrad = QLinearGradient(0, 0, w, h)
    bgrad.setColorAt(0, QColor("#3b82f6"))
    bgrad.setColorAt(1, QColor("#2563eb"))
    p.fillPath(bg, QBrush(bgrad))
    p.setBrush(QColor(255, 255, 255, 235))
    p.setPen(Qt.PenStyle.NoPen)
    bw = w * 0.13
    gap = w * 0.10
    base_y = h * 0.74
    x = w * 0.24
    for top_frac in (0.56, 0.40, 0.24):
        top = h * top_frac
        p.drawRoundedRect(QRectF(x, top, bw, base_y - top), w * 0.03, w * 0.03)
        x += bw + gap


class BarsLogo(QWidget):
    """Logo de la marca: tres barras con gradiente azul, igual que el .ico."""

    def __init__(self, size: int = 26, radius: int = 8) -> None:
        super().__init__()
        self._r = radius
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        _paint_bars(p, float(self.width()), float(self.height()), self._r)
        p.end()


def make_app_qicon() -> QIcon:
    """QIcon multi-tamaño con el logo de marca (para ventana/diálogos/tray)."""
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(s, s)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        _paint_bars(p, float(s), float(s), max(2.0, s * 0.22))
        p.end()
        icon.addPixmap(pix)
    return icon


def make_sparkline_icon(values: list[float], accent: str = "#3b82f6") -> QIcon:
    """Ícono de tray con un mini-gráfico (sparkline) del tráfico reciente."""
    s = 64
    pix = QPixmap(s, s)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QPainterPath()
    bg.addRoundedRect(QRectF(0, 0, s, s), 14, 14)
    p.fillPath(bg, QColor("#0d1117"))
    vals = values[-24:] or [0.0]
    peak = max(max(vals), 1.0)
    n = len(vals)
    step = s / max(n - 1, 1)
    line = QPainterPath()
    area = QPainterPath()
    area.moveTo(0, s)
    for i, v in enumerate(vals):
        x = i * step
        y = s - 6 - (v / peak) * (s - 16)
        pt = QPointF(x, y)
        (line.moveTo(pt) if i == 0 else line.lineTo(pt))
        area.lineTo(pt)
    area.lineTo((n - 1) * step, s)
    area.closeSubpath()
    fill = QColor(accent)
    fill.setAlpha(80)
    p.fillPath(area, QBrush(fill))
    p.setPen(QPen(QColor(accent), 4))
    p.drawPath(line)
    p.end()
    return QIcon(pix)


def _app_icon(name: str, theme: dict | None = None) -> dict:
    """Estilo del badge por app. En tema oscuro usa un chip oscuro con la
    letra de color (los pasteles claros quedaban como manchones)."""
    from .theme import APP_ICONS
    base = APP_ICONS.get(name)
    if base is None:
        letter = (name.strip()[:1] or "?").upper()
        base = {"bg": "#e7f0ff", "fg": "#2563eb", "letter": letter}
    if theme is not None and theme.get("is_dark"):
        return {"bg": theme["segment_bg"], "fg": base["fg"],
                "letter": base["letter"]}
    return base
