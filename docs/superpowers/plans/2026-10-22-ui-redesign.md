# Rediseño de la UI de escritorio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar la ventana principal de NetGauge (PySide6) al diseño aprobado por el PO: header con velocidad en vivo, navegación en una sola fila, tarjetas con tendencia, gráfico con ejes y tooltip, límites con estado, pestañas Por aplicación y Conexiones renovadas.

**Architecture:** Se mantiene la estructura actual (`MainWindow` + `widgets.py` + `theme.py` QSS). La lógica pura (formato, tendencia, tasa por app, filtro/orden) va a un módulo nuevo `viewmodel.py` con tests unitarios sin Qt. Los íconos se dibujan desde SVG inline con `QSvgRenderer` (sin dependencias nuevas). Los widgets se reutilizan in-place como hoy (no se recrean por tick).

**Tech Stack:** Python 3.14, PySide6 (Qt 6), pytest. Sin librerías nuevas (decisión del PO/orquestador: no `qt-material` ni Fluent).

**Spec:** Canvas aprobado https://claude.ai/artifact/DPB5HY2ENQknX1vcoGzM2i (3 artboards 786×720: Global, Por aplicación, Conexiones) + esta sección "Global Constraints". Referencia visual obligatoria: cada tarea de UI se compara contra el artboard.

## Global Constraints

- Ventana 786×720 por defecto; `setMinimumSize(420, 360)` se mantiene; en alto < 600 el gráfico se oculta (comportamiento existente en `resizeEvent`).
- Paleta oscura (tokens exactos): fondo `#0b0f17`, tarjeta `#111826`, borde `#1c2740`, texto `#eaf1fb`, texto secundario `#93a6c1`, acento `#458bf8`, bajada `#5aa9ff`, subida `#34d5a3`, advertencia `#f5b942`, peligro `#ef4444`, seleccionado `#13233f` con borde `#2a4a85`. Todo texto ≥ 4.5:1 sobre su fondo; tamaño mínimo de texto 12 px.
- Tipografía: Plus Jakarta Sans (UI) + JetBrains Mono (cifras). Fallback del sistema, nunca "Segoe UI" en macOS.
- Hit targets ≥ 32×32 px para botones de ventana/acciones; botones de la barra de título 36×36.
- i18n: toda cadena nueva en `es`, `en` y `pt` (`tests/test_i18n_parity.py` debe pasar).
- El tema claro (`LIGHT`) debe seguir funcionando (mismo set de claves de token); el diseño aprobado es el oscuro, el claro solo hereda estructura.
- No se agregan dependencias a `requirements.txt`. No se cambia la lógica de captura ni `MonitorService` salvo lo indicado en la Task 3.
- Nada de emojis como íconos; íconos SVG inline.
- Commits convencionales en español, con `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Rama: `feat/ui-redesign`. No pushear ni taguear.
- Tests: `.venv/bin/python -m pytest -q` verde al cerrar cada tarea. `tests/test_ui_snapshot.py` y `tests/test_main_window_snapshot.py` están saltados fuera de Windows: para validar Qt en macOS usá el script de render offscreen de la Task 0.

---

### Task 0: Rama y harness de render offscreen

**Files:**
- Create: `tools/render_ui.py`
- Test: ninguno (herramienta de verificación visual)

**Interfaces:**
- Produces: `python tools/render_ui.py <out_dir>` guarda `ui_global.png`, `ui_apps.png`, `ui_conexiones.png` renderizando `MainWindow` con datos falsos (offscreen). Las tareas 4-8 lo usan para comparar contra el canvas.

- [ ] **Step 1: Crear la rama**

```bash
git checkout -b feat/ui-redesign
```

- [ ] **Step 2: Crear `tools/render_ui.py`**

```python
"""Renderiza MainWindow offscreen con datos falsos y guarda PNGs (verificación visual)."""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from src.presentation.qt import theme  # noqa: E402

theme.load_app_fonts()
from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from src.domain.models import Settings, TrafficSample  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402

APPS = [("Google Chrome", 1, 900e6, 60e6), ("Dropbox", 2, 300e6, 250e6),
        ("Docker", 3, 400e6, 30e6), ("Spotify", 4, 120e6, 2e6),
        ("Slack", 5, 80e6, 40e6), ("Zoom", 6, 60e6, 55e6)]


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    random.seed(1)
    for _ in range(3):
        for name, pid, rx, tx in APPS:
            m._on_sample(TrafficSample(pid, name, bytes_sent=int(tx * random.random() / 3),
                                       bytes_recv=int(rx * random.random() / 3)))
    w = MainWindow(m, per_process=True)
    w.show()
    app.processEvents()
    for idx, name in enumerate(("global", "apps", "conexiones")):
        w._tabs.setCurrentIndex(idx)
        w._refresh()
        app.processEvents()
        w.grab().save(str(out / f"ui_{name}.png"))
    print("ok", out)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ng_ui"))
