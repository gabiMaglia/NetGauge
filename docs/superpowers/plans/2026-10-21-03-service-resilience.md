# Resiliencia del servicio y la captura (03-service-resilience) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que ningún error transitorio (SQLite bloqueada, toast caído, callback que revienta, `nettop` que muere, sesión ETW que falla) deje a NetGauge midiendo "en silencio" a medias: los ticks del `MonitorService` se reprograman siempre, el batch pendiente no se pierde, `stop()` no compite con un tick en curso, los hilos de captura sobreviven a errores por iteración, la captura nativa degrada a psutil si muere, y todo queda registrado en `netgauge.log` rotativo.

**Architecture:** Patrón único (decisión del spec): `try/except Exception → log.exception → finally reprogramar`. La capa de aplicación solo usa `logging.getLogger(__name__)` (sin importar infraestructura); la configuración del logging (`RotatingFileHandler` en `data_dir/netgauge.log`) vive en el composition root `main.py`. La concurrencia de `MonitorService` se resuelve con dos locks nuevos (`_sched_lock` para `_running`/timers, `_tick_lock` para serializar `_tick` con el flush final de `stop()`), sin tocar el `_lock` de datos del hot path. La degradación ETW/nettop → psutil se hace con un decorador mínimo `FallbackCaptureService` (implementa el puerto `CaptureService`) que la fábrica arma: el backend nativo expone un hook duck-typed `on_failure` y un flag `failed`. Se eligió esto frente a (a) polling de un flag desde la aplicación (meter conocimiento de backends en la capa de aplicación) o (b) agregar `on_failure` al puerto de dominio (obliga a todos los backends y fakes a implementarlo; YAGNI).

**Tech Stack:** Python 3.14, `threading`, `logging` + `logging.handlers.RotatingFileHandler`, pytest (fakes de `tests/conftest.py`, sin sleeps largos: se llama `_tick`/`_rate_tick`/`_loop` directo o se sincroniza con `threading.Event`).

**Spec:** docs/superpowers/specs/2026-10-21-release-audit-fixes-design.md

## Global Constraints

- Rama `fix/release-audit`. Un commit por tarea, conventional commits en español, **sin** `Co-Authored-By` ni atribución de IA.
- **No buildear** (ni PyInstaller ni instaladores). No tocar `src/infrastructure/persistence/*` (es del plan 02) ni `src/presentation/*`.
- Los planes 01 y 02 corren antes. Se asume que el plan 01 ya movió `import pty` de `nettop_capture.py` a un import lazy. En la Task 7 ese import termina dentro de `_spawn()`; si el plan 01 usó otro mecanismo (p. ej. `try: import pty except ImportError: pty = None` a nivel módulo), conservar ese mecanismo y solo mover el uso de `pty.openpty()` a `_spawn()`.
- Strict TDD: cada tarea arranca con el test en rojo, se verifica el FAIL, luego el mínimo código y el PASS.
- Estilo: comentarios y mensajes de log en español, concisos; `log = logging.getLogger(__name__)` como en `factory.py`/`nettop_capture.py`; `# noqa: BLE001` en los `except Exception` intencionales.
- Comando de tests: `python -m pytest -q` (Windows). Los tests que importan `etw_capture` se marcan `skipif(sys.platform != "win32")` (cadena de imports con `ctypes.windll`).
- Logs de alto volumen (ETW emite cientos de eventos/s) se limitan: nunca `log.exception` por evento sin throttle.

## Review Focus

- **Deadlocks**: `_tick` toma `_tick_lock` y dentro `_lock`; `stop()` toma `_sched_lock` (breve, se suelta) y después `_tick_lock`; `_schedule_*` toma `_sched_lock` y se llama SIEMPRE fuera de `_tick_lock`. Verificar que ningún camino invierta ese orden.
- **No doble conteo**: `_flush` re-mergea el batch fallido sumándolo (no pisando) lo que llegó mientras tanto; psutil y nettop actualizan su base (`prev`/`_prev`) ANTES de llamar a `on_sample`.
- **Auto-join**: `on_failure` se invoca desde el hilo del propio backend y termina llamando a `primary.stop()`; los `stop()` de ETW y nettop no deben hacer `join()` de su propio hilo (`t is not threading.current_thread()`).
- **Carrera stop/relanzamiento de nettop**: `_spawn()` publica `_proc`/`_master_fd` bajo `_proc_lock` solo si `_stop_event` no está seteado; si no, mata lo que acaba de lanzar.
- Tests sin flakiness: ningún `sleep`; las esperas son `Event.wait(timeout)` con timeouts generosos que solo se agotan si hay bug.

---

### Task 1: `_flush` no pierde el batch si `save_batch` falla

**Files:**
- Modify: `src/application/monitor_service.py` (imports + `_flush`)
- Test: `tests/test_monitor_service.py`

**Interfaces:**
- Consumes: `UsageRepository.save_batch(records)` (puede lanzar, p. ej. `sqlite3.OperationalError`).
- Produces: `MonitorService._flush()` — si `save_batch` lanza, el batch vuelve a `_pending` sumado a lo que haya llegado mientras tanto, y la excepción se re-lanza (el caller decide si loguea). Logger de módulo `log`.

- [ ] **Step 1: Escribir el test que falla.** En `tests/test_monitor_service.py`, reemplazar el bloque de imports de arriba por:

```python
"""Tests de la lógica de aplicación: cuotas, anomalías, retención, VT."""
import sqlite3
import threading
from datetime import datetime, timedelta

import pytest

from conftest import FakeNotifier, FakeRepo, make_monitor
from src.domain.models import (
    TRUST_SUSPICIOUS, TRUST_TRUSTED, TRUST_UNKNOWN, TrafficSample, TrustInfo,
    UsageRecord,
)
```

y agregar al final del archivo:

```python
# ---- resiliencia de persistencia (plan 03) --------------------------------
class FlakyRepo(FakeRepo):
    """save_batch falla `failures` veces (p.ej. 'database is locked') y después anda."""

    def __init__(self, failures: int = 1) -> None:
        super().__init__()
        self.failures = failures

    def save_batch(self, records):
        if self.failures > 0:
            self.failures -= 1
            raise sqlite3.OperationalError("database is locked")
        super().save_batch(records)


def _totals(records) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for r in records:
        sent, recv = out.get(r.app_name, (0, 0))
        out[r.app_name] = (sent + r.bytes_sent, recv + r.bytes_recv)
    return out


def test_flush_failure_keeps_batch_for_retry(settings, notifier):
    repo = FlakyRepo(failures=1)
    m = make_monitor(settings, notifier, repo)
    m._on_sample(TrafficSample(1, "A", bytes_sent=100, bytes_recv=200))
    with pytest.raises(sqlite3.OperationalError):
        m._flush()
    # Llegan más bytes mientras la DB estaba caída: se suman al batch pendiente.
    m._on_sample(TrafficSample(1, "A", bytes_sent=1, bytes_recv=2))
    m._flush()
    assert _totals(repo.saved) == {"A": (101, 202)}
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_monitor_service.py::test_flush_failure_keeps_batch_for_retry -q`
Expected: FAIL — `assert {'A': (1, 2)} == {'A': (101, 202)}` (el batch fallido se descartó con `self._pending.clear()`).

- [ ] **Step 3: Implementación mínima.** En `src/application/monitor_service.py`:

Agregar `import logging` junto a `import threading`, y debajo del bloque de imports de dominio (antes de `_SPIKE_FLOOR`):

