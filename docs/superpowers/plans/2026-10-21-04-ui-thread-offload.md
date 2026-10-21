# UI Thread Offload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el hilo GUI de NetGauge no haga IO nunca: trust (WinVerifyTrust/CryptQueryObject/version-info), `psutil.process_iter`, `psutil.net_connections` y los `SUM` de SQLite pasan a un único worker de fondo en la capa de aplicación; la UI sólo lee un snapshot. De paso: el cache de nombres por PID deja de heredar nombres de PIDs reciclados, y dos `.exe` distintos con el mismo FileDescription ya no comparten veredicto (se informa el PEOR).

**Architecture:** `SnapshotRefresher` (nuevo, `src/application/snapshot_refresher.py`) es un hilo daemon con loop basado en `threading.Event` (intervalo ~2 s + `trigger()` a demanda). `MonitorService` lo posee: `refresh_snapshot()` hace todo el IO (cuotas, período pedido, conexiones con demanda, trust de apps pedidas) y publica en campos protegidos por `_snap_lock`. Los getters públicos que usa la UI (`quota_status`, `daily_status`, `usage_for_period`, `trust_for`, `connections`) mantienen su nombre pero sólo leen el snapshot y, como mucho, despiertan al worker UNA vez por pedido nuevo. La presentación sólo agrega una `Signal` de Qt que recibe el aviso "snapshot listo" (QueuedConnection) y repinta. El dominio gana `worst_trust()`; el puerto `ConnectionProvider.exe_paths()` pasa a `dict[str, frozenset[str]]`.

**Tech Stack:** Python 3.14, PySide6, psutil, threading, pytest.

**Spec:** docs/superpowers/specs/2026-10-21-release-audit-fixes-design.md

## Global Constraints

- **Prerrequisitos:** los planes 01 (`trust.py` ctypes), 02 (SQLite) y 03 (`_tick`/`_rate_tick` con try/finally, logging con `logging.getLogger`, `FallbackCaptureService`) ya están aplicados. Este plan toca `monitor_service.py` SÓLO para el snapshot, trust y `exe_paths`. Si una porción de código citada como "actual" difiere por cambios del plan 03, aplicá el cambio sobre la versión vigente preservando lo que agregó el 03 (try/finally, logging).
- **Decisión del spec (no negociable):** un único worker en la capa de APLICACIÓN. Nada de `QThreadPool`/`QThread` con lógica de negocio en `src/presentation/`. `src/application/` NO importa Qt.
- Strict TDD: test rojo → implementación mínima → verde → commit. Cada task es un work unit con su commit.
- Comentarios y docstrings en español, mismo estilo que el archivo que se toca.
- Commits: conventional commits en español, SIN `Co-Authored-By` ni atribución de IA. Nunca `git add -A`: sólo los archivos listados.
- No buildear (PyInstaller) después de los cambios. Correr tests sí.
- En comandos de shell usar `rg`/`fd`/`bat`/`eza` (no grep/find/cat/ls).
- Los tests que crean widgets Qt se saltean fuera de Windows (`skipif(sys.platform != "win32")`), igual que `tests/test_native_window.py`.
- Comando de tests: `python -m pytest -q <ruta>` desde la raíz del repo.

## Review Focus

- **Bucle UI↔worker:** el worker avisa → la UI repinta → los getters NO deben volver a despertar al worker salvo por un pedido realmente nuevo (app nunca pedida, período distinto, conexiones tras >10 s sin demanda). Un `trigger()` por cada `trust_for` de una app sin ruta ("PID 1234", "System") generaría un loop caliente.
- **Locks:** `_snap_lock` NUNCA se mantiene tomado durante IO (evaluate, SQLite, psutil). `_lock` (camino caliente de captura) no se toca desde el worker salvo vía métodos existentes.
- **Getters sin IO:** ningún getter público usado por `MainWindow._refresh` llama al repo, al evaluador ni a psutil (lo prueban `tests/test_ui_snapshot.py` y `tests/test_main_window_snapshot.py`).
- **Peor veredicto:** orden `TRUSTED < UNKNOWN < CAUTION < SUSPICIOUS`; VT se aplica por ruta ANTES de combinar.
- **Cache de PID:** el fallback `"PID n"` no se cachea; reciclado de PID detectado por `create_time` en ≤ `_REVALIDATE_S`; tamaño acotado; lock sin IO adentro.
- **ETW:** `etw_capture._on_event` sigue llamando `friendly_name(pid)` dentro del callback. Aceptado: el primer evento de un PID hace IO (psutil + version.dll), los siguientes son hits O(1) del cache, re-verificados cada `_REVALIDATE_S` con una sola syscall (`create_time`). Se documenta con un comentario (Task 2), no se cambia el diseño.
- `geo_for` queda en el hilo GUI a propósito: `GeoIpService.lookup` es no bloqueante por contrato (cache + cola propia en `geoip_ipapi.py`).
- `_check_quota_alerts` (timer de flush, ya fuera del GUI) sigue consultando SQLite con `_compute_*`; no lee el snapshot para no acoplar alertas al worker.

---

### Task 1: `worst_trust` en el dominio

**Files:**
- Modify: `src/domain/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: `TrustInfo`, constantes `TRUST_*` (existentes).
- Produces: `worst_trust(infos: Iterable[TrustInfo]) -> TrustInfo` — devuelve el veredicto más severo (`TRUSTED < UNKNOWN < CAUTION < SUSPICIOUS`); ante empate gana el primero; lista vacía → `TrustInfo(level=TRUST_UNKNOWN)`. Lo usa `MonitorService` en Task 6.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `tests/test_models.py`:

```python
# ---- combinación de veredictos de confianza (plan 04) ----------------------
from src.domain.models import (  # noqa: E402
    TRUST_CAUTION, TRUST_SUSPICIOUS, TRUST_TRUSTED, TRUST_UNKNOWN, TrustInfo,
    worst_trust,
)


def test_worst_trust_picks_most_severe():
    real = TrustInfo(level=TRUST_TRUSTED,
                     exe_path="C:/Program Files/Google/Chrome/chrome.exe")
    fake = TrustInfo(level=TRUST_CAUTION, exe_path="C:/Users/x/AppData/chrome.exe")
    assert worst_trust([real, fake]) is fake
    assert worst_trust([fake, real]) is fake


def test_worst_trust_suspicious_beats_everything():
    infos = [TrustInfo(level=TRUST_TRUSTED), TrustInfo(level=TRUST_SUSPICIOUS),
             TrustInfo(level=TRUST_CAUTION), TrustInfo(level=TRUST_UNKNOWN)]
    assert worst_trust(infos).level == TRUST_SUSPICIOUS


def test_worst_trust_unknown_is_worse_than_trusted():
    # "no sé" nunca debe pasar por bueno
    infos = [TrustInfo(level=TRUST_TRUSTED), TrustInfo(level=TRUST_UNKNOWN)]
    assert worst_trust(infos).level == TRUST_UNKNOWN


def test_worst_trust_empty_is_unknown():
    assert worst_trust([]).level == TRUST_UNKNOWN


def test_worst_trust_tie_keeps_first():
    a = TrustInfo(level=TRUST_CAUTION, exe_path="a")
    b = TrustInfo(level=TRUST_CAUTION, exe_path="b")
    assert worst_trust([a, b]) is a
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_models.py`
Expected: FAIL — `ImportError: cannot import name 'worst_trust' from 'src.domain.models'`.

- [ ] **Step 3: Implementación mínima**

En `src/domain/models.py`, cambiar el import de cabecera:

```python
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
```

Debajo de `TRUST_SUSPICIOUS = "suspicious"  # varias señales de riesgo` agregar:

```python

# Severidad para combinar veredictos (mayor = peor). UNKNOWN va por encima de
# TRUSTED: "no sé" nunca debe tapar un problema ni pasar por bueno.
_TRUST_SEVERITY = {
    TRUST_TRUSTED: 0,
    TRUST_UNKNOWN: 1,
    TRUST_CAUTION: 2,
    TRUST_SUSPICIOUS: 3,
}
```

Debajo de la clase `TrustInfo` (antes de `class Connection`) agregar:

```python
def worst_trust(infos: Iterable[TrustInfo]) -> TrustInfo:
    """El veredicto MÁS severo de varios ejecutables que se muestran con el
    mismo nombre. El FileDescription es spoofeable: un 'Google Chrome' falso
    en AppData debe volver sospechosa la fila, no heredar la confianza del
    Chrome real. Ante empate gana el primero (el caller ordena las rutas)."""
    worst: TrustInfo | None = None
    for info in infos:
        if worst is None or (_TRUST_SEVERITY.get(info.level, 1)
                             > _TRUST_SEVERITY.get(worst.level, 1)):
            worst = info
    return worst if worst is not None else TrustInfo(level=TRUST_UNKNOWN)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_models.py`
Expected: PASS (todos, incluidos los 5 nuevos).

- [ ] **Step 5: Commit**

```bash
git add src/domain/models.py tests/test_models.py
git commit -m "feat(domain): worst_trust combina veredictos por severidad"
```

---

### Task 2: Cache de nombres por PID con invalidación por `create_time`

**Files:**
- Modify: `src/infrastructure/capture/app_names.py`
- Modify: `src/infrastructure/capture/etw_capture.py` (sólo comentario en `_resolve_name`)
- Test: `tests/test_app_names.py` (nuevo)

**Interfaces:**
- Consumes: `psutil.Process(pid).create_time()/exe()/name()`, `_file_description(path)` (existente; `trust.py` lo importa — NO renombrar).
- Produces: `friendly_name(pid) -> str` (misma firma). Nuevos internos: `_lock`, `_pid_cache: OrderedDict[int, tuple[float, str, float]]` (create_time, nombre, verificado_en), `_path_cache: OrderedDict[str, str]`, `_MAX_PIDS = 4096`, `_MAX_PATHS = 2048`, `_REVALIDATE_S = 5.0`, `_now = time.monotonic`, `_reset_caches()` (sólo tests).

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_app_names.py`:

```python
"""Cache de nombres amigables por PID (plan 04).

Bug original: `_pid_cache` nunca se invalidaba -> un PID reciclado heredaba el
nombre de la app anterior; el fallback "PID n" quedaba cacheado para siempre;
crecía sin límite y sin lock (ETW + worker lo tocan en paralelo).
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

import psutil
import pytest

from src.infrastructure.capture import app_names as an

_DESCS = {"C:/a/chrome.exe": "Google Chrome", "C:/b/evil.exe": "Evil Tool"}


def _fake_psutil(table: dict):
    """table: pid -> (create_time, exe | None, name). Ausente = NoSuchProcess.
    exe None = AccessDenied al pedir la ruta (proceso protegido)."""

    class Proc:
        def __init__(self, pid):
            if pid not in table:
                raise psutil.NoSuchProcess(pid)
            self._pid = pid

        def create_time(self):
            if self._pid not in table:
                raise psutil.NoSuchProcess(self._pid)
            return table[self._pid][0]

        def exe(self):
            exe = table[self._pid][1]
            if exe is None:
                raise psutil.AccessDenied(self._pid)
            return exe

        def name(self):
            return table[self._pid][2]

    return SimpleNamespace(Process=Proc, NoSuchProcess=psutil.NoSuchProcess,
                           AccessDenied=psutil.AccessDenied)


@pytest.fixture
def env(monkeypatch):
    table: dict = {}
    clock = [1000.0]
    monkeypatch.setattr(an, "psutil", _fake_psutil(table))
    monkeypatch.setattr(an, "_file_description", lambda path: _DESCS.get(path))
    monkeypatch.setattr(an, "_now", lambda: clock[0])
    an._reset_caches()
    yield table, clock
    an._reset_caches()


def test_recycled_pid_gets_new_name(env):
    table, clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    assert an.friendly_name(42) == "Google Chrome"
    table[42] = (2.0, "C:/b/evil.exe", "evil.exe")   # mismo PID, otro proceso
    clock[0] += an._REVALIDATE_S + 1
    assert an.friendly_name(42) == "Evil Tool"


def test_hit_within_window_does_not_touch_psutil(env):
    table, _clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    assert an.friendly_name(42) == "Google Chrome"
    del table[42]   # si tocara psutil, daría NoSuchProcess
    assert an.friendly_name(42) == "Google Chrome"


def test_same_process_keeps_name_after_revalidation(env):
    table, clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    an.friendly_name(42)
    clock[0] += an._REVALIDATE_S + 1
    assert an.friendly_name(42) == "Google Chrome"
    assert an._pid_cache[42][2] == clock[0]   # verificación renovada


def test_pid_fallback_is_not_cached(env):
    table, _clock = env
    assert an.friendly_name(7) == "PID 7"
    assert 7 not in an._pid_cache
    table[7] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    assert an.friendly_name(7) == "Google Chrome"   # sin esperar ventana


def test_dead_process_evicts_entry(env):
    table, clock = env
    table[42] = (1.0, "C:/a/chrome.exe", "chrome.exe")
    an.friendly_name(42)
    del table[42]
    clock[0] += an._REVALIDATE_S + 1
    assert an.friendly_name(42) == "PID 42"
    assert 42 not in an._pid_cache


def test_access_denied_exe_falls_back_to_process_name(env):
    table, _clock = env
    table[9] = (1.0, None, "svchost.exe")
    assert an.friendly_name(9) == "svchost.exe"


def test_pid_cache_is_bounded(env, monkeypatch):
    table, _clock = env
    monkeypatch.setattr(an, "_MAX_PIDS", 3)
    for pid in range(1, 6):
        table[pid] = (1.0, "C:/a/chrome.exe", "chrome.exe")
        an.friendly_name(pid)
    assert len(an._pid_cache) == 3
    assert list(an._pid_cache) == [3, 4, 5]   # se van los más viejos (LRU)


def test_path_cache_is_bounded(env, monkeypatch):
    monkeypatch.setattr(an, "_MAX_PATHS", 2)
    for i in range(5):
        an._from_path(f"C:/x/app{i}.exe")
    assert len(an._path_cache) == 2


def test_concurrent_access_is_safe(env):
    table, clock = env
    for pid in range(200):
        table[pid] = (float(pid), "C:/a/chrome.exe", "chrome.exe")
    errors: list[BaseException] = []

    def worker(offset):
        try:
            for i in range(2000):
                an.friendly_name((i + offset) % 250)   # incluye PIDs muertos
                if i % 97 == 0:
                    clock[0] += an._REVALIDATE_S + 1
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(k * 31,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(an._pid_cache) <= an._MAX_PIDS
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_app_names.py`
Expected: FAIL — `AttributeError: ... has no attribute '_now'` (el fixture no puede parchear `_now`; también faltan `_reset_caches`, `_REVALIDATE_S`, `_MAX_PIDS`).

- [ ] **Step 3: Implementación mínima**

En `src/infrastructure/capture/app_names.py`:

1. Reemplazar la última línea del docstring (`Cachea por PID y por ruta para no repetir la consulta.`) por:

```
Cachea por PID (validado con create_time: un PID reciclado NO hereda el nombre
anterior) y por ruta. Ambos caches están acotados y protegidos por un lock:
los usan en paralelo el hilo de ETW y el worker del snapshot.
```

2. Reemplazar el bloque de imports + caches:

```python
import ctypes
import struct
import threading
import time
from collections import OrderedDict
from ctypes import wintypes

import psutil

_MAX_PIDS = 4096
_MAX_PATHS = 2048
# Cada cuánto se re-verifica que un PID cacheado siga siendo el MISMO proceso
# (create_time). Entre verificaciones el hit es O(1) y sin syscalls: el
# callback de ETW llama a friendly_name() por cada evento de red.
_REVALIDATE_S = 5.0

_lock = threading.Lock()
# pid -> (create_time, nombre, instante monotónico de la última verificación)
_pid_cache: "OrderedDict[int, tuple[float, str, float]]" = OrderedDict()
_path_cache: "OrderedDict[str, str]" = OrderedDict()
_now = time.monotonic
```

3. Reemplazar `_from_path` y `friendly_name` completos (dejar `_file_description` intacto):

```python
def _remember(cache: OrderedDict, key, value, limit: int) -> None:
    """Inserta como más reciente y descarta los más viejos (LRU). Llamar con _lock."""
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > limit:
        cache.popitem(last=False)


def _from_path(path: str) -> str:
    with _lock:
        hit = _path_cache.get(path)
        if hit is not None:
            _path_cache.move_to_end(path)
            return hit
    desc = _file_description(path)   # IO de disco FUERA del lock
    if not desc:
        # Fallback: nombre del archivo sin extensión.
        base = path.replace("\\", "/").rsplit("/", 1)[-1]
        desc = base[:-4] if base.lower().endswith(".exe") else base
    with _lock:
        _remember(_path_cache, path, desc, _MAX_PATHS)
    return desc


def friendly_name(pid: int) -> str:
    """Nombre amigable de la app dueña del PID; fallback al nombre del proceso."""
    now = _now()
    with _lock:
        hit = _pid_cache.get(pid)
        if hit is not None and now - hit[2] < _REVALIDATE_S:
            _pid_cache.move_to_end(pid)
            return hit[1]
    try:
        proc = psutil.Process(pid)
        created = proc.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
        # Proceso muerto/inaccesible: fallback SIN cachear. El PID se recicla
        # y el próximo dueño no debe heredar "PID n".
        with _lock:
            _pid_cache.pop(pid, None)
        return f"PID {pid}"
    if hit is not None and hit[0] == created:
        name = hit[1]   # mismo proceso: sólo se renueva la verificación
    else:
        try:
            name = _from_path(proc.exe())
        except (psutil.AccessDenied, psutil.NoSuchProcess, FileNotFoundError, OSError):
            try:
                name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                return f"PID {pid}"
    with _lock:
        _remember(_pid_cache, pid, (created, name, now), _MAX_PIDS)
    return name


def _reset_caches() -> None:
    """Sólo para tests: vacía ambos caches."""
    with _lock:
        _pid_cache.clear()
        _path_cache.clear()
```

4. En `src/infrastructure/capture/etw_capture.py`, reemplazar:

```python
    def _resolve_name(self, pid: int) -> str:
        return friendly_name(pid)
```

por:

```python
    def _resolve_name(self, pid: int) -> str:
        # Corre DENTRO del callback de ETW. El primer evento de un PID hace IO
        # (psutil + version.dll); los siguientes son hits O(1) del cache de
        # app_names, re-verificado por create_time cada pocos segundos.
        return friendly_name(pid)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_app_names.py tests/test_infra.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/capture/app_names.py src/infrastructure/capture/etw_capture.py tests/test_app_names.py
git commit -m "fix(capture): cache de nombres por PID invalida por create_time y no cachea el fallback"
```

---

### Task 3: `SnapshotRefresher` (worker de fondo de la capa de aplicación)

**Files:**
- Create: `src/application/snapshot_refresher.py`
- Test: `tests/test_snapshot_refresher.py` (nuevo)

**Interfaces:**
- Consumes: un callable `refresh() -> None` (lo provee `MonitorService.refresh_snapshot` en Task 4).
- Produces: `SnapshotRefresher(refresh, interval=2.0, on_refreshed=None)` con `start()`, `stop(timeout=1.0)` (idempotente, también sin `start`), `trigger()` (no bloquea), `set_listener(cb)`, propiedad `running`. Primer refresco inmediato al arrancar; excepciones de `refresh`/listener se loguean y el loop sigue.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_snapshot_refresher.py`:

```python
"""Worker único de fondo que refresca el snapshot de la UI (plan 04)."""
from __future__ import annotations

import logging
import threading

from src.application.snapshot_refresher import SnapshotRefresher


def test_first_refresh_is_immediate_and_notifies():
    refreshed = threading.Event()
    notified = threading.Event()
    r = SnapshotRefresher(refreshed.set, interval=60, on_refreshed=notified.set)
    r.start()
    try:
        assert refreshed.wait(1)
        assert notified.wait(1)
    finally:
        r.stop()


def test_trigger_wakes_before_interval():
    calls: list[int] = []
    second = threading.Event()

    def refresh():
        calls.append(1)
        if len(calls) >= 2:
            second.set()

    r = SnapshotRefresher(refresh, interval=60)
    r.start()
    try:
        r.trigger()
        assert second.wait(1)   # no esperó los 60 s
    finally:
        r.stop()


def test_exception_does_not_kill_loop(caplog):
    calls: list[int] = []
    recovered = threading.Event()

    def refresh():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        recovered.set()

    r = SnapshotRefresher(refresh, interval=0.01)
    with caplog.at_level(logging.ERROR):
        r.start()
        try:
            assert recovered.wait(1)
        finally:
            r.stop()
    assert "Fallo refrescando el snapshot" in caplog.text


def test_listener_exception_does_not_kill_loop():
    calls: list[int] = []
    again = threading.Event()

    def refresh():
        calls.append(1)
        if len(calls) >= 2:
            again.set()

    def bad_listener():
        raise RuntimeError("widget ya destruido")

    r = SnapshotRefresher(refresh, interval=0.01, on_refreshed=bad_listener)
    r.start()
    try:
        assert again.wait(1)
    finally:
        r.stop()


def test_set_listener_after_construction():
    notified = threading.Event()
    r = SnapshotRefresher(lambda: None, interval=60)
    r.set_listener(notified.set)
    r.start()
    try:
        assert notified.wait(1)
    finally:
        r.stop()


def test_stop_joins_and_is_idempotent():
    r = SnapshotRefresher(lambda: None, interval=60)
    r.stop()                 # sin start: no-op
    r.start()
    assert r.running
    r.stop()
    assert not r.running
    r.stop()                 # dos veces: no-op
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_snapshot_refresher.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.application.snapshot_refresher'`.

- [ ] **Step 3: Implementación mínima**

Crear `src/application/snapshot_refresher.py`:

```python
"""Worker de fondo que mantiene fresco el snapshot que lee la UI.