```

- [ ] **Step 3: Ejecutar y confirmar que genera 3 PNG (estado "antes")**

Run: `.venv/bin/python tools/render_ui.py /tmp/ng_ui_before && ls /tmp/ng_ui_before`
Expected: `ui_global.png ui_apps.png ui_conexiones.png`

- [ ] **Step 4: Commit**

```bash
git add tools/render_ui.py
git commit -m "chore(ui): script de render offscreen para verificar el rediseño"
```

---

### Task 1: Tokens, tipografía y fix de fuente

**Files:**
- Modify: `src/presentation/qt/theme.py` (DARK, FONT_FAMILY, `load_app_fonts`, `app_qss`)
- Create: `assets/fonts/JetBrainsMono-Medium.ttf`, `assets/fonts/JetBrainsMono-Bold.ttf`, `assets/fonts/OFL-JetBrainsMono.txt`
- Modify: `build/network_monitor_macos.spec`, `build/network_monitor.spec` (datas de `assets/fonts` si no lo incluyen ya), `THIRD_PARTY_LICENSES.md`
- Test: `tests/test_theme_tokens.py` (nuevo)

**Interfaces:**
- Produces: `theme.MONO_FAMILY: str` (`'"JetBrains Mono", "Menlo", "Consolas", monospace'`); `theme.FONT_FAMILY` sin "Segoe UI" en macOS; claves nuevas en `DARK` y `LIGHT`: `"down"`, `"selected_bg"`, `"selected_bd"`, `"text_secondary"`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_theme_tokens.py
from src.presentation.qt import theme

REQUIRED = {"down", "upload", "accent", "warning", "danger", "selected_bg",
            "selected_bd", "text", "text_muted", "window_bg", "card_bg", "border"}


def test_both_themes_share_new_keys():
    for t in (theme.DARK, theme.LIGHT):
        assert REQUIRED <= set(t)
    assert set(theme.DARK) == set(theme.LIGHT)


def test_dark_palette_matches_approved_design():
    d = theme.DARK
    assert d["window_bg"] == "#0b0f17"
    assert d["card_bg"] == "#111826"
    assert d["border"] == "#1c2740"
    assert d["accent"] == "#458bf8"
    assert d["down"] == "#5aa9ff"
    assert d["upload"] == "#34d5a3"
    assert d["text_muted"] == "#93a6c1"


def _luminance(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_muted_text_has_aa_contrast_on_cards():
    d = theme.DARK
    assert _contrast(d["text_muted"], d["card_bg"]) >= 4.5
    assert _contrast(d["text_muted"], d["window_bg"]) >= 4.5


def test_font_family_has_no_segoe_on_stack():
    assert "Segoe UI" not in theme.FONT_FAMILY
    assert "JetBrains Mono" in theme.MONO_FAMILY
```

- [ ] **Step 2: Correr y ver el fallo**

Run: `.venv/bin/python -m pytest tests/test_theme_tokens.py -q`
Expected: FAIL (`KeyError: 'down'` / `AttributeError: MONO_FAMILY`).

- [ ] **Step 3: Implementar en `theme.py`**

Reemplazar el bloque `DARK` por estos valores (mantener todas las claves existentes; solo cambian valores y se suman 4 claves):

```python
DARK = {
    "is_dark": True,
    "app_bg": "#0b0f17", "window_bg": "#0b0f17", "titlebar_bg": "#0b0f17",
    "card_bg": "#111826", "chart_bg": "#111826", "input_bg": "#111826",
    "segment_bg": "#111826", "row_hover_bg": "#111826",
    "border": "#1c2740", "hairline": "#1c2740", "input_border": "#1c2740",
    "grid_line": "#1c2740", "track": "#0b0f17",
    "text": "#eaf1fb", "text_strong": "#eaf1fb", "text_muted": "#93a6c1",
    "text_faint": "#93a6c1", "text_secondary": "#c3d0e2",
    "accent": "#458bf8", "accent_strong": "#458bf8", "accent_soft_bg": "#13233f",
    "accent_soft_bd": "#2a4a85", "down": "#5aa9ff", "upload": "#34d5a3",
    "warning": "#f5b942", "warning_2": "#f5b942", "danger": "#ef4444",
    "on_accent": "#06101f", "selected_bg": "#13233f", "selected_bd": "#2a4a85",
    "total_grad_a": "#13233f", "total_grad_b": "#13233f", "total_grad_bd": "#2a4a85",
    "shadow_rgba": "rgba(2,6,23,0.6)",
}
```