```python
log = logging.getLogger(__name__)
```

Reemplazar el método `_flush` completo por:

```python
    def _flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            batch, self._pending = self._pending, {}
            now = datetime.now()
            records = [
                UsageRecord(u.app_name, u.bytes_sent, u.bytes_recv, now)
                for u in batch.values()
            ]
        try:
            self._repo.save_batch(records)
        except Exception:
            # No perder el batch: vuelve a pendientes, SUMADO a lo que haya
            # llegado mientras tanto; se reintenta en el próximo tick.
            with self._lock:
                for name, usage in batch.items():
                    pending = self._pending.setdefault(name, AppUsage(name))
                    pending.add(usage.bytes_sent, usage.bytes_recv)
            raise
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_monitor_service.py -q`
Expected: PASS (todos, incluido el nuevo).

- [ ] **Step 5: Commit.**

```bash
git add src/application/monitor_service.py tests/test_monitor_service.py
git commit -m "fix(service): no perder el batch pendiente si save_batch falla"
```

---

### Task 2: `_tick` y `_rate_tick` se reprograman siempre y loguean el error

**Files:**
- Modify: `src/application/monitor_service.py` (`_tick`, `_rate_tick`)
- Test: `tests/test_monitor_service.py`

**Interfaces:**
- Consumes: `_flush` (Task 1, re-lanza), `_check_quota_alerts`, `_check_new_apps`, `_purge_if_due`, `_check_spike`, `Notifier.notify` (puede lanzar).
- Produces: `_tick()` y `_rate_tick()` nunca propagan; cada paso de `_tick` está aislado (si falla el flush igual corren cuotas/purga); siempre terminan en `_schedule_flush()` / `_schedule_rate()` (que no hacen nada si `_running` es False).

- [ ] **Step 1: Escribir los tests que fallan.** Agregar al final de `tests/test_monitor_service.py`:

```python
@pytest.fixture
def running_monitor(settings, notifier):
    """MonitorService marcado como corriendo, sin start() (sin captura ni
    timers iniciales). Los timers que reprogramen los ticks se cancelan en
    stop(); intervalo de flush enorme para que ninguno dispare durante el test."""
    made = []

    def _make(repo=None, notifier_=None):
        m = make_monitor(settings, notifier_ or notifier, repo)
        m._flush_interval = 3600.0
        m._running = True
        made.append(m)
        return m

    yield _make
    for m in made:
        m.stop()


class BoomNotifier(FakeNotifier):
    def notify(self, title, message):
        raise RuntimeError("toast caído")


def test_tick_survives_save_error_and_retries(running_monitor):
    repo = FlakyRepo(failures=1)
    m = running_monitor(repo)
    m._on_sample(TrafficSample(1, "A", bytes_sent=100, bytes_recv=200))
    m._tick()                             # save_batch revienta: no debe propagar
    assert m._flush_timer is not None     # la cadena de timers sigue viva
    assert repo.saved == []
    m._tick()                             # reintento: persiste lo pendiente
    assert _totals(repo.saved) == {"A": (100, 200)}


def test_tick_notifier_error_does_not_skip_purge(settings, running_monitor):
    settings.monthly_quota_gb = 0.0
    settings.daily_quota_gb = 1.0 / (1024**3) * 1000   # ~1000 bytes -> 100%
    settings.retention_days = 30
    repo = FakeRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = running_monitor(repo, BoomNotifier())
    m._tick()                             # la alerta de cuota revienta en notify
    assert repo.purged_before is not None  # pero la purga igual corrió
    assert m._flush_timer is not None


def test_rate_tick_survives_notifier_error_and_reschedules(running_monitor):
    m = running_monitor(notifier_=BoomNotifier())
    for _ in range(12):
        m._check_spike(100_000)           # historial estable, sin pico
    m._rate_sent = 50_000_000             # pico -> notify revienta
    m._rate_tick()
    assert m.live_rate()[0] == 50_000_000
    assert m._rate_timer is not None      # la velocidad en vivo no se congela
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_monitor_service.py -q -k "tick_survives or notifier_error"`
Expected: FAIL x3 — `sqlite3.OperationalError: database is locked` y `RuntimeError: toast caído` propagan fuera de `_tick`/`_rate_tick`.

- [ ] **Step 3: Implementación mínima.** En `src/application/monitor_service.py` reemplazar `_rate_tick` completo por:

```python
    def _rate_tick(self) -> None:
        try:
            with self._lock:
                raw_up = float(self._rate_sent)
                raw_down = float(self._rate_recv)
                self._rate_sent = 0
                self._rate_recv = 0
                # Suavizado (T-012): promedio móvil sobre las últimas
                # _RATE_WINDOW lecturas crudas de 1s. Solo afecta lo MOSTRADO
                # (_live_up/_live_down); los totales/persistencia ya quedaron
                # actualizados en _on_sample y no se tocan aquí.
                self._raw_up_history.append(raw_up)
                self._raw_down_history.append(raw_down)
                self._live_up = sum(self._raw_up_history) / len(self._raw_up_history)
                self._live_down = sum(self._raw_down_history) / len(self._raw_down_history)
                smoothed_total = self._live_up + self._live_down
            self._check_spike(smoothed_total)
        except Exception:  # noqa: BLE001
            log.exception("Fallo en el tick de velocidad; sigo")
        finally:
            self._schedule_rate()  # la velocidad en vivo nunca se congela
```

y `_tick` completo por:

```python
    def _tick(self) -> None:
        try:
            # Cada paso aislado: si falla el flush (DB bloqueada) igual corren
            # cuotas, apps nuevas y purga; el batch queda pendiente (Task 1).
            for step in (self._flush, self._check_quota_alerts,
                         self._check_new_apps, self._purge_if_due):
                try:
                    step()
                except Exception:  # noqa: BLE001
                    log.exception("Fallo en %s; se reintenta en el próximo tick",
                                  step.__name__)
        finally:
            self._schedule_flush()  # la cadena de timers nunca se corta
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_monitor_service.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit.**

```bash
git add src/application/monitor_service.py tests/test_monitor_service.py
git commit -m "fix(service): reprogramar siempre _tick y _rate_tick y loguear errores"
```

---

### Task 3: `stop()` espera el tick en curso y ningún tick toca el repositorio después

**Files:**
- Modify: `src/application/monitor_service.py` (`__init__`, `start`, `stop`, `_schedule_rate`, `_schedule_flush`, `_tick`)
- Test: `tests/test_monitor_service.py`

**Interfaces:**
- Consumes: `CaptureService.stop()` (puede lanzar), `_flush` (puede lanzar).
- Produces: contrato de `stop()`: al retornar, (1) no hay timers vivos ni se crean nuevos, (2) no hay un `_tick` ejecutándose, (3) cualquier `_tick` que dispare después no toca el repositorio. `stop()` no propaga errores de `capture.stop()` ni del flush final (los loguea). `main.py` puede cerrar el repositorio con seguridad después de `stop()`.

- [ ] **Step 1: Escribir los tests que fallan.** Agregar al final de `tests/test_monitor_service.py`:

```python
def test_tick_after_stop_does_not_touch_repository(settings, notifier):
    repo = FakeRepo()
    m = make_monitor(settings, notifier, repo)
    m.start()
    m._on_sample(TrafficSample(1, "A", bytes_sent=10, bytes_recv=10))
    m.stop()                               # flush final: 1 registro
    saved_at_stop = len(repo.saved)
    m._on_sample(TrafficSample(1, "A", bytes_sent=5, bytes_recv=5))  # muestra tardía
    m._tick()                              # un Timer que ya había disparado
    assert len(repo.saved) == saved_at_stop
    assert m._flush_timer is None