Un ÚNICO hilo en la capa de aplicación (decisión del spec de release audit):
la UI nunca hace IO (SQLite, psutil, WinVerifyTrust); sólo lee lo que este
hilo dejó listo. Alternativa descartada: QThreadPool en presentación (mete
lógica de negocio en Qt).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

_log = logging.getLogger(__name__)


class SnapshotRefresher:
    def __init__(self, refresh: Callable[[], None], interval: float = 2.0,
                 on_refreshed: Callable[[], None] | None = None) -> None:
        self._refresh = refresh
        self._interval = interval
        self._on_refreshed = on_refreshed
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_listener(self, callback: Callable[[], None] | None) -> None:
        """Callback tras cada refresco. Corre en ESTE hilo: el receptor (UI)
        es responsable de saltar a su propio hilo (ej. señal Qt encolada)."""
        self._on_refreshed = callback

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="netgauge-snapshot", daemon=True)
        self._thread.start()

    def trigger(self) -> None:
        """Pide un refresco ya, sin esperar al intervalo. No bloquea."""
        self._wake.set()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            # Si un refresco está trabado (ej. WinVerifyTrust lento) no
            # bloqueamos el cierre más de `timeout`: el hilo es daemon.
            thread.join(timeout)
        self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._refresh()
            except Exception:  # noqa: BLE001 — el worker nunca muere en silencio
                _log.exception("Fallo refrescando el snapshot de la UI")
            if self._stop.is_set():
                break
            callback = self._on_refreshed
            if callback is not None:
                try:
                    callback()
                except Exception:  # noqa: BLE001
                    _log.exception("Fallo notificando el snapshot a la UI")
            # Un trigger() que llegó DURANTE el refresco deja el evento puesto:
            # wait() vuelve enseguida y se refresca de nuevo (no se pierde).
            self._wake.wait(self._interval)
            self._wake.clear()
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_snapshot_refresher.py`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/application/snapshot_refresher.py tests/test_snapshot_refresher.py
git commit -m "feat(app): SnapshotRefresher, worker de fondo para el snapshot de la UI"
```

---

### Task 4: Cuotas y períodos desde el snapshot (sin SQLite en el hilo GUI)