Agregar a `LIGHT` las claves nuevas con equivalentes claros: `"down": "#2563eb"`, `"text_secondary": "#475569"`, `"selected_bg": "#eff5ff"`, `"selected_bd": "#dbe8ff"`.

Cambiar:

```python
FONT_FAMILY = '"Plus Jakarta Sans", "Helvetica Neue", "Segoe UI", sans-serif'
MONO_FAMILY = '"JetBrains Mono", "Menlo", "Consolas", monospace'
```

Nota: `FONT_FAMILY` conserva "Segoe UI" solo como tercer fallback para Windows; el test verifica que **no** esté, así que dejar `'"Plus Jakarta Sans", "Helvetica Neue", sans-serif'` y que Windows caiga en `sans-serif` (Qt resuelve Segoe UI por defecto). Esto elimina el warning de alias en macOS.

En `load_app_fonts()`, registrar también `JetBrainsMono-*.ttf` con el mismo patrón `glob`.

- [ ] **Step 4: Fuentes**

Bajar JetBrains Mono Medium y Bold (OFL 1.1) desde el repo oficial `JetBrains/JetBrainsMono` (carpeta `fonts/ttf`) a `assets/fonts/`, junto a su `OFL.txt` renombrado `OFL-JetBrainsMono.txt`. Agregar la atribución a `THIRD_PARTY_LICENSES.md`. Verificar que ambos specs de PyInstaller incluyan `assets/fonts` en `datas` (ya incluye las de Plus Jakarta; no duplicar).

- [ ] **Step 5: Correr tests y suite**

Run: `.venv/bin/python -m pytest tests/test_theme_tokens.py -q && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/presentation/qt/theme.py assets/fonts tests/test_theme_tokens.py THIRD_PARTY_LICENSES.md build/*.spec
git commit -m "feat(ui): tokens del rediseño, JetBrains Mono y fix del fallback Segoe UI"
```

---

### Task 2: viewmodel puro (formato, tendencia, tasa por app, filtro y orden)

**Files:**
- Create: `src/presentation/qt/viewmodel.py`
- Test: `tests/test_viewmodel.py`

**Interfaces:**
- Produces (todas puras, sin Qt):
  - `trend_pct(current: float, previous: float | None) -> float | None` — `None` si `previous` es `None` o `0`; si no, `(current - previous) / previous * 100`.
  - `trend_label(pct: float | None) -> tuple[str, str]` — `(texto, nivel)` con nivel `"up" | "down" | "flat" | "none"`; texto `"▲ 12 %"`, `"▼ 4 %"`, `"= 0 %"` o `""` (|pct| < 0.5 → flat).
  - `class AppRateTracker` — `update(totals: dict[str, int], now: float) -> dict[str, float]` devuelve bytes/s por app calculado contra la llamada anterior; apps nuevas y contadores que bajan dan `0.0`.
  - `filter_sort_apps(rows: list[AppRowData], query: str, sort: str) -> list[AppRowData]` con `AppRowData` = `dataclass(name: str, sent: int, recv: int, rate: float)`; `sort` ∈ `"total" | "down" | "up" | "now"`; filtro case-insensitive por substring en `name`; orden descendente, desempate por nombre.
  - `share_pct(part: float, total: float) -> float`.

- [ ] **Step 1: Tests que fallan**

```python
# tests/test_viewmodel.py
import pytest

from src.presentation.qt.viewmodel import (
    AppRateTracker, AppRowData, filter_sort_apps, share_pct, trend_label, trend_pct)


def test_trend_pct():
    assert trend_pct(112, 100) == pytest.approx(12.0)
    assert trend_pct(96, 100) == pytest.approx(-4.0)
    assert trend_pct(50, None) is None
    assert trend_pct(50, 0) is None


def test_trend_label():
    assert trend_label(12.4) == ("▲ 12 %", "up")
    assert trend_label(-4.2) == ("▼ 4 %", "down")
    assert trend_label(0.2) == ("= 0 %", "flat")
    assert trend_label(None) == ("", "none")


def test_rate_tracker_computes_bytes_per_second():
    t = AppRateTracker()
    assert t.update({"a": 1000}, now=10.0) == {"a": 0.0}   # primera lectura
    assert t.update({"a": 3000, "b": 500}, now=12.0) == {"a": 1000.0, "b": 0.0}


def test_rate_tracker_counter_drop_is_zero():
    t = AppRateTracker()
    t.update({"a": 5000}, now=0.0)
    assert t.update({"a": 100}, now=1.0) == {"a": 0.0}


def test_filter_sort():
    rows = [AppRowData("Chrome", 10, 90, 5.0), AppRowData("Dropbox", 60, 40, 9.0),
            AppRowData("Slack", 1, 2, 0.0)]
    # Chrome y Dropbox empatan en total (100): desempate por nombre ascendente.
    assert [r.name for r in filter_sort_apps(rows, "", "total")] == ["Chrome", "Dropbox", "Slack"]
    assert [r.name for r in filter_sort_apps(rows, "", "up")][0] == "Dropbox"
    assert [r.name for r in filter_sort_apps(rows, "", "now")][0] == "Dropbox"
    assert [r.name for r in filter_sort_apps(rows, "ch", "total")] == ["Chrome"]


def test_share_pct():
    assert share_pct(25, 100) == 25.0
    assert share_pct(5, 0) == 0.0
```