def test_stop_waits_for_in_progress_tick(settings, notifier):
    entered, release = threading.Event(), threading.Event()

    class SlowRepo(FakeRepo):
        def save_batch(self, records):
            entered.set()
            release.wait(5)
            super().save_batch(records)

    repo = SlowRepo()
    m = make_monitor(settings, notifier, repo)
    m.start()
    m._on_sample(TrafficSample(1, "A", bytes_sent=10, bytes_recv=10))
    ticker = threading.Thread(target=m._tick)
    ticker.start()
    assert entered.wait(5)                 # el tick está adentro de save_batch
    stopper = threading.Thread(target=m.stop)
    stopper.start()
    stopper.join(0.3)
    try:
        assert stopper.is_alive(), "stop() debe esperar al tick en curso"
    finally:
        release.set()
        ticker.join(5)
        stopper.join(5)
    assert not stopper.is_alive()
    assert m._flush_timer is None          # el tick terminó sin reprogramarse
    assert _totals(repo.saved) == {"A": (10, 10)}
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_monitor_service.py -q -k "after_stop or waits_for"`
Expected: FAIL x2 — el tick post-stop persiste la muestra tardía (`len(repo.saved)` crece) y `stop()` retorna sin esperar (`AssertionError: stop() debe esperar al tick en curso`).

- [ ] **Step 3: Implementación mínima.** En `src/application/monitor_service.py`:

En `__init__`, debajo de `self._lock = threading.Lock()`:

```python
        # _sched_lock: protege _running y los timers (start/stop vs. ticks).
        # _tick_lock: serializa _tick con el flush final de stop(), para que
        # nada toque el repositorio después de que stop() retorna.
        # Orden: nunca tomar _sched_lock teniendo _tick_lock.
        self._sched_lock = threading.Lock()
        self._tick_lock = threading.Lock()
```

Reemplazar `start` y `stop` por:

```python
    def start(self) -> None:
        with self._sched_lock:
            self._running = True
        self._capture.start(self._on_sample)
        self._schedule_flush()
        self._schedule_rate()

    def stop(self) -> None:
        with self._sched_lock:
            if not self._running:
                return  # idempotente: stop() puede llegar desde quit_app y atexit
            self._running = False
            timers = (self._flush_timer, self._rate_timer)
            self._flush_timer = None
            self._rate_timer = None
        for t in timers:
            if t is not None:
                t.cancel()
        try:
            self._capture.stop()
        except Exception:  # noqa: BLE001
            log.exception("Fallo deteniendo la captura")
        # Espera un _tick en curso y hace el flush final.
        with self._tick_lock:
            try:
                self._flush()
            except Exception:  # noqa: BLE001
                log.exception("Fallo en el flush final al detener el monitor")
```

Reemplazar `_schedule_rate` y `_schedule_flush` por:

```python
    def _schedule_rate(self) -> None:
        with self._sched_lock:
            if not self._running:
                return
            self._rate_timer = threading.Timer(1.0, self._rate_tick)
            self._rate_timer.daemon = True
            self._rate_timer.start()
```

```python
    def _schedule_flush(self) -> None:
        with self._sched_lock:
            if not self._running:
                return
            self._flush_timer = threading.Timer(self._flush_interval, self._tick)
            self._flush_timer.daemon = True
            self._flush_timer.start()