**Files:**
- Modify: `src/application/monitor_service.py`
- Modify: `tests/test_monitor_service.py` (sólo `test_quota_status_sums_repo_usage`)
- Test: `tests/test_ui_snapshot.py` (nuevo)

**Interfaces:**
- Consumes: `SnapshotRefresher` (Task 3), `UsageRepository.totals_by_app`.
- Produces:
  - `MonitorService.__init__(..., snapshot_interval: float = 2.0)`.
  - `refresh_snapshot() -> None` — un ciclo del worker (público para tests).
  - `set_snapshot_listener(cb) -> None`.
  - `quota_status()` / `daily_status()` — leen snapshot; `used_bytes=0` hasta el primer refresco o si cambió el ciclo/día; `limit_bytes` SIEMPRE desde `self.settings` actual.
  - `usage_for_period(period)` — lee snapshot; si el período cambió dispara UN `trigger()`; devuelve lo último conocido o `[]`.
  - Internos: `_compute_quota_status()`, `_compute_daily_status()`, `_compute_usage_for_period(period)` (con IO, sólo hilos de fondo).
  - `start()` arranca el worker; `stop()` lo detiene; `update_settings()` lo despierta.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_ui_snapshot.py`:

```python
"""Snapshot de la UI (plan 04): los getters que usa MainWindow._refresh NO
hacen IO; el worker de fondo (refresh_snapshot) es el único que consulta
SQLite / psutil / el evaluador de confianza."""
from __future__ import annotations

import threading
import time
from datetime import datetime

from conftest import (
    FakeCapture, FakeRepo, FakeReporter, FakeStore, make_monitor,
)
from src.application.monitor_service import MonitorService
from src.domain.models import UsageRecord


class SpyRepo(FakeRepo):
    def __init__(self, records=None) -> None:
        super().__init__(records)
        self.queries = 0

    def totals_by_app(self, start, end):
        self.queries += 1
        return super().totals_by_app(start, end)


def _monitor(settings, notifier, repo=None, **kw) -> MonitorService:
    m = MonitorService(FakeCapture(), repo or FakeRepo(), FakeReporter(),
                       FakeStore(settings), notifier, **kw)
    m.set_translator(lambda k: k)
    return m