- [ ] **Step 2: Ver el fallo**

Run: `.venv/bin/python -m pytest tests/test_viewmodel.py -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implementar `viewmodel.py`**

```python
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
    return f"{arrow} {abs(pct):.0f} %", level


def share_pct(part: float, total: float) -> float:
    return part / total * 100.0 if total else 0.0


class AppRateTracker:
    """Bytes/s por app, calculados entre dos lecturas consecutivas del acumulado."""

    def __init__(self) -> None:
        self._prev: dict[str, int] = {}
        self._t: float | None = None

    def update(self, totals: dict[str, int], now: float) -> dict[str, float]:
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
```

- [ ] **Step 4: Tests en verde**

Run: `.venv/bin/python -m pytest tests/test_viewmodel.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/presentation/qt/viewmodel.py tests/test_viewmodel.py
git commit -m "feat(ui): viewmodel puro (tendencia, tasa por app, filtro y orden)"
```

---

### Task 3: Datos que faltan en MonitorService (período previo y ruta del ejecutable)

**Files:**
- Modify: `src/application/monitor_service.py` (cerca de `usage_for_period`, líneas ~485-516, y `trust_for`, ~530)
- Test: `tests/test_monitor_service_periods.py` (nuevo; usar los fakes de `tests/conftest.py`)

**Interfaces:**
- Produces:
  - `MonitorService.previous_period_total(period: str) -> int | None` — total de bytes (enviados+recibidos) del período inmediatamente anterior de igual duración (`day` → ayer, `week` → 7 días previos, `month` → mes previo). Para `"session"` devuelve `None`. Devuelve `None` si el repo no tiene datos previos (suma 0).
  - `MonitorService.exe_path_for(app_name: str) -> str | None` — primera ruta conocida del ejecutable (de `_refresh_exe_paths`) o `None`. Lo consume la Task 7 para el ícono real.

- [ ] **Step 1:** Leer `monitor_service.py` líneas 485-545 y 518-530 para reutilizar `_period_start(period)` y el almacén de rutas; **no duplicar** la lógica de ventanas.
- [ ] **Step 2: Test que falla** — con `FakeRepo` cuyo `totals_by_app(start, end)` devuelve registros solo si `end <= hoy 00:00`: afirmar que `previous_period_total("day")` es la suma de los registros de ayer, `previous_period_total("session") is None`, y que sin registros previos da `None`. Afirmar que `exe_path_for("x")` devuelve `None` si no hay ruta y la primera ruta si la hay.
- [ ] **Step 3: Correr y ver el fallo.** Run: `.venv/bin/python -m pytest tests/test_monitor_service_periods.py -q` → FAIL (`AttributeError`).
- [ ] **Step 4: Implementar** ambos métodos como lecturas del snapshot ya calculado por el worker (no I/O en el hilo GUI: `previous_period_total` debe calcularse en el worker junto a `_refresh_period_snapshot` y exponerse como lectura de dict; **la UI jamás consulta SQLite**, es una regla de `test_main_window_snapshot.py`).
- [ ] **Step 5: Suite completa verde.** Run: `.venv/bin/python -m pytest -q`
- [ ] **Step 6: Commit**

```bash
git add src/application/monitor_service.py tests/test_monitor_service_periods.py
git commit -m "feat(app): período previo y ruta de ejecutable disponibles para la UI"
```

---

### Task 4: Íconos SVG y barra de título

**Files:**
- Create: `src/presentation/qt/icons.py`
- Modify: `src/presentation/qt/main_window.py` (`_build_titlebar`, `_style_mode_badge`, `_tick`, `_retranslate`), `src/presentation/qt/theme.py` (QSS `#TitleBar`, `#SpeedDown`, `#SpeedUp`, `#WinBtn`)
- Test: `tests/test_icons.py`

**Interfaces:**
- Produces: `icons.svg_icon(name: str, color: str, size: int = 18) -> QIcon` con `name` ∈ `info`, `settings`, `moon`, `minimize`, `maximize`, `restore`, `close`, `search`, `chevron-down`, `check`, `wifi-off`; lanza `KeyError` si el nombre no existe.