```

Reemplazar `_tick` (versión de la Task 2) por:

```python
    def _tick(self) -> None:
        try:
            with self._tick_lock:
                if not self._running:
                    return  # stop() ya corrió: no tocar el repositorio
                # Cada paso aislado: si falla el flush (DB bloqueada) igual corren
                # cuotas, apps nuevas y purga; el batch queda pendiente.
                for step in (self._flush, self._check_quota_alerts,
                             self._check_new_apps, self._purge_if_due):
                    try:
                        step()
                    except Exception:  # noqa: BLE001
                        log.exception("Fallo en %s; se reintenta en el próximo tick",
                                      step.__name__)
        finally:
            self._schedule_flush()  # fuera de _tick_lock; no-op si ya no corre
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_monitor_service.py -q`
Expected: PASS (todos, incluidos los de las Tasks 1-2).

- [ ] **Step 5: Commit.**

```bash
git add src/application/monitor_service.py tests/test_monitor_service.py
git commit -m "fix(service): stop() espera el tick en curso y no se reprograma tras detener"
```

---

### Task 4: Logging rotativo en `data_dir/netgauge.log`

**Files:**
- Modify: `main.py` (imports, constantes, `_setup_logging`, `main()`)
- Modify: `docs/BUILD.md` (L130), `docs/ARCHITECTURE.md` (L91), `.github/ISSUE_TEMPLATE/bug_report.md` (L25), `.claude/skills/run-netgauge/SKILL.md` (L34 y L45)
- Test: `tests/test_main.py` (nuevo)

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `main._setup_logging(data_dir: Path) -> logging.Handler` — instala (una sola vez) un `RotatingFileHandler` en el root logger apuntando a `data_dir/netgauge.log` (1 MB x 3 backups, UTF-8) y fija el nivel root en INFO. Idempotente: devuelve el handler existente si ya estaba. Reemplaza al `logging.basicConfig(filename=monitor.log)` actual (que además es no-op si el root ya tiene handlers). `monitor.log` sigue en `_MIGRATE_FILES` (es el nombre del log de trafficMe).

- [ ] **Step 1: Escribir el test que falla.** Crear `tests/test_main.py`:

```python
"""Tests del composition root (main.py): logging y cierre ordenado."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler


def test_setup_logging_writes_rotating_netgauge_log(tmp_path):
    from main import _setup_logging

    root = logging.getLogger()
    old_level = root.level
    handler = _setup_logging(tmp_path)
    try:
        assert isinstance(handler, RotatingFileHandler)
        assert handler.maxBytes > 0 and handler.backupCount >= 1
        assert _setup_logging(tmp_path) is handler     # idempotente
        logging.getLogger("netgauge.test").warning("hola log")
        handler.flush()
        assert "hola log" in (tmp_path / "netgauge.log").read_text(encoding="utf-8")
    finally:
        root.removeHandler(handler)
        handler.close()            # Windows: liberar el archivo antes de borrar tmp_path
        root.setLevel(old_level)
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_main.py -q`
Expected: FAIL — `ImportError: cannot import name '_setup_logging' from 'main'`.

- [ ] **Step 3: Implementación mínima.** En `main.py`:

Debajo de `import logging` agregar:

```python
from logging.handlers import RotatingFileHandler
```

Debajo de `_MIGRATE_DIRS = ("reports",)` agregar:

```python
# Log de la app (spec release-audit): rotativo para no crecer sin límite.
_LOG_FILE = "netgauge.log"
_LOG_MAX_BYTES = 1_000_000
_LOG_BACKUPS = 3
```

Debajo de `_data_dir()` agregar:

```python
def _setup_logging(data_dir: Path) -> logging.Handler:
    """Instala el log rotativo `data_dir/netgauge.log` en el root logger.

    Idempotente: si ya está instalado devuelve el mismo handler. No usa
    basicConfig porque es no-op si el root ya tiene handlers.
    """
    path = os.path.abspath(data_dir / _LOG_FILE)
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, RotatingFileHandler) and h.baseFilename == path:
            return h
    handler = RotatingFileHandler(
        path, maxBytes=_LOG_MAX_BYTES, backupCount=_LOG_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler
```

En `main()`, reemplazar el bloque

```python
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=str(data_dir / "monitor.log"),
    )
```

por:

```python
    _setup_logging(data_dir)
```

y en el comentario de arriba cambiar "para que el monitor.log viejo también se preserve" por "para que el monitor.log de trafficMe también se preserve".

- [ ] **Step 4: Actualizar referencias al nombre del log** (README queda para el plan 06, que ya lo prevé):
  - `docs/BUILD.md`: `` `%LOCALAPPDATA%\NetGauge\monitor.log`: `` → `` `%LOCALAPPDATA%\NetGauge\netgauge.log`: ``
  - `docs/ARCHITECTURE.md`: `` `usage.db`, `settings.json`, `monitor.log`, `reports\`. `` → `` `usage.db`, `settings.json`, `netgauge.log` (rotativo, 1 MB x 3), `reports\`. ``
  - `.github/ISSUE_TEMPLATE/bug_report.md`: `` `%LOCALAPPDATA%\NetGauge\monitor.log` `` → `` `%LOCALAPPDATA%\NetGauge\netgauge.log` ``
  - `.claude/skills/run-netgauge/SKILL.md`: `NetGauge/monitor.log"` → `NetGauge/netgauge.log"` y `` `monitor.log`, `settings.json` `` → `` `netgauge.log`, `settings.json` ``

Verificación: `python -c "import pathlib; fs=['docs/BUILD.md','docs/ARCHITECTURE.md','.github/ISSUE_TEMPLATE/bug_report.md','.claude/skills/run-netgauge/SKILL.md']; print([f for f in fs if 'monitor.log' in pathlib.Path(f).read_text(encoding='utf-8')])"`
Expected: `[]`

- [ ] **Step 5: Correr y ver el PASS.**

Run: `python -m pytest tests/test_main.py tests/test_data_migration.py -q`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add main.py tests/test_main.py docs/BUILD.md docs/ARCHITECTURE.md .github/ISSUE_TEMPLATE/bug_report.md .claude/skills/run-netgauge/SKILL.md
git commit -m "fix(app): log rotativo en netgauge.log en lugar de monitor.log sin límite"
```

---

### Task 5: Cierre ordenado con `try/finally` (el repositorio se cierra siempre)

**Files:**
- Modify: `main.py` (`_shutdown` nuevo, `_on_exit`)
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `MonitorService.generate_session_report()`, `MonitorService.stop()`, `UsageRepository.close()`.
- Produces: `main._shutdown(monitor, repository) -> None` — informe (errores logueados), `stop()` (errores logueados), y `repository.close()` en `finally`. `_on_exit` delega en él (se mantiene como closure porque el handler de señales hace `atexit.unregister(_on_exit)`).

- [ ] **Step 1: Escribir los tests que fallan.** Agregar al final de `tests/test_main.py`:

```python
class _Repo:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_shutdown_closes_repository_even_if_stop_fails():
    from main import _shutdown

    class BoomMonitor:
        def generate_session_report(self): return ""
        def stop(self): raise RuntimeError("timer colgado")

    repo = _Repo()
    _shutdown(BoomMonitor(), repo)        # no propaga
    assert repo.closed is True


def test_shutdown_stops_monitor_even_if_report_fails():
    from main import _shutdown

    class Monitor:
        stopped = False
        def generate_session_report(self): raise OSError("disco lleno")
        def stop(self): Monitor.stopped = True

    repo = _Repo()
    _shutdown(Monitor(), repo)
    assert Monitor.stopped is True and repo.closed is True
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_main.py -q -k shutdown`
Expected: FAIL x2 — `ImportError: cannot import name '_shutdown' from 'main'`.

- [ ] **Step 3: Implementación mínima.** En `main.py`, agregar `from src.domain.ports import UsageRepository` junto a los imports de `src.application`, y debajo de `_setup_logging` agregar:

```python
def _shutdown(monitor: MonitorService, repository: UsageRepository) -> None:
    """Cierre ordenado: informe de sesión, stop del monitor y cierre de la DB.

    El repositorio se cierra SIEMPRE, aunque stop() falle (antes, una
    excepción en stop() dejaba la DB abierta).
    """
    try:
        try:
            monitor.generate_session_report()
        except Exception:  # noqa: BLE001
            logging.exception("Fallo generando informe de cierre")
        monitor.stop()
    except Exception:  # noqa: BLE001
        logging.exception("Fallo deteniendo el monitor")
    finally:
        repository.close()
```

En `main()`, reemplazar el cuerpo de `_on_exit` por:

```python
    def _on_exit() -> None:
        _shutdown(monitor, repository)
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_main.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit.**

```bash
git add main.py tests/test_main.py
git commit -m "fix(app): cerrar el repositorio siempre al salir aunque stop() falle"
```

---

### Task 6: El loop de psutil no muere ante un error de una iteración

**Files:**
- Modify: `src/infrastructure/capture/psutil_fallback.py`
- Test: `tests/test_capture_resilience.py` (nuevo)

**Interfaces:**
- Consumes: `psutil.net_io_counters()` (puede lanzar), `on_sample` (puede lanzar).
- Produces: `PsutilCaptureService._loop` con `try/except` por iteración y log; la base `prev` se actualiza ANTES de `on_sample` (un callback que falla no re-cuenta el delta). Espera con `self._stop_event.wait(interval)` en lugar de `time.sleep` (stop() responde enseguida).

- [ ] **Step 1: Escribir el test que falla.** Crear `tests/test_capture_resilience.py`:

```python
"""Resiliencia de los backends de captura (plan 03): los loops sobreviven a
errores por iteración y la captura nativa degrada a psutil si muere."""
from __future__ import annotations

import threading
from types import SimpleNamespace


def test_psutil_loop_survives_on_sample_error(monkeypatch):
    import src.infrastructure.capture.psutil_fallback as mod

    counters = {"n": 0}

    def fake_counters():
        counters["n"] += 100
        return SimpleNamespace(bytes_sent=counters["n"], bytes_recv=counters["n"])

    monkeypatch.setattr(mod.psutil, "net_io_counters", fake_counters)
    calls = []
    second = threading.Event()

    def on_sample(sample):
        calls.append(sample)
        if len(calls) == 1:
            raise RuntimeError("UI caída")
        second.set()

    svc = mod.PsutilCaptureService(interval=0.01)
    svc.start(on_sample)
    try:
        assert second.wait(2), "el loop murió tras el primer error"
    finally:
        svc.stop()
    assert calls[1].bytes_sent == 100   # delta normal, sin re-contar el fallido
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_capture_resilience.py -q`
Expected: FAIL — `AssertionError: el loop murió tras el primer error` (el hilo terminó con `RuntimeError: UI caída`).

- [ ] **Step 3: Implementación mínima.** En `src/infrastructure/capture/psutil_fallback.py`:

Reemplazar `import time` por `import logging`, y debajo de `_GLOBAL_APP = "Sistema (global)"` agregar:

```python
log = logging.getLogger(__name__)
```

Reemplazar `_loop` completo por:

```python
    def _loop(self, on_sample: Callable[[TrafficSample], None]) -> None:
        prev = None
        while True:
            try:
                cur = psutil.net_io_counters()
                # La base avanza ANTES de on_sample: si el callback falla,
                # el próximo delta no re-cuenta estos bytes.
                base, prev = prev, cur
                if base is not None:
                    sent = max(0, cur.bytes_sent - base.bytes_sent)
                    recv = max(0, cur.bytes_recv - base.bytes_recv)
                    if sent or recv:
                        on_sample(
                            TrafficSample(
                                pid=0, app_name=_GLOBAL_APP,
                                bytes_sent=sent, bytes_recv=recv,
                            )
                        )
            except Exception:  # noqa: BLE001
                log.exception("psutil: fallo en una iteración de captura; sigo")
            if self._stop_event.wait(self._interval):
                return
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_capture_resilience.py -q`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/infrastructure/capture/psutil_fallback.py tests/test_capture_resilience.py
git commit -m "fix(capture): el loop de psutil sobrevive a errores por iteración"
```

---

### Task 7: nettop tolera errores por bloque y se relanza con backoff acotado

**Files:**
- Modify: `src/infrastructure/capture/nettop_capture.py` (`__init__`, `start`, `_spawn`/`_respawn`/`_terminate`/`_close_fd`/`_give_up` nuevos, `_loop`, `_pump` nuevo, `_emit_deltas`, `stop`)
- Test: `tests/test_nettop_capture.py`

**Interfaces:**
- Consumes: `iter_lines_from_fd` (global del módulo, monkeypatcheable), `split_into_blocks`, `parse_nettop_block`.
- Produces:
  - `NettopCaptureService.failed: bool` y `NettopCaptureService.on_failure: Callable[[], None] | None` (hook duck-typed que usa `FallbackCaptureService` en la Task 9).
  - `_emit_deltas` actualiza `_prev` antes de emitir y aísla cada `on_sample` (error logueado, muestra descartada, sin doble conteo).
  - `_loop`: si `nettop` termina sin `stop()`, lo relanza con backoff exponencial (`_RESTART_BASE_DELAY` x 2^n, tope `_RESTART_MAX_DELAY`); tras `_MAX_RESTARTS` fallas SEGUIDAS (corridas sin ningún bloque) se rinde: `failed = True` y llama `on_failure()`. Una corrida con datos resetea el contador.
  - `_spawn()` publica `_proc`/`_master_fd` bajo `_proc_lock` solo si no hubo `stop()`.

- [ ] **Step 1: Escribir los tests que fallan.** Agregar al final de `tests/test_nettop_capture.py`:

```python
# --- plan 03: resiliencia del loop (errores por bloque + relanzamiento) ---

_HDR = ",bytes_in,bytes_out,"


def _no_resolve(svc, monkeypatch):
    monkeypatch.setattr(svc, "_resolve_name", lambda pid, fallback: fallback)


def test_loop_survives_on_sample_error_without_double_counting(monkeypatch):
    import src.infrastructure.capture.nettop_capture as mod

    stream = [_HDR, "A.1,100,100,", _HDR, "A.1,200,200,", _HDR, "A.1,300,300,"]
    monkeypatch.setattr(mod, "iter_lines_from_fd", lambda fd, ev: iter(stream))
    svc = NettopCaptureService()
    svc._master_fd = -1
    svc._MAX_RESTARTS = 0          # sin relanzar: al cortarse el stream se rinde
    _no_resolve(svc, monkeypatch)
    calls = []

    def on_sample(sample):
        calls.append(sample)
        if len(calls) == 1:
            raise RuntimeError("UI caída")

    svc._loop(on_sample)
    assert [c.bytes_recv for c in calls] == [100, 100]


def test_loop_restarts_nettop_with_backoff_and_gives_up(monkeypatch):
    import src.infrastructure.capture.nettop_capture as mod

    feeds = iter([[_HDR, "A.1,100,100,"], [_HDR, "A.1,150,150,"]])
    monkeypatch.setattr(
        mod, "iter_lines_from_fd", lambda fd, ev: iter(next(feeds, []))
    )
    svc = NettopCaptureService()
    svc._master_fd = -1
    svc._RESTART_BASE_DELAY = 0.0
    _no_resolve(svc, monkeypatch)
    respawns = []
    monkeypatch.setattr(svc, "_respawn", lambda: respawns.append(1))
    failed = []
    svc.on_failure = lambda: failed.append(True)
    samples = []

    svc._loop(samples.append)

    # El 2º nettop retoma con la base previa: delta 50, sin perder ni duplicar.
    assert [(s.bytes_recv, s.bytes_sent) for s in samples] == [(50, 50)]
    # 2 corridas con datos (cada una resetea el contador) + _MAX_RESTARTS
    # relanzamientos seguidos sin datos -> se rinde y avisa.
    assert len(respawns) == svc._MAX_RESTARTS + 1
    assert svc.failed is True and failed == [True]
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_nettop_capture.py -q -k "loop_survives or loop_restarts"`
Expected: FAIL x2 — el primero corta en el bloque 2 (`[100] != [100, 100]`); el segundo no relanza (`len(respawns) == 0`, `AttributeError`/`assert` sobre `failed`).

- [ ] **Step 3: Implementación mínima.** En `src/infrastructure/capture/nettop_capture.py`:

En la clase, debajo de `_MAX_MISSING_TICKS = 3`:

```python
    # Relanzamiento si `nettop` muere solo: backoff 1, 2, 4, 8, 16 s (tope 30)
    # y se rinde tras _MAX_RESTARTS corridas seguidas sin datos.
    _MAX_RESTARTS = 5
    _RESTART_BASE_DELAY = 1.0
    _RESTART_MAX_DELAY = 30.0
```

En `__init__`, debajo de `self._name_cache: dict[int, str] = {}`:

```python
        self._proc_lock = threading.Lock()
        # Salud: si nettop no se puede sostener, failed=True y se avisa a
        # on_failure (lo engancha FallbackCaptureService para degradar a psutil).
        self.failed = False
        self.on_failure: Callable[[], None] | None = None
```

Reemplazar `start` completo por `start` + `_spawn` + helpers (conservar el `import pty` lazy del plan 01 dentro de `_spawn`):

```python
    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self.reap_orphans()
        cmd = self._build_command()
        self._stop_event.clear()
        self._prev = {}
        self._name_cache = {}
        self.failed = False
        self._spawn(cmd)
        self._thread = threading.Thread(
            target=self._loop, args=(on_sample,), daemon=True
        )
        self._thread.start()

    def _spawn(self, cmd: list[str] | None = None) -> None:
        """Lanza `nettop` y deja listos `_proc`/`_master_fd`.

        Bajo un PTY (en vez de un pipe simple) para que vea su stdout como un
        TTY y use line-buffering: así entrega cada bloque ~1/s en vez de
        bufferear varios y volcarlos en ráfaga (causa raíz de T-011).
        """
        import pty  # lazy (plan 01): `pty` no existe en Windows

        cmd = cmd or self._build_command()
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as exc:
            raise CaptureUnavailable(f"No se pudo abrir un PTY: {exc}") from exc
        try:
            proc = subprocess.Popen(
                cmd, stdout=slave_fd, stderr=subprocess.DEVNULL, close_fds=True,
            )
        except OSError as exc:
            # slave_fd lo cierra el `finally` (corre siempre); acá solo el master
            # para no fugarlo. Cerrar slave en ambos lados sería un doble-close.
            os.close(master_fd)
            raise CaptureUnavailable(f"No se pudo iniciar nettop: {exc}") from exc
        finally:
            os.close(slave_fd)  # el hijo ya tiene su propio fd duplicado
        with self._proc_lock:
            if not self._stop_event.is_set():
                self._proc, self._master_fd = proc, master_fd
                return
        # stop() llegó mientras relanzábamos: no dejar un nettop huérfano.
        self._terminate(proc)
        self._close_fd(master_fd)

    def _respawn(self) -> None:
        """Descarta el nettop muerto y lanza otro (corre en el hilo del loop)."""
        with self._proc_lock:
            proc, self._proc = self._proc, None
            fd, self._master_fd = self._master_fd, None
        self._terminate(proc)
        self._close_fd(fd)
        self._spawn()

    def _terminate(self, proc: subprocess.Popen | None) -> None:
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=self._interval + 2)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    def _close_fd(fd: int | None) -> None:
        if fd is None:
            return
        try:
            os.close(fd)
        except OSError:
            pass

    def _give_up(self) -> None:
        self.failed = True
        callback = self.on_failure
        if callback is not None:
            try:
                callback()
            except Exception:  # noqa: BLE001
                log.exception("nettop: fallo activando el fallback")
```

Reemplazar `_loop` completo por `_loop` + `_pump`:

```python
    def _loop(self, on_sample: Callable[[TrafficSample], None]) -> None:
        failures = 0  # corridas SEGUIDAS sin datos
        while True:
            if self._pump(on_sample):
                failures = 0
            if self._stop_event.is_set():
                return
            # nettop terminó sin que nadie llamara a stop(): relanzar.
            while True:
                if failures >= self._MAX_RESTARTS:
                    log.error("nettop: %d relanzamientos seguidos sin datos; "
                              "abandono la captura nativa.", failures)
                    self._give_up()
                    return
                failures += 1
                delay = min(self._RESTART_MAX_DELAY,
                            self._RESTART_BASE_DELAY * 2 ** (failures - 1))
                log.warning("nettop terminó inesperadamente; reintento %d/%d en %.0fs.",
                            failures, self._MAX_RESTARTS, delay)
                if self._stop_event.wait(delay):
                    return
                try:
                    self._respawn()
                    break
                except Exception:  # noqa: BLE001
                    log.exception("nettop: no se pudo relanzar")

    def _pump(self, on_sample: Callable[[TrafficSample], None]) -> int:
        """Consume la salida del nettop actual hasta EOF o stop().
        Devuelve cuántos bloques procesó."""
        blocks = 0
        try:
            lines = iter_lines_from_fd(self._master_fd, self._stop_event)
            for block in split_into_blocks(lines):
                if self._stop_event.is_set():
                    break
                blocks += 1
                try:
                    parsed = parse_nettop_block(block)
                    # Resolver el nombre real por PID (T-025) antes de los deltas:
                    # nettop trunca el nombre a un ancho fijo (y puede partir un
                    # carácter multibyte -> U+FFFD/"cajas" en la UI).
                    resolved = {
                        pid: (self._resolve_name(pid, name), bin_, bout)
                        for pid, (name, bin_, bout) in parsed.items()
                    }
                    self._emit_deltas(resolved, on_sample)
                except Exception:  # noqa: BLE001
                    log.exception("nettop: fallo procesando un bloque; se descarta")
        except Exception:  # noqa: BLE001
            log.exception("nettop: error leyendo salida")
        return blocks
```

En `_emit_deltas`: (1) debajo de `new_prev: dict[int, tuple[int, int, int]] = {}` agregar `samples: list[TrafficSample] = []`; (2) reemplazar

```python
            if sent or recv:
                on_sample(
                    TrafficSample(
                        pid=pid, app_name=name, bytes_sent=sent, bytes_recv=recv
                    )
                )
```

por

```python
            if sent or recv:
                samples.append(
                    TrafficSample(
                        pid=pid, app_name=name, bytes_sent=sent, bytes_recv=recv
                    )
                )
```

y (3) reemplazar la última línea `self._prev = new_prev` por:

```python
        # La base se actualiza ANTES de emitir: si un on_sample falla, el
        # próximo bloque no re-cuenta lo ya emitido.
        self._prev = new_prev
        for sample in samples:
            try:
                on_sample(sample)
            except Exception:  # noqa: BLE001
                log.exception("nettop: on_sample falló; se descarta la muestra")
```

Reemplazar `stop` completo por:

```python
    def stop(self) -> None:
        self._stop_event.set()
        with self._proc_lock:
            proc, self._proc = self._proc, None
        self._terminate(proc)  # EOF en el PTY: desbloquea el loop
        thread, self._thread = self._thread, None
        # on_failure -> FallbackCaptureService -> stop() corre en el propio hilo.
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self._interval + 2)
        # El fd se cierra DESPUÉS del join: evita que el loop lea un fd reciclado.
        with self._proc_lock:
            fd, self._master_fd = self._master_fd, None
        self._close_fd(fd)
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_nettop_capture.py -q`
Expected: PASS en los dos nuevos y en los de `_emit_deltas`/`start`/fábrica existentes (los de `iter_lines_from_fd` con `os.pipe` + `select` dependen de cómo los haya dejado el plan 01 en Windows; no se tocan acá).

- [ ] **Step 5: Commit.**

```bash
git add src/infrastructure/capture/nettop_capture.py tests/test_nettop_capture.py
git commit -m "fix(capture): nettop tolera errores por bloque y se relanza con backoff"
```

---

### Task 8: ETW con flag de salud, `on_failure` y `stop()` que joinea

**Files:**
- Modify: `src/infrastructure/capture/etw_capture.py`
- Test: `tests/test_etw_capture.py` (nuevo, solo Windows)

**Interfaces:**
- Consumes: sesión de pywintrace (`start()`/`stop()`), vía `_build_session()` (monkeypatcheable).
- Produces:
  - `EtwCaptureService.failed: bool`, `EtwCaptureService.on_failure: Callable[[], None] | None` (mismo contrato duck-typed que nettop).
  - El hilo corre `_run(session)`: si `session.start()` lanza, loguea, `failed = True` y llama `on_failure()`.
  - `_on_event` nunca propaga errores de `on_sample` al callback de pywintrace (log con throttle: 1º error y cada 1000).
  - `stop()`: detiene la sesión, hace `join(timeout=2)` del hilo (salvo que sea el actual) y limpia `_on_sample`.

- [ ] **Step 1: Escribir los tests que fallan.** Crear `tests/test_etw_capture.py`:

```python
"""Resiliencia de la captura ETW (plan 03) con sesiones falsas: sin admin ni pywintrace."""
from __future__ import annotations

import sys
import threading

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="ETW es solo Windows")

if sys.platform == "win32":
    from src.infrastructure.capture.etw_capture import EtwCaptureService


class _FakeSession:
    """Doble de la sesión pywintrace: start() bloquea hasta stop() o falla."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.stopped = threading.Event()

    def start(self) -> None:
        if self.fail:
            raise RuntimeError("StartTrace falló")
        self.stopped.wait(5)

    def stop(self) -> None:
        self.stopped.set()