def _wait_until(pred, timeout=2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


# ---- cuotas / períodos ------------------------------------------------------
def test_ui_getters_never_touch_repository(settings, notifier):
    repo = SpyRepo([UsageRecord("A", 100, 200, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    m.quota_status()
    m.daily_status()
    m.usage_for_period("day")
    m.usage_for_period("week")
    assert repo.queries == 0


def test_refresh_snapshot_fills_quotas(settings, notifier):
    settings.monthly_quota_gb = 1.0
    settings.daily_quota_gb = 1.0
    repo = SpyRepo([UsageRecord("A", 100, 200, datetime.now()),
                    UsageRecord("B", 300, 400, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    assert m.quota_status().used_bytes == 0     # aún sin snapshot
    m.refresh_snapshot()
    assert m.quota_status().used_bytes == 1000
    assert m.daily_status().used_bytes == 1000
    assert m.quota_status().has_limit
    before = repo.queries
    m.quota_status()
    m.daily_status()
    assert repo.queries == before               # leer no consulta


def test_quota_limit_follows_settings_without_refresh(settings, notifier):
    settings.monthly_quota_gb = 1.0
    repo = SpyRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    m.refresh_snapshot()
    before = repo.queries
    settings.monthly_quota_gb = 2.0
    m.update_settings(settings)
    st = m.quota_status()
    assert st.limit_bytes == 2 * 1024**3
    assert st.used_bytes == 1000
    assert repo.queries == before


def test_period_snapshot_after_request(settings, notifier):
    repo = SpyRepo([UsageRecord("A", 1, 2, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    assert m.usage_for_period("week") == []     # pedido nuevo: vacío y despierta
    m.refresh_snapshot()
    assert [r.app_name for r in m.usage_for_period("week")] == ["A"]


def test_period_request_wakes_worker_once(settings, notifier):
    m = make_monitor(settings, notifier)
    calls: list[int] = []
    m._refresher.trigger = lambda: calls.append(1)
    m.usage_for_period("day")
    m.usage_for_period("day")
    m.usage_for_period("day")
    assert len(calls) == 1
    m.usage_for_period("month")
    assert len(calls) == 2


def test_start_runs_worker_and_notifies(settings, notifier):
    settings.monthly_quota_gb = 1.0
    repo = SpyRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = _monitor(settings, notifier, repo, snapshot_interval=60)
    ready = threading.Event()
    m.set_snapshot_listener(ready.set)
    m.start()
    try:
        assert ready.wait(2)
        assert m.quota_status().used_bytes == 1000
    finally:
        m.stop()
    assert not m._refresher.running
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_ui_snapshot.py`
Expected: FAIL — `test_ui_getters_never_touch_repository` (`repo.queries == 4`), `AttributeError: 'MonitorService' object has no attribute 'refresh_snapshot'` / `_refresher`, `TypeError: ... unexpected keyword argument 'snapshot_interval'`.

- [ ] **Step 3: Implementación mínima**

En `src/application/monitor_service.py`:

1. **Logger.** Correr `rg -n "getLogger" src/application/monitor_service.py`. El plan 03 define el logger del módulo; si se llama distinto de `_log`, usá ese nombre en todo el código de este plan. Si no hay logger, agregar `import logging` junto a los imports y debajo de ellos `_log = logging.getLogger(__name__)`.

2. **Import** (junto a los imports relativos, debajo del bloque `from ..domain.ports import (...)`):

```python
from .snapshot_refresher import SnapshotRefresher
```

3. **Constructor:** agregar el parámetro al final de la firma de `__init__`, después de `geoip: GeoIpService | None = None,`:

```python
        snapshot_interval: float = 2.0,
```

y al FINAL del cuerpo de `__init__` (después de `self._alert_day: datetime | None = None`):

```python

        # ---- snapshot para la UI (plan 04) ------------------------------
        # La UI SÓLO lee estos campos (getters baratos, sin IO). Los llena el
        # worker de fondo vía refresh_snapshot(). Lock propio: _lock es el del
        # camino caliente de captura y no queremos contención con la UI.
        # Regla: nunca hacer IO con _snap_lock tomado.
        self._snap_lock = threading.Lock()
        self._snap_daily: QuotaStatus | None = None
        self._snap_monthly: QuotaStatus | None = None
        self._snap_periods: dict[str, list[UsageRecord]] = {}
        self._wanted_period: str | None = None
        self._refresher = SnapshotRefresher(self.refresh_snapshot,
                                            interval=snapshot_interval)
```

4. **Ciclo de vida.** En `start()`, como última línea:

```python
        self._refresher.start()
```

En `stop()`, inmediatamente después de `self._running = False`:

```python
        self._refresher.stop()
```

5. **Cuotas.** Reemplazar `quota_status`, `daily_status` y `_check_quota_alerts` (dejar `_cycle_start` y `_usage_since` como están) por:

```python
    @staticmethod
    def _day_start() -> datetime:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def _monthly_limit(self) -> int:
        return int(self.settings.monthly_quota_gb * (1024**3))

    def _daily_limit(self) -> int:
        return int(self.settings.daily_quota_gb * (1024**3))

    def _compute_quota_status(self) -> QuotaStatus:
        """Consulta SQLite: SÓLO desde hilos de fondo (worker / timer de flush)."""
        start = self._cycle_start()
        return QuotaStatus(used_bytes=self._usage_since(start),
                           limit_bytes=self._monthly_limit(), cycle_start=start)

    def _compute_daily_status(self) -> QuotaStatus:
        """Consulta SQLite: SÓLO desde hilos de fondo (worker / timer de flush)."""
        start = self._day_start()
        return QuotaStatus(used_bytes=self._usage_since(start),
                           limit_bytes=self._daily_limit(), cycle_start=start)

    @staticmethod
    def _from_snapshot(snap: QuotaStatus | None, start: datetime,
                       limit: int) -> QuotaStatus:
        # Si el snapshot es de otro ciclo/día (recién cambió), 0 hasta el
        # próximo refresco antes que mostrar el consumo del período anterior.
        used = snap.used_bytes if snap is not None and snap.cycle_start == start else 0
        return QuotaStatus(used_bytes=used, limit_bytes=limit, cycle_start=start)

    def quota_status(self) -> QuotaStatus:
        """Para la UI: lee el snapshot (sin IO). El límite sale de los settings
        actuales para reflejar un cambio de cuota sin esperar al worker."""
        with self._snap_lock:
            snap = self._snap_monthly
        return self._from_snapshot(snap, self._cycle_start(), self._monthly_limit())

    def daily_status(self) -> QuotaStatus:
        """Para la UI: lee el snapshot (sin IO)."""
        with self._snap_lock:
            snap = self._snap_daily
        return self._from_snapshot(snap, self._day_start(), self._daily_limit())

    def _check_quota_alerts(self) -> None:
        # Corre en el timer de flush (fuera del hilo GUI): consulta directo.
        self._check_alerts(self._compute_quota_status(), "monthly",
                           self._alerts_fired, "_alert_cycle")
        self._check_alerts(self._compute_daily_status(), "daily",
                           self._daily_alerts_fired, "_alert_day")
```

6. **update_settings:** agregar como última línea del método:

```python
        self._refresher.trigger()  # límites/flags nuevos: refrescar ya
```

7. **Períodos.** Reemplazar `usage_for_period` por:

```python
    @staticmethod
    def _period_start(period: str) -> datetime:
        now = datetime.now()
        return {
            "day": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": now - timedelta(days=now.weekday(), hours=now.hour,
                                    minutes=now.minute, seconds=now.second),
            "month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        }.get(period, now - timedelta(days=1))

    def _compute_usage_for_period(self, period: str) -> list[UsageRecord]:
        """Consulta SQLite: SÓLO desde el worker."""
        now = datetime.now()
        return self._repo.totals_by_app(self._period_start(period),
                                        now + timedelta(seconds=1))

    def usage_for_period(self, period: str) -> list[UsageRecord]:
        """Para la UI. period in {'day', 'week', 'month'}. Lee el snapshot (sin
        IO); si es un período nuevo despierta al worker UNA vez y devuelve lo
        último conocido (o vacío) hasta que llegue el dato."""
        with self._snap_lock:
            rows = self._snap_periods.get(period)
            changed = period != self._wanted_period
            self._wanted_period = period
        if changed:
            self._refresher.trigger()
        return list(rows) if rows is not None else []
```

8. **Snapshot.** Agregar una sección nueva justo antes de `# ---- consultas para la UI -----` :

```python
    # ---- snapshot para la UI (worker de fondo, plan 04) ----------------
    def set_snapshot_listener(self, callback: Callable[[], None] | None) -> None:
        """Avisa tras cada refresco. Corre en el hilo del worker: la UI debe
        saltar a su hilo (señal Qt encolada)."""
        self._refresher.set_listener(callback)

    def refresh_snapshot(self) -> None:
        """Un ciclo del worker: hace TODO el IO que antes hacía la UI y lo
        publica. Cada paso es independiente: si uno falla, los demás siguen.
        Público para poder testearlo de forma síncrona."""
        for step in (self._refresh_quota_snapshot, self._refresh_period_snapshot):
            try:
                step()
            except Exception:  # noqa: BLE001
                _log.exception("Fallo refrescando %s", step.__name__)

    def _refresh_quota_snapshot(self) -> None:
        daily = self._compute_daily_status()
        monthly = self._compute_quota_status()
        with self._snap_lock:
            self._snap_daily = daily
            self._snap_monthly = monthly

    def _refresh_period_snapshot(self) -> None:
        with self._snap_lock:
            period = self._wanted_period
        if period is None:
            return
        rows = self._compute_usage_for_period(period)
        with self._snap_lock:
            self._snap_periods[period] = rows
```

9. **Test existente.** En `tests/test_monitor_service.py`, `test_quota_status_sums_repo_usage`: insertar `m.refresh_snapshot()` entre `m = make_monitor(settings, notifier, repo)` y `st = m.quota_status()`:

```python
    m = make_monitor(settings, notifier, repo)
    m.refresh_snapshot()   # plan 04: quota_status() lee el snapshot
    st = m.quota_status()
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_ui_snapshot.py tests/test_monitor_service.py tests/test_snapshot_refresher.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/application/monitor_service.py tests/test_ui_snapshot.py tests/test_monitor_service.py
git commit -m "perf(app): cuotas y períodos se leen del snapshot, no de SQLite en el hilo GUI"
```

---

### Task 5: Confianza y conexiones calculadas en el worker

**Files:**
- Modify: `src/application/monitor_service.py`
- Test: `tests/test_ui_snapshot.py`

**Interfaces:**
- Consumes: `TrustEvaluator.evaluate(path)`, `ConnectionProvider.exe_paths()` (todavía `dict[str, str]` en esta task), `ConnectionProvider.connections()`, `_enrich_with_vt` (existente).
- Produces:
  - `trust_for(app)` — sin IO; app nunca vista → `TrustInfo(level=TRUST_UNKNOWN)` ("evaluando") + UN `trigger()` por app; con trust apagado o sin evaluador → UNKNOWN y no encola.
  - `connections()` — sin IO; marca demanda; despierta sólo si la demanda estaba vencida (>`_CONN_DEMAND_S` = 10 s).
  - Internos: `_snap_trust`, `_trust_requested`, `_snap_connections`, `_conn_wanted_at`, `_refresh_trust_snapshot()`, `_refresh_connections_snapshot()`. `_refresh_exe_paths()` (30 s) corre sólo en el worker.

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_ui_snapshot.py`, agregar a los imports de cabecera:

```python
from src.domain.models import (
    TRUST_TRUSTED, TRUST_UNKNOWN, Connection, TrustInfo,
)
```

(dejar `UsageRecord` en su import existente) y agregar al final del archivo:

```python
# ---- confianza / conexiones -------------------------------------------------
# Mapa que devuelve el ConnectionProvider fake. Task 6 lo pasa a frozenset.
CHROME_PATHS = {"Chrome": "C:/chrome.exe"}


class BlockingEvaluator:
    """Evaluador que se traba hasta `release`: simula WinVerifyTrust lento."""

    def __init__(self, level=TRUST_TRUSTED) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self._level = level

    def evaluate(self, path):
        self.calls += 1
        self.entered.set()
        self.release.wait(5)
        return TrustInfo(level=self._level, exe_path=path)


class DictEvaluator:
    def __init__(self, levels: dict, fail: set | None = None) -> None:
        self._levels = levels
        self._fail = fail or set()

    def evaluate(self, path):
        if path in self._fail:
            raise OSError("WinVerifyTrust explotó")
        return TrustInfo(level=self._levels.get(path, TRUST_UNKNOWN), exe_path=path)


class FakeConnProvider:
    def __init__(self, paths=None, conns=None) -> None:
        self.paths = paths or {}
        self.conns = conns or []
        self.conn_calls = 0
        self.path_calls = 0

    def exe_paths(self):
        self.path_calls += 1
        return dict(self.paths)

    def connections(self):
        self.conn_calls += 1
        return list(self.conns)


def test_trust_for_unseen_app_returns_fast_without_evaluating(settings, notifier):
    ev = BlockingEvaluator()
    prov = FakeConnProvider(CHROME_PATHS)
    m = _monitor(settings, notifier, trust_evaluator=ev, connection_provider=prov)
    t0 = time.perf_counter()
    info = m.trust_for("Chrome")
    assert time.perf_counter() - t0 < 0.05
    assert info.level == TRUST_UNKNOWN
    assert ev.calls == 0
    assert prov.path_calls == 0          # ni siquiera psutil.process_iter


def test_worker_fills_trust_in_background(settings, notifier):
    ev = BlockingEvaluator()
    m = _monitor(settings, notifier, trust_evaluator=ev,
                 connection_provider=FakeConnProvider(CHROME_PATHS))
    m.trust_for("Chrome")                # encola la app
    m.start()
    try:
        assert ev.entered.wait(2)        # el WORKER está evaluando (trabado)
        t0 = time.perf_counter()
        assert m.trust_for("Chrome").level == TRUST_UNKNOWN   # GUI no se traba
        assert time.perf_counter() - t0 < 0.05
        ev.release.set()
        assert _wait_until(lambda: m.trust_for("Chrome").level == TRUST_TRUSTED)
    finally:
        ev.release.set()
        m.stop()


def test_trust_for_wakes_worker_once_per_app(settings, notifier):
    m = _monitor(settings, notifier, trust_evaluator=DictEvaluator({}),
                 connection_provider=FakeConnProvider(CHROME_PATHS))
    calls: list[int] = []
    m._refresher.trigger = lambda: calls.append(1)
    for _ in range(3):
        m.trust_for("System")            # sin ruta: nunca se resuelve
    assert len(calls) == 1               # sin bucle UI <-> worker
    m.trust_for("Chrome")
    assert len(calls) == 2


def test_trust_disabled_returns_unknown_and_does_not_enqueue(settings, notifier):
    settings.trust_check_enabled = False
    m = _monitor(settings, notifier, trust_evaluator=DictEvaluator({}),
                 connection_provider=FakeConnProvider(CHROME_PATHS))
    assert m.trust_for("Chrome").level == TRUST_UNKNOWN
    assert m._trust_requested == set()


def test_refresh_evaluates_only_requested_apps(settings, notifier):
    ev = DictEvaluator({"C:/chrome.exe": TRUST_TRUSTED})
    prov = FakeConnProvider(CHROME_PATHS)
    m = _monitor(settings, notifier, trust_evaluator=ev, connection_provider=prov)
    m.refresh_snapshot()                 # nadie pidió nada
    assert prov.path_calls == 0
    m.trust_for("Chrome")
    m.refresh_snapshot()
    assert m.trust_for("Chrome").level == TRUST_TRUSTED


def test_evaluator_failure_on_one_app_does_not_block_others(settings, notifier):
    ev = DictEvaluator({"C:/b.exe": TRUST_TRUSTED}, fail={"C:/a.exe"})
    paths = {"A": "C:/a.exe", "B": "C:/b.exe"}
    if isinstance(next(iter(CHROME_PATHS.values())), frozenset):   # Task 6
        paths = {k: frozenset({v}) for k, v in paths.items()}
    m = _monitor(settings, notifier, trust_evaluator=ev,
                 connection_provider=FakeConnProvider(paths))
    m.trust_for("A")
    m.trust_for("B")
    m.refresh_snapshot()
    assert m.trust_for("A").level == TRUST_UNKNOWN
    assert m.trust_for("B").level == TRUST_TRUSTED


def test_connections_read_snapshot_after_demand(settings, notifier):
    conn = Connection("Chrome", 10, "1.2.3.4", 443, "ESTABLISHED")
    prov = FakeConnProvider(conns=[conn])
    m = _monitor(settings, notifier, connection_provider=prov)
    assert m.connections() == []         # sin psutil en el hilo GUI
    assert prov.conn_calls == 0
    m.refresh_snapshot()
    assert prov.conn_calls == 1
    assert m.connections() == [conn]


def test_connections_not_enumerated_without_demand(settings, notifier):
    prov = FakeConnProvider(conns=[Connection("X", 1, "1.1.1.1", 80, "ESTABLISHED")])
    m = _monitor(settings, notifier, connection_provider=prov)
    m.refresh_snapshot()                 # pestaña nunca mirada
    assert prov.conn_calls == 0


def test_connections_demand_wakes_worker_only_when_stale(settings, notifier):
    m = _monitor(settings, notifier, connection_provider=FakeConnProvider())
    calls: list[int] = []
    m._refresher.trigger = lambda: calls.append(1)
    m.connections()
    m.connections()
    assert len(calls) == 1
    m._conn_wanted_at = time.monotonic() - 60   # demanda vencida
    m.connections()
    assert len(calls) == 2
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_ui_snapshot.py`
Expected: FAIL — `test_trust_for_unseen_app_returns_fast_without_evaluating` se cuelga ~5 s y falla (`ev.calls == 1`, evaluación síncrona), `AttributeError: ... '_trust_requested'`, `prov.conn_calls == 1` en `test_connections_read_snapshot_after_demand`.

- [ ] **Step 3: Implementación mínima**

En `src/application/monitor_service.py`:

1. Agregar `import time` junto a `import threading`. Debajo de `_NEW_APP_BYTES = ...`:

```python
# Las conexiones sólo se enumeran mientras la UI las pidió en los últimos
# N segundos (MainWindow sólo las pide con la pestaña visible).
_CONN_DEMAND_S = 10.0
```

2. Al final del bloque de snapshot en `__init__` (antes de `self._refresher = SnapshotRefresher(...)`):

```python
        self._snap_trust: dict[str, TrustInfo] = {}
        self._trust_requested: set[str] = set()
        self._snap_connections: list[Connection] = []
        self._conn_wanted_at: float | None = None
```

3. En `refresh_snapshot`, ampliar la tupla de pasos:

```python
        for step in (self._refresh_quota_snapshot, self._refresh_period_snapshot,
                     self._refresh_connections_snapshot, self._refresh_trust_snapshot):
```

4. Reemplazar `trust_for` y `connections` (dejar `_refresh_exe_paths`, `_enrich_with_vt` y `geo_for` como están) por:

```python
    def trust_for(self, app_name: str) -> TrustInfo:
        """Para la UI: veredicto del snapshot (sin IO). Una app nunca vista
        devuelve UNKNOWN ("evaluando") y queda encolada para el worker."""
        if self._trust is None or not self.settings.trust_check_enabled:
            return TrustInfo(level=TRUST_UNKNOWN)
        with self._snap_lock:
            info = self._snap_trust.get(app_name)
            is_new = app_name not in self._trust_requested
            self._trust_requested.add(app_name)
        if is_new:
            # Una sola vez por app: una app sin ruta ("System", "PID n")
            # nunca se resuelve y no debe despertar al worker en cada repintado.
            self._refresher.trigger()
        return info if info is not None else TrustInfo(level=TRUST_UNKNOWN)

    def _refresh_trust_snapshot(self) -> None:
        """Worker: evalúa las apps pedidas por la UI. El evaluador cachea por
        ruta, así que sólo la PRIMERA evaluación de cada .exe es cara; VT se
        re-aplica cada ciclo porque su lookup es asíncrono (llega después)."""
        if self._trust is None or not self.settings.trust_check_enabled:
            return
        with self._snap_lock:
            wanted = sorted(self._trust_requested)
        if not wanted:
            return
        self._refresh_exe_paths()
        for app in wanted:
            path = self._exe_paths.get(app)
            if not path:
                continue   # sin .exe conocido: queda lo último (o UNKNOWN)
            try:
                info = self._enrich_with_vt(self._trust.evaluate(path), path)
            except Exception:  # noqa: BLE001 — una app rota no frena a las demás
                _log.exception("Fallo evaluando confianza de %s", app)
                continue
            with self._snap_lock:
                self._snap_trust[app] = info   # de a una: la UI ve progreso

    def connections(self) -> list[Connection]:
        """Para la UI: conexiones del snapshot (sin psutil en el hilo GUI).
        Llamarla marca demanda; el worker sólo enumera mientras haya demanda."""
        if self._conn_provider is None:
            return []
        now = time.monotonic()
        with self._snap_lock:
            stale = (self._conn_wanted_at is None
                     or now - self._conn_wanted_at > _CONN_DEMAND_S)
            self._conn_wanted_at = now
            conns = list(self._snap_connections)
        if stale:
            self._refresher.trigger()
        return conns

    def _refresh_connections_snapshot(self) -> None:
        if self._conn_provider is None:
            return
        with self._snap_lock:
            wanted_at = self._conn_wanted_at
        if wanted_at is None or time.monotonic() - wanted_at > _CONN_DEMAND_S:
            return
        conns = self._conn_provider.connections()
        with self._snap_lock:
            self._snap_connections = conns
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_ui_snapshot.py tests/test_monitor_service.py`
Expected: PASS (incluye `test_trust_for_unknown_without_evaluator` existente).

- [ ] **Step 5: Commit**

```bash
git add src/application/monitor_service.py tests/test_ui_snapshot.py
git commit -m "perf(app): confianza y conexiones se calculan en el worker de fondo"
```

---

### Task 6: `exe_paths` por ruta y peor veredicto entre ejecutables homónimos

**Files:**
- Modify: `src/domain/ports.py`
- Modify: `src/infrastructure/capture/connections.py`
- Modify: `src/application/monitor_service.py`
- Test: `tests/test_connections.py` (nuevo), `tests/test_ui_snapshot.py`

**Interfaces:**
- Consumes: `worst_trust` (Task 1), `friendly_name` (Task 2).
- Produces: `ConnectionProvider.exe_paths() -> dict[str, frozenset[str]]` (nombre visible → TODAS las rutas de .exe que se muestran con ese nombre). `MonitorService._exe_paths: dict[str, frozenset[str]]`. El trust de una fila = `worst_trust` de las rutas, ordenadas, cada una enriquecida con VT.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_connections.py`:

```python
"""PsutilConnectionProvider.exe_paths (plan 04): el nombre visible
(FileDescription) es spoofeable, así que se devuelven TODAS las rutas."""
from __future__ import annotations

from types import SimpleNamespace

from src.infrastructure.capture import connections as cx

REAL = "C:/Program Files/Google/Chrome/chrome.exe"
FAKE = "C:/Users/x/AppData/Local/Temp/chrome.exe"


def test_exe_paths_keeps_every_path_per_name(monkeypatch):
    procs = [
        SimpleNamespace(info={"pid": 1, "exe": REAL}),
        SimpleNamespace(info={"pid": 2, "exe": FAKE}),
        SimpleNamespace(info={"pid": 3, "exe": REAL}),     # duplicado
        SimpleNamespace(info={"pid": 4, "exe": None}),     # sin ruta: se ignora
        SimpleNamespace(info={"pid": 5, "exe": "C:/w/notepad.exe"}),
    ]
    names = {1: "Google Chrome", 2: "Google Chrome", 3: "Google Chrome",
             4: "System", 5: "Notepad"}
    monkeypatch.setattr(cx.psutil, "process_iter", lambda attrs: iter(procs))
    monkeypatch.setattr(cx, "friendly_name", lambda pid: names[pid])
    out = cx.PsutilConnectionProvider().exe_paths()
    assert out == {"Google Chrome": frozenset({REAL, FAKE}),
                   "Notepad": frozenset({"C:/w/notepad.exe"})}
```

En `tests/test_ui_snapshot.py`:

1. Cambiar la constante a frozenset:

```python
# Mapa que devuelve el ConnectionProvider fake: nombre -> rutas (plan 04, Task 6).
CHROME_PATHS = {"Chrome": frozenset({"C:/chrome.exe"})}
```

2. Agregar `TRUST_CAUTION, TRUST_SUSPICIOUS` al import de `src.domain.models`:

```python
from src.domain.models import (
    TRUST_CAUTION, TRUST_SUSPICIOUS, TRUST_TRUSTED, TRUST_UNKNOWN, Connection,
    TrustInfo,
)
```

3. Agregar al final:

```python
# ---- ejecutables homónimos: gana el PEOR veredicto --------------------------
REAL = "C:/Program Files/Google/Chrome/chrome.exe"
FAKE = "C:/Users/x/AppData/Local/Temp/chrome.exe"
SPOOFED = {"Google Chrome": frozenset({REAL, FAKE})}


def test_trust_reports_worst_across_same_named_exes(settings, notifier):
    ev = DictEvaluator({REAL: TRUST_TRUSTED, FAKE: TRUST_CAUTION})
    m = _monitor(settings, notifier, trust_evaluator=ev,
                 connection_provider=FakeConnProvider(SPOOFED))
    m.trust_for("Google Chrome")
    m.refresh_snapshot()
    info = m.trust_for("Google Chrome")
    assert info.level == TRUST_CAUTION
    assert info.exe_path == FAKE


class _PathReputation:
    def __init__(self, by_path): self._by_path = by_path
    def set_api_key(self, key): pass
    def lookup(self, path): return self._by_path.get(path)


def test_vt_detection_on_any_same_named_exe_marks_row_suspicious(settings, notifier):
    settings.virustotal_enabled = True
    settings.virustotal_api_key = "k"
    ev = DictEvaluator({REAL: TRUST_TRUSTED, FAKE: TRUST_TRUSTED})
    m = _monitor(settings, notifier, trust_evaluator=ev,
                 connection_provider=FakeConnProvider(SPOOFED),
                 reputation=_PathReputation({REAL: (0, 70), FAKE: (5, 70)}))
    m.trust_for("Google Chrome")
    m.refresh_snapshot()
    info = m.trust_for("Google Chrome")
    assert info.level == TRUST_SUSPICIOUS
    assert info.vt_malicious == 5
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_connections.py tests/test_ui_snapshot.py`
Expected: FAIL — `test_exe_paths_keeps_every_path_per_name` (devuelve `{"Google Chrome": REAL, ...}` con `str`), y los tests de trust: el fake evaluador recibe un `frozenset` como ruta → `TRUST_UNKNOWN` en vez de `TRUST_TRUSTED`/`TRUST_CAUTION`.

- [ ] **Step 3: Implementación mínima**

1. `src/domain/ports.py`, en `ConnectionProvider` reemplazar `exe_paths`:

```python
    @abstractmethod
    def exe_paths(self) -> dict[str, frozenset[str]]:
        """Mapa app_name -> rutas de TODOS los ejecutables que se muestran con
        ese nombre. El nombre (FileDescription) es spoofeable: dos .exe
        distintos pueden compartirlo, así que la confianza se evalúa por ruta."""
```

2. `src/infrastructure/capture/connections.py`, reemplazar `exe_paths`:

```python
    def exe_paths(self) -> dict[str, frozenset[str]]:
        paths: dict[str, set[str]] = {}
        for proc in psutil.process_iter(["pid", "exe"]):
            try:
                exe = proc.info.get("exe")
                if not exe:
                    continue
                name = friendly_name(proc.info["pid"])
                # NO setdefault(name, exe): un "Google Chrome" falso no debe
                # esconderse detrás de la ruta del real (ni viceversa).
                paths.setdefault(name, set()).add(exe)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {name: frozenset(p) for name, p in paths.items()}
```

3. `src/application/monitor_service.py`:
   - Agregar `worst_trust` al import de `..domain.models` (orden alfabético, al final de la lista: `human_bytes,` → `human_bytes,\n    worst_trust,`).
   - En `__init__`, cambiar `self._exe_paths: dict[str, str] = {}` por:

```python
        self._exe_paths: dict[str, frozenset[str]] = {}
```

   - En `_refresh_trust_snapshot`, reemplazar el cuerpo del `for app in wanted:` por:

```python
        for app in wanted:
            paths = self._exe_paths.get(app)
            if not paths:
                continue   # sin .exe conocido: queda lo último (o UNKNOWN)
            try:
                # VT por ruta ANTES de combinar: una detección en cualquiera
                # de los homónimos vuelve sospechosa la fila.
                info = worst_trust(
                    self._enrich_with_vt(self._trust.evaluate(p), p)
                    for p in sorted(paths))
            except Exception:  # noqa: BLE001 — una app rota no frena a las demás
                _log.exception("Fallo evaluando confianza de %s", app)
                continue
            with self._snap_lock:
                self._snap_trust[app] = info   # de a una: la UI ve progreso
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_connections.py tests/test_ui_snapshot.py tests/test_monitor_service.py tests/test_models.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain/ports.py src/infrastructure/capture/connections.py src/application/monitor_service.py tests/test_connections.py tests/test_ui_snapshot.py
git commit -m "fix(capture): exe_paths por ruta y confianza = peor veredicto entre ejecutables homónimos"
```

---

### Task 7: MainWindow repinta al aviso del snapshot (sin IO en el hilo GUI)

**Files:**
- Modify: `src/presentation/qt/main_window.py`
- Test: `tests/test_main_window_snapshot.py` (nuevo, Windows-only como `test_native_window.py`)

**Interfaces:**
- Consumes: `MonitorService.set_snapshot_listener`, getters de snapshot (Tasks 4–6).
- Produces: `MainWindow.snapshot_ready = Signal()` conectada a `_refresh` con `QueuedConnection`. El `_tick` de 1 s ya NO llama `_refresh` (el repintado de datos lo marca el worker, ~2 s). Las llamadas existentes al monitor dentro de `_refresh` (`session_usage`, `usage_for_period`, `daily_status`, `quota_status`, `trust_for`, `connections`, `geo_for`, `settings`) NO cambian de nombre.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_main_window_snapshot.py`:

```python
"""Smoke test (plan 04): MainWindow._refresh corre en el hilo GUI y NO debe
hacer IO (SQLite, psutil, evaluación de firma). Todo eso es del worker."""
from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32",
                                reason="widgets Qt reales: sólo en Windows")

from PySide6.QtWidgets import QApplication  # noqa: E402

from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from src.domain.models import Settings, TrafficSample  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402


class _NoIoRepo(FakeRepo):
    def __init__(self) -> None:
        super().__init__()
        self.queries = 0

    def totals_by_app(self, start, end):
        self.queries += 1
        return []


class _ExplodingEvaluator:
    def evaluate(self, path):
        raise AssertionError("evaluate() en el hilo GUI")


class _ExplodingProvider:
    def exe_paths(self):
        raise AssertionError("process_iter en el hilo GUI")

    def connections(self):
        raise AssertionError("net_connections en el hilo GUI")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_refresh_does_no_io_on_gui_thread(qapp):
    repo = _NoIoRepo()
    m = MonitorService(FakeCapture(), repo, FakeReporter(), FakeStore(Settings()),
                       FakeNotifier(), trust_evaluator=_ExplodingEvaluator(),
                       connection_provider=_ExplodingProvider())
    m._on_sample(TrafficSample(1, "Chrome", bytes_sent=10, bytes_recv=20))
    w = MainWindow(m, per_process=True)
    try:
        for period in ("session", "day", "week", "month"):
            w._set_period(period)
        w._tabs.setCurrentIndex(2)      # pestaña de conexiones visible
        w._refresh()
        assert repo.queries == 0
        assert m._refresher._on_refreshed is not None   # listener enganchado
    finally:
        w._timer.stop()
        m.set_snapshot_listener(None)
        w.deleteLater()


def test_tick_does_not_refresh_data(qapp, monkeypatch):
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    w = MainWindow(m, per_process=True)
    try:
        calls: list[int] = []
        monkeypatch.setattr(w, "_refresh", lambda: calls.append(1))
        for _ in range(4):
            w._tick()
        assert calls == []              # el repintado de datos lo marca el worker
    finally:
        w._timer.stop()
        m.set_snapshot_listener(None)
        w.deleteLater()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest -q tests/test_main_window_snapshot.py`
Expected: FAIL — `test_refresh_does_no_io_on_gui_thread`: `assert m._refresher._on_refreshed is not None` (listener no enganchado); `test_tick_does_not_refresh_data`: `calls == [1, 1]` (el `_tick` refresca cada 2 ticks).

(Si `repo.queries != 0` o salta un `AssertionError` de los fakes, hay una llamada con IO que se escapó de Tasks 4–6: corregir ahí, no en la UI.)

- [ ] **Step 3: Implementación mínima**

En `src/presentation/qt/main_window.py`:

1. Import:

```python
from PySide6.QtCore import QPoint, Qt, QTimer, Signal
```

2. En `class MainWindow(QWidget):`, como primera línea del cuerpo de la clase (antes de `def __init__`):

```python
    # Aviso del worker de MonitorService: "hay snapshot nuevo". Se emite desde
    # OTRO hilo; la conexión encolada garantiza que _refresh corre en el GUI.
    snapshot_ready = Signal()
```

3. En `__init__`, borrar la línea `self._data_ticks = 0`, y reemplazar:

```python
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._refresh()
```

por:

```python
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        # Los datos pesados (SQLite, psutil, firma de .exe) los calcula el
        # worker de MonitorService; acá sólo se repinta cuando avisa.
        self.snapshot_ready.connect(self._refresh, Qt.ConnectionType.QueuedConnection)
        monitor.set_snapshot_listener(self.snapshot_ready.emit)
        self._refresh()
```

4. En `_tick`, borrar las tres últimas líneas:

```python
        self._data_ticks += 1
        if self._data_ticks % 2 == 0:
            self._refresh()
```

(el resto de `_tick` — gráfico y velocidad en vivo — queda igual).

5. Verificar que no quedan referencias: `rg -n "_data_ticks" src/` → sin resultados.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `python -m pytest -q tests/test_main_window_snapshot.py tests/test_native_window.py`
Expected: PASS en Windows (en otros OS: SKIPPED).

- [ ] **Step 5: Commit**

```bash
git add src/presentation/qt/main_window.py tests/test_main_window_snapshot.py
git commit -m "perf(ui): MainWindow repinta al aviso del snapshot, sin IO en el hilo GUI"
```

---

### Task 8: Verificación de la suite completa (sin commit)

**Files:** ninguno.

**Interfaces:** —

- [ ] **Step 1: Suite completa**

Run: `python -m pytest -q`
Expected: PASS, sin tests colgados (los de threading terminan en < 5 s en total).

- [ ] **Step 2: Estabilidad de los tests con hilos (5 corridas)**

Run (bash): `for i in 1 2 3 4 5; do python -m pytest -q tests/test_snapshot_refresher.py tests/test_ui_snapshot.py tests/test_app_names.py tests/test_main_window_snapshot.py || break; done`
Expected: 5 corridas verdes seguidas. Si alguna es intermitente, NO subir timeouts a ciegas: revisar el orden `wait()/clear()` del refresher y que ningún test dependa del intervalo de 2 s.

- [ ] **Step 3: Chequeo de capas**

Run: `rg -n "PySide6|QThread" src/application/`
Expected: sin resultados (el worker vive en aplicación sin Qt).

Run: `rg -n "_compute_|totals_by_app|\.evaluate\(|process_iter|net_connections" src/presentation/`
Expected: sin resultados.

---

## Self-review

- **Cobertura del alcance:** trust en worker con UNKNOWN mientras evalúa (Task 5), exe_paths cada 30 s en worker (Task 5, `_refresh_exe_paths` sólo se llama desde `_refresh_trust_snapshot`), conexiones en worker con demanda (Task 5), cuotas/diario/período en worker (Task 4), `geo_for` se queda (no bloqueante por contrato, justificado en Review Focus), cache de PID por `create_time` + fallback sin cachear + lock + cota (Task 2), worst trust por ruta (Tasks 1 y 6), nota ETW (Task 2 comentario + Review Focus), UI mínima y mecánica con smoke test Qt (Task 7).
- **Consistencia de nombres:** `refresh_snapshot`, `set_snapshot_listener`, `_snap_lock`, `_refresh_quota_snapshot`, `_refresh_period_snapshot`, `_refresh_connections_snapshot`, `_refresh_trust_snapshot`, `_compute_quota_status`, `_compute_daily_status`, `_compute_usage_for_period`, `_trust_requested`, `_conn_wanted_at`, `_CONN_DEMAND_S`, `snapshot_ready` — usados igual en código y tests.
- **Transición Task 5 → 6:** en Task 5 el fake devuelve `str`; Task 6 cambia la constante `CHROME_PATHS` a `frozenset` y `test_evaluator_failure_on_one_app_does_not_block_others` se adapta solo (detecta el tipo de `CHROME_PATHS`). Entre ambas tasks la suite queda verde.
- **Test existente afectado:** sólo `test_quota_status_sums_repo_usage` (Task 4, paso 9). `test_quota_alert_fires_once_per_threshold` sigue verde porque `_check_quota_alerts` usa `_compute_*`.
- **Riesgo de bucle:** cubierto por `test_trust_for_wakes_worker_once_per_app`, `test_period_request_wakes_worker_once`, `test_connections_demand_wakes_worker_only_when_stale`.