- [ ] **Step 1: Test que falla**

```python
# tests/test_icons.py
import os
import pytest
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from src.presentation.qt import icons

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])

def test_all_icons_render(qapp):
    for name in icons.NAMES:
        ic = icons.svg_icon(name, "#93a6c1", 18)
        assert not ic.pixmap(18, 18).isNull(), name

def test_unknown_icon_raises(qapp):
    with pytest.raises(KeyError):
        icons.svg_icon("nope", "#fff")
```

- [ ] **Step 2:** Correr → FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implementar `icons.py`** con un dict `_SVG` de plantillas con `{c}` para el color (trazos Lucide-like de 24×24, `stroke-width` 2, mismos paths que el artboard: círculo + `M12 11v5M12 7.5v.01` para `info`; engranaje, luna `M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z`, `minimize` `M5 12h14`, `maximize` cuadrado, `restore` dos cuadrados, `close` `M6 6l12 12M18 6L6 18`, `search`, `chevron-down` `M6 9l6 6 6-6`, `check` `M5 12.5l4.5 4.5L19 7`, `wifi-off`). `svg_icon` arma el SVG, lo renderiza con `QSvgRenderer` a un `QPixmap` transparente `size×size` (devicePixelRatio 2 para nitidez) y devuelve `QIcon`. Exponer `NAMES = tuple(_SVG)`.
- [ ] **Step 4:** `.venv/bin/python -m pytest tests/test_icons.py -q` → PASS.
- [ ] **Step 5: Barra de título.** En `_build_titlebar`: alto 56; logo + `NetGauge` (se **elimina** `brand.sub` "· Mes actual" y el badge `nettop · por app`); `addStretch()`; velocidades como dos `QLabel` con `objectName` `SpeedDown`/`SpeedUp`, fuente `MONO_FAMILY` 20 px bold, y la unidad (`MB/s`) en un `QLabel` aparte 12 px gris (formato `↓ 12,4 MB/s`: separar valor y unidad con `loc_bytes(...).partition(" ")`); separador vertical 1×24 `#1c2740`; botones `info`, `settings`, `moon` de 36×36 con `svg_icon(..., theme["text_muted"])` y tooltips existentes; botones de ventana 32×32 con `minimize/maximize/close`. El modo de captura (`mode.*`) pasa al pie de la ventana (Task 8 crea la barra de estado; hasta entonces dejarlo como tooltip del logo). Mantener `objectName="WinBtn"` y la propiedad `class="CloseBtn"` para el hover rojo.
- [ ] **Step 6:** `_tick` actualiza los nuevos labels; `_retranslate` y `_toggle_theme` recoloran los íconos (`svg_icon` con el color del tema); `_toggle_maximize` y `changeEvent` cambian el ícono `maximize`/`restore` en vez de texto.
- [ ] **Step 7: Verificación visual.** `.venv/bin/python tools/render_ui.py /tmp/ng_t4` y comparar `ui_global.png` (zona header) con el artboard "1 · Global": velocidad grande a la derecha, íconos nítidos, sin badge verde.
- [ ] **Step 8:** Suite verde + commit

```bash
git add src/presentation/qt/icons.py src/presentation/qt/main_window.py src/presentation/qt/theme.py tests/test_icons.py
git commit -m "feat(ui): barra de título con velocidad en vivo grande e íconos SVG"
```

---

### Task 5: Navegación en una sola fila (pestañas + período + unidad)

**Files:**
- Modify: `src/presentation/qt/main_window.py` (`_build_ui`, `_build_toolbar`, `_build_tabs`, `_open_quota`, `_retranslate`), `src/presentation/qt/theme.py` (QSS `QTabBar`, `#Segment`, `#SegChip`, `#UnitBox`, nuevo `#UnitCaption`)
- Test: extender `tests/test_ui_snapshot.py` con un test de estructura que corra en cualquier SO (`QT_QPA_PLATFORM=offscreen`; quitar el `skipif` de win32 **solo** para este test nuevo).

**Interfaces:**
- Consumes: `svg_icon` (Task 4).
- Produces: `MainWindow._nav_row` (QHBoxLayout) que contiene `self._tabs.tabBar()` a la izquierda, el segmento de período y `UnitBox` con su caption "Unidad" a la derecha; el botón "Cuota" desaparece de la barra (se accede desde las tarjetas de límites, Task 6).