def test_etw_session_failure_sets_failed_and_calls_on_failure(monkeypatch):
    svc = EtwCaptureService()
    monkeypatch.setattr(svc, "_build_session", lambda: _FakeSession(fail=True))
    fired = threading.Event()
    svc.on_failure = fired.set
    svc.start(lambda sample: None)
    try:
        assert fired.wait(2), "la falla del hilo ETW no se notificó"
        assert svc.failed is True
    finally:
        svc.stop()


def test_etw_on_event_swallows_on_sample_errors(monkeypatch):
    svc = EtwCaptureService()
    monkeypatch.setattr(svc, "_resolve_name", lambda pid: "App")

    def boom(sample):
        raise RuntimeError("UI caída")

    svc._on_sample = boom
    svc._on_event((10, {"PID": 4, "size": 100}))   # no debe propagar a pywintrace


def test_etw_stop_joins_thread_and_clears_callback(monkeypatch):
    svc = EtwCaptureService()
    session = _FakeSession()
    monkeypatch.setattr(svc, "_build_session", lambda: session)
    svc.start(lambda sample: None)
    thread = svc._thread
    svc.stop()
    assert session.stopped.is_set()
    assert thread is not None and not thread.is_alive()
    assert svc._thread is None and svc._on_sample is None
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_etw_capture.py -q`
Expected: FAIL x3 — `la falla del hilo ETW no se notificó`; `RuntimeError: UI caída` propaga desde `_on_event`; `svc._thread`/`svc._on_sample` no se limpian en `stop()`.

- [ ] **Step 3: Implementación mínima.** En `src/infrastructure/capture/etw_capture.py`:

Agregar `import logging` antes de `import threading` y, debajo de los imports del paquete, `log = logging.getLogger(__name__)`.

Reemplazar `__init__` por:

```python
    def __init__(self) -> None:
        self._etw = None
        self._thread: threading.Thread | None = None
        self._on_sample: Callable[[TrafficSample], None] | None = None
        self._sample_errors = 0
        # Salud: si la sesión ETW muere, failed=True y se avisa a on_failure
        # (lo engancha FallbackCaptureService para degradar a psutil).
        self.failed = False
        self.on_failure: Callable[[], None] | None = None
