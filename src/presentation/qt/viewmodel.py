"""Lógica de presentación pura (sin Qt): tendencias, tasa por app, filtro y orden."""
from __future__ import annotations

from dataclasses import dataclass


def trend_pct(current: float, previous: float | None) -> float | None:
    if previous is None or previous <= 0:
        return None
    return (current - previous) / previous * 100.0


def trend_label(pct: float | None) -> tuple[str, str]:
    if pct is None:
        return "", "none"
    if abs(pct) < 0.5:
        return "= 0 %", "flat"
    arrow, level = ("▲", "up") if pct > 0 else ("▼", "down")
    # half-up (no el redondeo bancario de format): 12,5 % -> 13 %
    return f"{arrow} {int(abs(pct) + 0.5)} %", level


def share_pct(part: float, total: float) -> float:
    return part / total * 100.0 if total else 0.0


class AppRateTracker:
    """Bytes/s por app a partir del acumulado.

    window=0: entre dos lecturas consecutivas.

    window>0: sobre los *puntos de cambio* del acumulado de los últimos `window`
    segundos. nettop entrega snapshots cada 2 s, así que el acumulado sólo cambia
    cada 2ª lectura: medir entre lecturas alterna 0 / 2x, y una ventana fija
    oscila según la fase. Tomando las marcas de tiempo de los cambios la tasa queda
    estable; si no hay cambios durante `window`, vuelve a 0."""

    def __init__(self, window: float = 0.0) -> None:
        self._window = window
        self._prev: dict[str, int] = {}
        self._t: float | None = None
        self._points: dict[str, list[tuple[float, int]]] = {}

    def update(self, totals: dict[str, int], now: float) -> dict[str, float]:
        if self._window <= 0:
            return self._update_pairwise(totals, now)
        rates: dict[str, float] = {}
        points: dict[str, list[tuple[float, int]]] = {}
        for name, value in totals.items():
            pts = self._points.get(name)
            if pts is None or value < pts[-1][1]:
                pts = [(now, value)]          # app nueva o contador reiniciado
            elif value > pts[-1][1]:
                pts = pts + [(now, value)]
            points[name] = pts = self._trim(pts, now)
            rates[name] = self._rate(pts, now)
        self._points = points                 # las apps que desaparecen se descartan
        return rates

    def _trim(self, pts: list[tuple[float, int]], now: float) -> list[tuple[float, int]]:
        # se conserva un punto previo a la ventana como ancla
        old = [i for i, (t, _v) in enumerate(pts) if t < now - self._window]
        return pts[max(old[-1], 0):] if old else pts

    def _rate(self, pts: list[tuple[float, int]], now: float) -> float:
        if len(pts) < 2 or now - pts[-1][0] > self._window:
            return 0.0
        inside = [p for p in pts if p[0] >= now - self._window]
        first = inside[0] if len(inside) >= 2 else pts[-2]
        t_last, v_last = pts[-1]
        return (v_last - first[1]) / (t_last - first[0]) if t_last > first[0] else 0.0

    def _update_pairwise(self, totals: dict[str, int], now: float) -> dict[str, float]:
        dt = (now - self._t) if self._t is not None else 0.0
        rates: dict[str, float] = {}
        for name, value in totals.items():
            before = self._prev.get(name)
            if before is None or dt <= 0 or value < before:
                rates[name] = 0.0
            else:
                rates[name] = (value - before) / dt
        self._prev = dict(totals)
        self._t = now
        return rates


@dataclass(frozen=True)
class AppRowData:
    name: str
    sent: int
    recv: int
    rate: float = 0.0

    @property
    def total(self) -> int:
        return self.sent + self.recv


_SORT_KEYS = {
    "total": lambda r: r.total,
    "down": lambda r: r.recv,
    "up": lambda r: r.sent,
    "now": lambda r: r.rate,
}


def filter_sort_apps(rows: list[AppRowData], query: str, sort: str) -> list[AppRowData]:
    q = query.strip().lower()
    items = [r for r in rows if not q or q in r.name.lower()]
    key = _SORT_KEYS.get(sort, _SORT_KEYS["total"])
    return sorted(items, key=lambda r: (-key(r), r.name.lower()))


def conn_status_kind(status: str) -> str:
    """Agrupa el estado TCP crudo en las cuatro categorías que muestra la tabla."""
    s = status.upper()
    if s == "ESTABLISHED":
        return "established"
    if s == "LISTEN":
        return "listening"
    if s in ("CLOSE_WAIT", "TIME_WAIT", "CLOSING", "LAST_ACK") or s.startswith("FIN_WAIT"):
        return "closing"
    return "other"


def filter_connections(conns, query: str, geo_lookup) -> list:
    """Filtra por app, IP remota, código de país u organización (sin I/O: geo_lookup
    sólo consulta la caché del servicio)."""
    q = query.strip().lower()
    if not q:
        return list(conns)
    out = []
    for c in conns:
        geo = geo_lookup(c.raddr)
        hay = [c.app_name, c.raddr, *(geo or ())]
        if any(q in str(h).lower() for h in hay):
            out.append(c)
    return out