- [ ] **Step 1: Test que falla** — instanciar `MainWindow` con los fakes y afirmar: (a) `hasattr(w, "_quota_btn")` es `False`; (b) `w._tabs.tabBar().parent()` está en la misma fila que `w._seg_group.buttons()[0].parent()` (mismo `QLayout` padre: `w._nav_row.indexOf(...) >= 0`); (c) `len(w._seg_group.buttons()) == 4`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3: Implementar.** `QTabWidget` mantiene el stack pero su `tabBar()` se reparenta al `_nav_row` (`self._tabs.tabBar().setParent(None)` luego `addWidget`); el resto de `_build_toolbar` se mueve a esa fila; `UnitBox` pasa a un `QWidget` con `QLabel("Unidad")` (nueva clave i18n `unit.caption`) + combo; QSS: pestaña seleccionada `#eaf1fb` 700 con borde inferior 2 px `#458bf8`; inactiva `#93a6c1` 600; segmento con fondo `card_bg`, borde `border`, chip activo `background: accent; color: on_accent`.
- [ ] **Step 4:** Línea divisoria 1 px `border` bajo la fila (`QFrame` HLine).
- [ ] **Step 5:** Test en verde + `render_ui.py` y comparar la fila con el artboard.
- [ ] **Step 6: Commit** `feat(ui): navegación en una sola fila con período y unidad rotulada`

---

### Task 6: Pestaña Global (tarjetas con tendencia, gráfico con ejes y tooltip, límites con estado)

**Files:**
- Modify: `src/presentation/qt/widgets.py` (`MetricCard`, `LiveChart`, `QuotaBar` → nuevo `LimitCard`), `src/presentation/qt/main_window.py` (`_build_global_tab`, `_refresh`, `_tick`, `_open_quota`), `src/presentation/qt/theme.py` (QSS tarjetas/chips)
- Test: `tests/test_widgets_redesign.py` (nuevo, offscreen)

**Interfaces:**
- Consumes: `trend_pct`, `trend_label`, `share_pct` (Task 2); `MonitorService.previous_period_total` (Task 3).
- Produces:
  - `MetricCard.set_values(value_text, unit_text, sub, trend_text="", trend_level="none", spark=None)` con `spark: list[float] | None` (hasta 24 puntos, se dibuja como polilínea de 2 px en el color de la tarjeta).
  - `LiveChart.set_window_seconds(n: int)`, `LiveChart.hover_index() -> int | None`, `LiveChart.value_at(i: int) -> tuple[float, float]` (down, up); pinta ejes (0, ¼, ½, ¾ del pico redondeado a 1/2/5×10ⁿ con etiqueta en `MONO_FAMILY` 12 px), etiquetas de tiempo (`−2 min`, `−1 min`, `ahora`), degradé bajo la curva de bajada, tooltip al mover el mouse (`setMouseTracking(True)`) con hora relativa y ↓/↑.
  - `LimitCard(theme)` con `set_state(label: str, used_text: str, percent: float, has_limit: bool, hint: str)` y señal `define_clicked`; sin límite muestra borde punteado y botón "Definir límite"; con límite, barra coloreada: `< 80` acento, `80–99` advertencia, `≥ 100` peligro, y texto `hint` ("Te avisamos al llegar al 80 %").

- [ ] **Step 1: Tests que fallan** (offscreen):
  - `nice_ticks(peak)` (función pública de `widgets.py`): `nice_ticks(18.6e6)` devuelve `[0, 5e6, 10e6, 15e6, 20e6]` redondeado; `nice_ticks(0)` devuelve `[0, 1, 2, 3, 4]` en bytes (mínimo 1 KB/s se evita en la etiqueta: usar `max(peak, 1024)`).
  - `LimitCard.set_state(..., percent=68, has_limit=True)` → `card.level() == "ok"`; `percent=85` → `"warn"`; `percent=100` → `"danger"`; `has_limit=False` → `"empty"` y el botón "Definir límite" es visible y emite `define_clicked`.
  - `LiveChart` con 60 puntos: `value_at(59)` devuelve el último push; el tooltip no rompe con `peak == 0`.
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3: Implementar** `nice_ticks` (paso = 1/2/5 × 10ⁿ ≥ peak/4), `LimitCard`, `LiveChart` (márgenes: izquierda 52 px para etiquetas, abajo 24 px; dibujo con `QPainter`; hover con `mouseMoveEvent`/`leaveEvent` y `update()`), `MetricCard` con `spark`.
- [ ] **Step 4: Cableado en `main_window.py`.** `_refresh`: para `period != "session"` calcular `trend_pct(total_período, monitor.previous_period_total(period))`; para `session` no hay tendencia (el texto de tendencia queda vacío y la tarjeta total muestra "esta sesión"); guardar en `self._spark_down/_spark_up/_spark_total` (deque de 24, un punto por refresco) para las mini curvas; sub del total = `Pico: {peak}/s`. Reemplazar `_quota_row` por dos `LimitCard`; `define_clicked` y el click del título abren `_open_quota`. Textos nuevos en i18n (es/en/pt): `card.vs_prev` "{p} vs ayer/semana/mes" (según período), `chart.axis.now`, `chart.axis.minutes`, `limit.define`, `limit.hint_80`, `limit.none`.
- [ ] **Step 5:** Tests en verde; `render_ui.py` y comparar con el artboard "1 · Global" (tarjetas, ejes, límites).
- [ ] **Step 6: Commit** `feat(ui): pestaña Global con tendencia, gráfico con ejes/tooltip y límites con estado`