```

En `_on_event`, reemplazar desde `if pid <= 0 or size <= 0 or self._on_sample is None:` hasta el final del método por:

```python
        on_sample = self._on_sample
        if pid <= 0 or size <= 0 or on_sample is None:
            return

        sent = size if event_id in _SENT_EVENTS or event_id in _UDP_SENT else 0
        recv = size if event_id in _RECV_EVENTS or event_id in _UDP_RECV else 0
        if sent == 0 and recv == 0:
            return

        try:
            on_sample(
                TrafficSample(
                    pid=pid,
                    app_name=self._resolve_name(pid),
                    bytes_sent=sent,
                    bytes_recv=recv,
                )
            )
        except Exception:  # noqa: BLE001
            # Nunca propagar al callback de pywintrace (puede matar el consumer).
            # Log con throttle: ETW emite cientos de eventos por segundo.
            if self._sample_errors % 1000 == 0:
                log.exception("ETW: on_sample falló (%d errores)", self._sample_errors + 1)
            self._sample_errors += 1
```

Reemplazar `start` y `stop` por:

```python
    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self._on_sample = on_sample
        self.failed = False
        self._etw = self._build_session()
        self._thread = threading.Thread(
            target=self._run, args=(self._etw,), daemon=True
        )
        self._thread.start()

    def _run(self, session) -> None:
        try:
            session.start()
        except Exception:  # noqa: BLE001
            log.exception("ETW: la sesión de captura falló")
            self.failed = True
            callback = self.on_failure
            if callback is not None:
                try:
                    callback()
                except Exception:  # noqa: BLE001
                    log.exception("ETW: fallo activando el fallback")

    def stop(self) -> None:
        session, self._etw = self._etw, None
        if session is not None:
            try:
                session.stop()
            except Exception:  # noqa: BLE001
                log.debug("ETW: fallo al detener la sesión", exc_info=True)
        thread, self._thread = self._thread, None
        # on_failure -> FallbackCaptureService -> stop() corre en el propio hilo.
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._on_sample = None
```

- [ ] **Step 4: Correr y ver el PASS.**

Run: `python -m pytest tests/test_etw_capture.py -q`
Expected: PASS (3 tests en Windows; "3 skipped" en otras plataformas).

- [ ] **Step 5: Commit.**

```bash
git add src/infrastructure/capture/etw_capture.py tests/test_etw_capture.py
git commit -m "fix(capture): ETW expone salud, avisa la falla del hilo y stop() joinea"
```

---

### Task 9: `FallbackCaptureService` degrada a psutil si la captura nativa muere

**Files:**
- Create: `src/infrastructure/capture/fallback.py`
- Modify: `src/infrastructure/capture/factory.py`
- Test: `tests/test_capture_resilience.py`, `tests/test_nettop_capture.py` (actualizar `test_factory_returns_nettop_backend_on_macos`), `tests/test_etw_capture.py` (test de fábrica Windows)

**Interfaces:**
- Consumes: `CaptureService` (puerto), backend primario con atributo `on_failure` (Tasks 7-8), fábrica `Callable[[], CaptureService]` del fallback (`PsutilCaptureService`).
- Produces: `FallbackCaptureService(primary, make_fallback)` implementa `CaptureService`; propiedades `primary` y `degraded`. Cambia a psutil una sola vez si (a) `primary.start()` lanza o (b) el primario llama `on_failure()`; ignora fallas después de `stop()`. `create_capture_service()` devuelve el backend nativo envuelto (`per_process` sigue en `True`: es lo que se pudo arrancar).

- [ ] **Step 1: Escribir los tests que fallan.** Agregar al final de `tests/test_capture_resilience.py`:

```python
class FakeBackend:
    def __init__(self, fail_on_start: bool = False) -> None:
        self.on_failure = None
        self.fail_on_start = fail_on_start
        self.started_with = None
        self.stopped = 0

    def start(self, on_sample):
        if self.fail_on_start:
            raise RuntimeError("sin sesión")
        self.started_with = on_sample

    def stop(self):
        self.stopped += 1


