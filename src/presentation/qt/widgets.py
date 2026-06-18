"""Widgets custom dibujados con QPainter para fidelidad pixel-perfect."""
from __future__ import annotations

from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
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

_GRAPH_POINTS = 60


class LiveChart(QWidget):
    """Gráfico de área+línea en vivo: bajada (azul) y subida (verde)."""

    def __init__(self, theme: dict) -> None:
        super().__init__()
        self._t = theme
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._down = deque([0.0] * _GRAPH_POINTS, maxlen=_GRAPH_POINTS)
        self._up = deque([0.0] * _GRAPH_POINTS, maxlen=_GRAPH_POINTS)

    def set_theme(self, theme: dict) -> None:
        self._t = theme
        self.update()

    def push(self, up: float, down: float) -> None:
        self._up.append(up)
        self._down.append(down)
        self.update()

    def peak(self) -> float:
        return max(max(self._up), max(self._down), 1.0)

    def _series_path(self, data, w: float, h: float, peak: float):
        step = w / (_GRAPH_POINTS - 1)
        line = QPainterPath()
        area = QPainterPath()
        area.moveTo(0, h)
        for i, v in enumerate(data):
            x = i * step
            y = h - (v / peak) * (h - 6) - 3
            pt = QPointF(x, y)
            (line.moveTo(pt) if i == 0 else line.lineTo(pt))
            (area.lineTo(pt) if i else area.lineTo(pt))
        area.lineTo(w, h)
        area.closeSubpath()
        return line, area

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        peak = self.peak()

        # Grilla
        grid = QPen(QColor(self._t["grid_line"]), 1)
        p.setPen(grid)
        for frac in (0.0, 0.5, 1.0):
            y = h * frac if frac else 1
            y = min(h - 1, max(1, h * frac))
            p.drawLine(QPointF(0, y), QPointF(w, y))

        def draw(data, color_hex):
            line, area = self._series_path(data, w, h, peak)
            color = QColor(color_hex)
            grad = QLinearGradient(0, 0, 0, h)
            fill = QColor(color_hex)
            fill.setAlpha(70)
            grad.setColorAt(0.0, fill)
            tail = QColor(color_hex)
            tail.setAlpha(0)
            grad.setColorAt(1.0, tail)
            p.fillPath(area, QBrush(grad))
            p.setPen(QPen(color, 2.3))
            p.drawPath(line)

        draw(self._down, self._t["accent"])
        draw(self._up, self._t["upload"])
        p.end()


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


class MetricCard(QFrame):
    """Tarjeta de métrica: punto + nombre, número hero + unidad, subtexto."""

    def __init__(self, theme: dict, dot_color: str, name: str,
                 is_total: bool = False) -> None:
        super().__init__()
        self.setObjectName("TotalCard" if is_total else "Card")
        self._dot = dot_color
        self._is_total = is_total
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 15, 16, 15)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(7)
        if not is_total:
            dot = QLabel()
            dot.setFixedSize(9, 9)
            dot.setStyleSheet(f"background:{dot_color}; border-radius:4px;")
            top.addWidget(dot)
        self._name = QLabel(name)
        self._name.setObjectName("TotalName" if is_total else "MetricName")
        top.addWidget(self._name)
        top.addStretch()
        lay.addLayout(top)

        hero = QHBoxLayout()
        hero.setSpacing(5)
        hero.setContentsMargins(0, 0, 0, 0)
        self._value = QLabel("0.0")
        self._value.setObjectName("MetricHero")
        self._unit = QLabel("B")
        self._unit.setObjectName("MetricUnit")
        if is_total:
            self._unit.setStyleSheet("color:#60a5fa;")
        hero.addWidget(self._value)
        hero.addWidget(self._unit, 0, Qt.AlignmentFlag.AlignBottom)
        hero.addStretch()
        lay.addLayout(hero)

        self._sub = QLabel("")
        self._sub.setObjectName("TotalSub" if is_total else "MetricSub")
        lay.addWidget(self._sub)

    def set_values(self, value_text: str, unit_text: str, sub: str) -> None:
        self._value.setText(value_text)
        self._unit.setText(unit_text)
        self._sub.setText(sub)

    def set_name(self, name: str) -> None:
        self._name.setText(name)


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
        name = QLabel(app_name)
        name.setObjectName("AppName")
        lay.addWidget(name)
        self._geo = QLabel("")
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