---

### Task 7: Pestaña Por aplicación

**Files:**
- Modify: `src/presentation/qt/widgets.py` (`AppRow`), `src/presentation/qt/main_window.py` (`_build_apps_tab`, `_rebuild_apps`, `_tick`), `src/presentation/qt/theme.py`
- Create: `src/presentation/qt/app_icons.py`
- Test: `tests/test_app_icons.py`, ampliar `tests/test_widgets_redesign.py`

**Interfaces:**
- Consumes: `AppRateTracker`, `filter_sort_apps`, `AppRowData`, `share_pct` (Task 2); `MonitorService.exe_path_for` (Task 3).
- Produces:
  - `app_icons.icon_for(app_name: str, exe_path: str | None, size: int = 44) -> QPixmap` — usa `QFileIconProvider().icon(QFileInfo(exe_path))` cuando hay ruta y devuelve un pixmap no nulo; si no, genera un chip de color estable (hash del nombre → 1 de 8 hues de la paleta del diseño) con la inicial. Cachea por `(app_name, exe_path)`.
  - `AppRow.update_data(total_text, rate_text, share_text, pct_of_top, conns_text, active)`; fila en 4 columnas: ícono 44 px · (nombre + `N conexiones`, barra a todo el ancho) · velocidad actual (`↓`/`↑` en `MONO_FAMILY` 12 px) · total (`MONO_FAMILY` 15 px bold) + `% del total`.
  - `MainWindow._apps_search: QLineEdit`, `MainWindow._apps_sort: str` con chips `Total ↓ / Bajada / Subida / Ahora`; cabecera de columnas.

- [ ] **Step 1: Tests que fallan**
  - `icon_for("Foo", None)` devuelve pixmap no nulo; dos llamadas iguales devuelven el mismo color de chip (determinismo); nombres distintos pueden diferir; `icon_for("Foo", "/ruta/que/no/existe")` cae al chip sin lanzar.
  - `AppRow` con `update_data(...)` muestra los textos en los labels (`row._tot.text()`, `row._rate.text()`, `row._share.text()`).
  - Tras `w._apps_search.setText("chr")` y `w._refresh()` solo queda visible la fila de Chrome (`isVisible()`/`isHidden()` de las demás o ausencia en `_app_rows` según la reconciliación que uses; documentarlo en el test).
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3: Implementar** `app_icons.py`, `AppRow` nuevo (reutiliza `set_trust`/`set_vt_badge` y los slots de 22/16 px existentes), buscador (ícono `search`), chips de orden (`aria`-equivalente: `QPushButton` checkable en `QButtonGroup`), cabecera. En `_rebuild_apps`: construir `AppRowData` con `AppRateTracker.update({app: sent+recv}, time.monotonic())` (instancia en `__init__`, se actualiza en `_tick` y se guarda `self._rates`), aplicar `filter_sort_apps`, y conservar la reconciliación in-place (no recrear filas). La "fila activa" es la primera tras ordenar (`active=(i == 0)`) con fondo `selected_bg`/borde `selected_bd`. El conteo de conexiones sale de `self._monitor.connections()` agrupado por `app_name` (ya es snapshot, sin I/O). Estado vacío cuando el filtro no encuentra nada: texto centrado "Sin resultados para «{q}»" (i18n `apps.no_results`).
- [ ] **Step 4:** i18n es/en/pt: `apps.search`, `apps.sort`, `apps.sort.total/down/up/now`, `apps.col.app/now/total`, `apps.conns` (plural simple), `apps.no_results`.
- [ ] **Step 5:** Tests verdes; `render_ui.py` vs artboard "2 · Por aplicación".
- [ ] **Step 6: Commit** `feat(ui): pestaña Por aplicación con íconos, búsqueda, orden y velocidad actual`

---

### Task 8: Pestaña Conexiones + barra de estado

**Files:**
- Modify: `src/presentation/qt/widgets.py` (`ConnRow`), `src/presentation/qt/main_window.py` (`_build_connections_tab`, `_refresh_connections`, nueva `_build_statusbar`), `src/presentation/qt/theme.py` (QSS `QCheckBox::indicator`, tabla, chips de estado)
- Test: ampliar `tests/test_widgets_redesign.py`