def _wrap(primary):
    from src.infrastructure.capture.fallback import FallbackCaptureService

    made = []

    def make_fallback():
        made.append(FakeBackend())
        return made[-1]

    return FallbackCaptureService(primary, make_fallback), made


def test_fallback_switches_once_when_primary_fails():
    primary = FakeBackend()
    svc, made = _wrap(primary)
    cb = lambda sample: None
    svc.start(cb)
    assert svc.degraded is False
    primary.on_failure()                # el hilo nativo murió
    primary.on_failure()                # un segundo aviso no duplica
    assert svc.degraded is True and len(made) == 1
    assert made[0].started_with is cb and primary.stopped == 1
    svc.stop()
    assert made[0].stopped == 1


def test_fallback_when_primary_start_raises():
    svc, made = _wrap(FakeBackend(fail_on_start=True))
    svc.start(lambda sample: None)
    assert svc.degraded is True and len(made) == 1


def test_failure_after_stop_is_ignored():
    primary = FakeBackend()
    svc, made = _wrap(primary)
    svc.start(lambda sample: None)
    svc.stop()
    primary.on_failure()
    assert made == [] and svc.degraded is False
```

En `tests/test_nettop_capture.py`, reemplazar el cuerpo de `test_factory_returns_nettop_backend_on_macos` (desde `service, per_process = ...`) por:

```python
    service, per_process = factory_mod.create_capture_service()
    from src.infrastructure.capture.fallback import FallbackCaptureService
    from src.infrastructure.capture.nettop_capture import NettopCaptureService

    assert isinstance(service, FallbackCaptureService)
    assert isinstance(service.primary, NettopCaptureService)
    assert per_process is True
```

En `tests/test_etw_capture.py` agregar al final:

```python
def test_factory_wraps_etw_with_psutil_fallback(monkeypatch):
    import src.infrastructure.capture.factory as factory_mod
    from src.infrastructure.capture.fallback import FallbackCaptureService

    monkeypatch.setattr(factory_mod.sys, "platform", "win32")
    monkeypatch.setattr(factory_mod, "_is_admin", lambda: True)
    monkeypatch.setattr(EtwCaptureService, "_build_session",
                        lambda self: _FakeSession())
    service, per_process = factory_mod.create_capture_service()
    assert isinstance(service, FallbackCaptureService)
    assert isinstance(service.primary, EtwCaptureService)
    assert per_process is True
```

- [ ] **Step 2: Correr y ver el FAIL.**

Run: `python -m pytest tests/test_capture_resilience.py tests/test_nettop_capture.py tests/test_etw_capture.py -q -k "fallback or factory"`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.infrastructure.capture.fallback'`.

- [ ] **Step 3: Implementación mínima.** Crear `src/infrastructure/capture/fallback.py`:

```python
"""Captura con degradación: si el backend nativo por proceso (ETW / nettop)
no arranca o muere en runtime, pasa a psutil (global) en vez de dejar la app
sin medir.

Contrato duck-typed con el primario: expone un atributo `on_failure` que el
primario llama desde su propio hilo cuando ya no puede capturar. No va al
puerto de dominio a propósito (solo los backends nativos lo necesitan).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from ...domain.models import TrafficSample
from ...domain.ports import CaptureService

log = logging.getLogger(__name__)


class FallbackCaptureService(CaptureService):
    def __init__(self, primary: CaptureService,
                 make_fallback: Callable[[], CaptureService]) -> None:
        self._primary = primary
        self._make_fallback = make_fallback
        self._active: CaptureService = primary
        self._on_sample: Callable[[TrafficSample], None] | None = None
        self._lock = threading.Lock()
        self._stopped = True
        primary.on_failure = self._switch  # type: ignore[attr-defined]

    @property
    def primary(self) -> CaptureService:
        return self._primary

    @property
    def degraded(self) -> bool:
        return self._active is not self._primary

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        with self._lock:
            self._on_sample = on_sample
            self._stopped = False
        try:
            self._primary.start(on_sample)
        except Exception:  # noqa: BLE001
            log.exception("La captura nativa no arrancó; uso psutil (global)")
            self._switch()

    def _switch(self) -> None:
        with self._lock:
            if self._stopped or self.degraded or self._on_sample is None:
                return
            log.warning("Captura nativa caída: paso a psutil (medición global).")
            try:
                self._primary.stop()
            except Exception:  # noqa: BLE001
                log.exception("Fallo deteniendo la captura nativa caída")
            fallback = self._make_fallback()
            fallback.start(self._on_sample)
            self._active = fallback

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            active = self._active
        active.stop()
```

En `src/infrastructure/capture/factory.py`, agregar `from .fallback import FallbackCaptureService` debajo de `from ...domain.ports import CaptureService`, y cambiar:

```python
            return EtwCaptureService(), True
```

por

```python
            # Si la sesión ETW muere en runtime, degrada a psutil (plan 03).
            return FallbackCaptureService(EtwCaptureService(), PsutilCaptureService), True
```

y

```python
            return NettopCaptureService(), True
```

por

```python
            # Si nettop no se puede sostener, degrada a psutil (plan 03).
            return FallbackCaptureService(NettopCaptureService(), PsutilCaptureService), True
```

- [ ] **Step 4: Correr y ver el PASS (suite completa).**

Run: `python -m pytest -q`
Expected: PASS (los tests de ETW se saltean fuera de Windows). Repetir 2 veces más para descartar flakiness de los tests con hilos.

- [ ] **Step 5: Commit.**

```bash
git add src/infrastructure/capture/fallback.py src/infrastructure/capture/factory.py tests/test_capture_resilience.py tests/test_nettop_capture.py tests/test_etw_capture.py
git commit -m "feat(capture): degradar a psutil si la captura nativa muere en runtime"
```

---

## Self-review (hecho al escribir el plan)

- **Cobertura del spec (fila 3):** `_tick`/`_rate_tick` se reprograman siempre (Task 2) · `_flush` no pierde el batch (Task 1) · carrera stop/tick (Task 3) · hilos ETW/nettop/psutil no mueren en silencio (Tasks 6-9) · `_on_exit` con try/finally (Task 5) · logging estándar a `data_dir/netgauge.log` con rotación (Task 4). Sin huecos.
- **Consistencia de nombres:** `on_failure`/`failed` iguales en ETW (Task 8), nettop (Task 7) y `FallbackCaptureService` (Task 9). `_totals`/`FlakyRepo` (Task 1) se reusan en Tasks 2-3; `BoomNotifier`/`running_monitor` (Task 2) solo ahí. `_FakeSession` (Task 8) se reusa en la Task 9.
- **El `_tick` de la Task 2 se reemplaza entero en la Task 3** (se agrega `_tick_lock` + guard de `_running`): es intencional para que cada commit quede verde por sí solo.
- **Tests no flaky:** ningún `sleep`; los timers reales que quedan (`Timer(1.0)` de velocidad, flush de 3600 s en el fixture) se cancelan en `stop()`. El único `join(0.3)` (Task 3) solo puede dar falso negativo si `stop()` tarda más de 0.3 s esperando algo que no sea el tick, lo cual no ocurre con fakes.
- **Capas:** `monitor_service.py` solo importa `logging`; la config del handler vive en `main.py`; `FallbackCaptureService` está en infraestructura y depende del puerto de dominio.

## Riesgos / preguntas abiertas

1. **pywintrace `ETW.start()` probablemente NO bloquea** (arranca su propio hilo consumer y retorna). Si es así, el `failed`/`on_failure` de la Task 8 cubre fallas al arrancar la sesión (acceso denegado, sesión duplicada) pero no la muerte posterior del consumer interno de pywintrace. Verificar a mano en Windows como admin; si hace falta, un watchdog que mire "sin eventos ETW por N minutos con tráfico global > 0" sería el siguiente paso (fuera de alcance, YAGNI).
2. **La UI no se entera de la degradación:** `per_process` se pasa a `MainWindow` una sola vez; tras un fallback en runtime la pestaña "Por aplicación" seguirá pensando que es por proceso. `FallbackCaptureService.degraded` queda expuesto para que el plan 04 (worker/snapshot) o el 07 lo muestren.
3. **Rename del log** `monitor.log` → `netgauge.log`: las instalaciones existentes conservan un `monitor.log` huérfano (no se borra). README lo ajusta el plan 06 (ya lo prevé en su pregunta abierta 3).
4. **Rotación con dos instancias en Windows:** si corren dos procesos, `RotatingFileHandler` no puede renombrar el archivo abierto por el otro (`PermissionError` manejado por `logging.handleError`, va a stderr, no crashea). Lo resuelve el single-instance del plan 07.
5. **`stop()` ahora espera un tick en curso** (hasta el timeout de SQLite, 5 s por defecto) antes de retornar: el cierre puede tardar un poco más en el peor caso, a cambio de no escribir en una DB cerrada.
6. **nettop sin `import pty` en Windows:** los tests nuevos de la Task 7 no llaman a `start()`/`_spawn()` (se monkeypatchea `iter_lines_from_fd`/`_respawn`), así que corren en Windows siempre que el plan 01 haya dejado el módulo importable.