**Interfaces:**
- Produces:
  - `ConnRow` en 5 columnas: Aplicación (ícono 22 px de `app_icons` + nombre) · Destino (`host` si hay y `ip:puerto` en gris, `MONO_FAMILY` 12 px) · País (código) · Estado (punto + texto: `Establecida` verde, `Cerrando` ámbar, resto gris) · Tráfico (si no hay dato, `—`).
  - Cabecera de tabla fija; filtro de texto (app/host/país) y chips `Todas · N / Establecidas / Escuchando`; checkbox "Ocultar localhost" con indicador propio (20×20, borde `border`, marcado `accent` con ícono `check`).
  - Estado vacío con ícono `wifi-off`, título y texto (i18n `conn.empty.title`, `conn.empty.body`) en lugar del label suelto.
  - `MainWindow._build_statusbar() -> QWidget` (30 px): punto verde + "Captura por aplicación activa" (o la etiqueta `mode.*` correspondiente) a la izquierda, "Mes actual · v{APP_VERSION}" a la derecha; reemplaza lo que dejó el badge de la Task 4.

- [ ] **Step 1: Tests que fallan:** (a) con 3 conexiones falsas y filtro `"drop"` solo queda la de Dropbox; (b) con lista vacía `_conn_empty` es visible y con datos se oculta; (c) el checkbox sigue persistiendo `hide_localhost` en settings (`monitor.settings.hide_localhost` cambia al togglear).
- [ ] **Step 2:** Correr → FAIL.
- [ ] **Step 3: Implementar** la tabla (mismas filas reutilizadas in-place por clave `app|raddr:rport|status`), filtros, estado vacío y statusbar.
- [ ] **Step 4:** i18n es/en/pt para las claves nuevas; `tests/test_i18n_parity.py` verde.
- [ ] **Step 5:** `render_ui.py` vs artboard "3 · Conexiones".
- [ ] **Step 6: Commit** `feat(ui): pestaña Conexiones con tabla, filtros y estado vacío + barra de estado`

---

### Task 9: Cierre — paridad de temas, regresión y entrega

**Files:**
- Modify: `CHANGELOG.md` (`[Unreleased]` → `Changed`: rediseño de la UI), `README.md` (capturas si se actualizan)
- Test: suite completa

- [ ] **Step 1: Tema claro.** Alternar `_toggle_theme()` en el harness y verificar que no hay claves faltantes ni texto ilegible (render de `LIGHT`: `w._toggle_theme()` y guardar `ui_*_light.png`); corregir contrastes obvios en `LIGHT`.
- [ ] **Step 2: Regresión.** `.venv/bin/python -m pytest -q` verde; `grep -rn "Segoe UI" src/presentation/qt/` sin resultados salvo comentarios; arrancar `python main.py` ~10 s en macOS sin warnings de fuente y sin excepciones en el log.
- [ ] **Step 3: Rendimiento.** Medir CPU de la app con la UI abierta 30 s (idle) con `ps -o cputime`: no debe superar ~10 % de un core (el gráfico y el hover no deben forzar repintados continuos: `update()` solo en `push` y en hover).
- [ ] **Step 4: Capturas antes/después.** `tools/render_ui.py` → `/tmp/ng_after` y comparar con `/tmp/ng_ui_before` (Task 0). Entregar ambas rutas al PO para la verificación visual.
- [ ] **Step 5: CHANGELOG** con una entrada `Changed` que resuma el rediseño (header, navegación, gráfico, límites, aplicaciones, conexiones, tipografía).
- [ ] **Step 6: Commit** `docs(ui): changelog del rediseño` — sin merge ni release: lo decide el PO tras su verificación visual.

---

## Self-Review

- **Cobertura del spec:** header (T4), navegación única (T5), tarjetas con tendencia + gráfico con ejes/tooltip + límites (T6), Por aplicación (T7), Conexiones + estado vacío + checkbox (T8), fix "Segoe UI" y tipografía (T1), unidades rotuladas (T5), movimiento sutil — **fuera de alcance de esta versión** (se evalúa después de la verificación visual; el canvas no lo mostraba).
- **Placeholders:** las Tasks 3, 6, 7 y 8 describen la implementación de widgets en prosa con contratos exactos (firmas y comportamiento) en vez de pegar cientos de líneas de QPainter; el código obligatorio (tests, helpers puros, íconos, tokens) está completo. El implementador debe respetar las firmas de "Interfaces".
- **Consistencia de tipos:** `AppRowData(name, sent, recv, rate)`, `filter_sort_apps(rows, query, sort)`, `trend_label -> (str, level)`, `MetricCard.set_values(..., trend_text, trend_level, spark)`, `LimitCard.set_state/level/define_clicked`, `exe_path_for`, `previous_period_total` se usan con los mismos nombres en todas las tareas.
