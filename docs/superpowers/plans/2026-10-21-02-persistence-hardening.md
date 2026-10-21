# Persistence Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `usage.db` deje de crecer sin techo (una fila por app por minuto, no por flush de 10 s), que una DB o un `settings.json` dañados nunca impidan el arranque ni borren en silencio la config del usuario, y que la purga devuelva espacio a disco.

**Architecture:** Todo el cambio vive en la capa de infraestructura (`src/infrastructure/persistence/`), detrás de los puertos `UsageRepository` / `SettingsStore` que no cambian de firma. La tabla `usage` pasa a esquema v2 (`minute` + `UNIQUE(app_name, minute)` + UPSERT), migrada con el mecanismo existente `_MIGRATIONS` / `PRAGMA user_version`. La única toca fuera de infraestructura es un bug de borde en `MonitorService.usage_for_period` (inicio de semana con microsegundos) que el bucketing por minuto vuelve visible.

**Tech Stack:** Python 3.14, `sqlite3` stdlib (SQLite 3.50, UPSERT y WAL disponibles), pytest con `tmp_path` / `monkeypatch` / `caplog`.

**Spec:** docs/superpowers/specs/2026-10-21-release-audit-fixes-design.md

## Global Constraints

- Se sigue la decisión "Agregación" del spec al pie de la letra: tabla `usage` con `minute TEXT` (ISO truncado a minuto, `'YYYY-MM-DDTHH:MM'`), `UNIQUE(app_name, minute)`, `save_batch` con `INSERT ... ON CONFLICT DO UPDATE SET bytes += excluded`, migración v2 que recrea la tabla con `GROUP BY app_name, substr(recorded_at,1,16)`. La columna `recorded_at` se mantiene y guarda el inicio del minuto en ISO completo (`'YYYY-MM-DDTHH:MM:00'`) para que `usage_between`, `totals_by_app`, `purge_older_than` y los reportes no cambien.
- Python y SQL truncan igual: `dt.isoformat()[:16]` ≡ `substr(recorded_at, 1, 16)`. Esto absorbe microsegundos (`.123456`) y, si algún día hubiera tz, también lo descarta igual en ambos caminos (hoy `MonitorService._flush` usa `datetime.now()` naive).
- Las firmas de los puertos (`src/domain/ports.py`) NO cambian. `tests/conftest.py::FakeRepo` no se toca.
- Plan 01 (`01-windows-crash-safety`) corre antes: sin él, `python -m pytest -q` completo crashea (ctypes en `trust.py`) o falla la colección (`import pty` en `nettop_capture.py`). Mientras tanto, correr sólo los archivos de test indicados en cada task.
- Strict TDD: test rojo → implementación mínima → verde → commit. Un commit por task.
- Commits: conventional commits en español, SIN `Co-Authored-By` ni atribución de IA.
- No buildear. Comentarios en español, concisos, como el código existente.
- `main.py::_migrate_legacy_data` copia `usage.db` de trafficMe (sin `-wal`/`-shm`; trafficMe nunca usó WAL). La DB copiada es v1 (user_version 0 o 1) y la migración v2 la consolida al abrirla: no hace falta tocar `main.py`. `tests/test_data_migration.py` usa bytes falsos y nunca abre SQLite: no se ve afectado.

## Review Focus

- **Integridad de la migración v1→v2**: totales por app idénticos antes/después; corre en UNA transacción (`BEGIN` explícito, rollback ante error); un crash a mitad deja la DB v1 intacta y se reintenta al próximo arranque (`DROP TABLE IF EXISTS usage_v2` al inicio).
- **DB pre-versionado**: `user_version = 0` con tabla `usage` existente se trata como v1 (el `_migrate` viejo asumía "0 = nueva"; eso hoy dejaría una DB v1 marcada como v2 sin migrar).
- **Recuperación de corrupción acotada**: sólo `SQLITE_CORRUPT` / `SQLITE_NOTADB` disparan el renombrado. `database is locked` (`OperationalError`, p.ej. dos instancias hasta que llegue el plan 07) se propaga y NO renombra la DB sana.
- **Costo de arranque**: la migración (GROUP BY sobre millones de filas) + `VACUUM` corren una única vez al abrir; en DBs infladas puede tardar decenas de segundos y necesita espacio libre ~2× el tamaño de la DB. Se loguea antes y después.
- **Escritura atómica de settings**: `tmp` + `fsync` + `os.replace`; ante fallo el archivo anterior queda intacto y el `.tmp` se borra.

---

### Task 1: Esquema v2 con UPSERT por (app, minuto) + migración v1→v2

**Files:**
- Modify: `src/infrastructure/persistence/sqlite_repository.py` (L1-68: imports, `_SCHEMA`, `_SCHEMA_VERSION`, `_MIGRATIONS`, `__init__`, `_migrate`, `save_batch`; L70-105 sin cambios)
- Modify: `src/domain/models.py:38` (docstring de `UsageRecord`)
- Create: `tests/test_sqlite_repository.py`
- Test: `tests/test_sqlite_repository.py`

**Interfaces:**
- Consumes: `UsageRecord(app_name, bytes_sent, bytes_recv, recorded_at: datetime)` de `src/domain/models.py`; puerto `UsageRepository` de `src/domain/ports.py`.
- Produces: tabla `usage` v2 (`id, app_name, minute, recorded_at, bytes_sent, bytes_recv`, `UNIQUE(app_name, minute)`, índice `idx_usage_recorded_app(recorded_at, app_name)`), `PRAGMA user_version = 2`; helper de módulo `_minute_key(dt) -> str`; método `SqliteUsageRepository._open() -> sqlite3.Connection`; `_migrate` pasa a `@staticmethod _migrate(conn)` (Tasks 2 y 3 lo extienden).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_sqlite_repository.py`:

```python
"""SqliteUsageRepository: agregación por (app, minuto), migración v2, WAL/recuperación, purga."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from src.domain.models import UsageRecord
from src.infrastructure.persistence import sqlite_repository as sr
from src.infrastructure.persistence.sqlite_repository import SqliteUsageRepository

T0 = datetime(2026, 10, 21, 10, 15, 5, 123456)


@pytest.fixture
def repo(tmp_path):
    r = SqliteUsageRepository(tmp_path / "usage.db")
    yield r
    r.close()


def _rows(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(
            "SELECT app_name, minute, recorded_at, bytes_sent, bytes_recv "
            "FROM usage ORDER BY app_name, minute"
        ).fetchall()
    finally:
        conn.close()


def _pragma(path, name):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"PRAGMA {name}").fetchone()[0]
    finally:
        conn.close()


# ---- Task 1: agregación + esquema v2 ------------------------------------

def test_two_batches_same_minute_collapse_into_one_summed_row(repo, tmp_path):
    repo.save_batch([UsageRecord("chrome", 100, 1000, T0)])
    repo.save_batch([UsageRecord("chrome", 50, 500, T0 + timedelta(seconds=40))])

    assert _rows(tmp_path / "usage.db") == [
        ("chrome", "2026-10-21T10:15", "2026-10-21T10:15:00", 150, 1500),
    ]


def test_different_minutes_or_apps_stay_separate(repo, tmp_path):
    repo.save_batch([
        UsageRecord("chrome", 1, 2, T0),
        UsageRecord("chrome", 3, 4, T0 + timedelta(minutes=1)),
        UsageRecord("slack", 5, 6, T0),
    ])

    assert _rows(tmp_path / "usage.db") == [
        ("chrome", "2026-10-21T10:15", "2026-10-21T10:15:00", 1, 2),
        ("chrome", "2026-10-21T10:16", "2026-10-21T10:16:00", 3, 4),
        ("slack", "2026-10-21T10:15", "2026-10-21T10:15:00", 5, 6),
    ]


def test_fresh_db_is_created_with_v2_schema(repo, tmp_path):
    path = tmp_path / "usage.db"
    assert _pragma(path, "user_version") == 2
    conn = sqlite3.connect(path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(usage)")]
        indexes = [row[1] for row in conn.execute("PRAGMA index_list(usage)")]
    finally:
        conn.close()
    assert {"app_name", "minute", "recorded_at", "bytes_sent", "bytes_recv"} <= set(cols)
    assert "idx_usage_recorded_app" in indexes


def test_queries_return_same_totals_after_aggregation(repo):
    day = datetime(2026, 10, 21)
    repo.save_batch([UsageRecord("chrome", 100, 1000, day.replace(hour=9, second=10))])
    repo.save_batch([UsageRecord("chrome", 100, 1000, day.replace(hour=9, second=20))])
    repo.save_batch([UsageRecord("slack", 1, 1, day.replace(hour=23, minute=59, second=59))])
    repo.save_batch([UsageRecord("chrome", 7, 7, day - timedelta(seconds=1))])  # ayer

    totals = repo.totals_by_app(day, day + timedelta(days=1))
    assert [(t.app_name, t.bytes_sent, t.bytes_recv) for t in totals] == [
        ("chrome", 200, 2000), ("slack", 1, 1),
    ]
    rows = repo.usage_between(day, day + timedelta(days=1))
    assert [(r.app_name, r.recorded_at) for r in rows] == [
        ("chrome", datetime(2026, 10, 21, 9, 0)),
        ("slack", datetime(2026, 10, 21, 23, 59)),
    ]


# ---- Task 1: migración v1 → v2 -------------------------------------------

_V1_SCHEMA = """
CREATE TABLE usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name    TEXT    NOT NULL,
    bytes_sent  INTEGER NOT NULL,
    bytes_recv  INTEGER NOT NULL,
    recorded_at TEXT    NOT NULL
);
CREATE INDEX idx_usage_recorded_at ON usage(recorded_at);
CREATE INDEX idx_usage_app ON usage(app_name);
"""

_V1_ROWS = [
    ("chrome", 10, 100, "2026-10-21T10:15:05.123456"),
    ("chrome", 20, 200, "2026-10-21T10:15:15.000001"),
    ("chrome", 30, 300, "2026-10-21T10:15:59"),
    ("chrome", 1, 1, "2026-10-21T10:16:00"),
    ("slack", 5, 5, "2026-10-21T10:15:30.5"),
]


def _build_v1(path, user_version):
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.executemany(
        "INSERT INTO usage (app_name, bytes_sent, bytes_recv, recorded_at) VALUES (?, ?, ?, ?)",
        _V1_ROWS,
    )
    conn.execute(f"PRAGMA user_version = {user_version}")
    conn.commit()
    conn.close()


@pytest.mark.parametrize("user_version", [1, 0])  # 0 = DB anterior al versionado
def test_v1_db_is_migrated_consolidating_rows(tmp_path, user_version):
    path = tmp_path / "usage.db"
    _build_v1(path, user_version)

    SqliteUsageRepository(path).close()

    assert _pragma(path, "user_version") == 2
    assert _rows(path) == [
        ("chrome", "2026-10-21T10:15", "2026-10-21T10:15:00", 60, 600),
        ("chrome", "2026-10-21T10:16", "2026-10-21T10:16:00", 1, 1),
        ("slack", "2026-10-21T10:15", "2026-10-21T10:15:00", 5, 5),
    ]


def test_migration_preserves_grand_totals_and_keeps_upserting(tmp_path):
    path = tmp_path / "usage.db"
    _build_v1(path, 1)

    repo = SqliteUsageRepository(path)
    try:
        day = datetime(2026, 10, 21)
        totals = {t.app_name: (t.bytes_sent, t.bytes_recv)
                  for t in repo.totals_by_app(day, day + timedelta(days=1))}
        assert totals == {"chrome": (61, 601), "slack": (5, 5)}
        # Una fila migrada sigue siendo destino del UPSERT.
        repo.save_batch([UsageRecord("slack", 1, 1, datetime(2026, 10, 21, 10, 15, 45))])
    finally:
        repo.close()
    assert ("slack", "2026-10-21T10:15", "2026-10-21T10:15:00", 6, 6) in _rows(path)


def test_reopening_v2_db_does_not_touch_data(tmp_path):
    path = tmp_path / "usage.db"
    repo = SqliteUsageRepository(path)
    repo.save_batch([UsageRecord("chrome", 1, 2, T0)])
    repo.close()

    SqliteUsageRepository(path).close()

    assert _rows(path) == [("chrome", "2026-10-21T10:15", "2026-10-21T10:15:00", 1, 2)]
```

(`sr` se usa en la Task 3; dejarlo importado desde ahora.)

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/test_sqlite_repository.py -q`
Expected: FAIL — `sqlite3.OperationalError: no such column: minute` en los tests que leen `_rows`, `user_version == 1` en `test_fresh_db_is_created_with_v2_schema`, y `test_queries_return_same_totals_after_aggregation` falla porque `usage_between` devuelve dos filas de chrome con segundos.

- [ ] **Step 3: Implementación mínima**

Reemplazar las líneas 1-68 de `src/infrastructure/persistence/sqlite_repository.py` (todo hasta el final de `save_batch`; desde `usage_between` en adelante queda igual) por:

```python
"""Repositorio SQLite. Thread-safe vía lock; agrega por (app, minuto)."""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ...domain.models import UsageRecord
from ...domain.ports import UsageRepository

_log = logging.getLogger(__name__)

# v2: una fila por (app, minuto). `minute` = 'YYYY-MM-DDTHH:MM' (clave del UPSERT);
# `recorded_at` = el mismo minuto en ISO completo ('...:00'), lo usan las queries.
_TABLE_V2 = """
CREATE TABLE {name} (
    id          INTEGER PRIMARY KEY,
    app_name    TEXT    NOT NULL,
    minute      TEXT    NOT NULL,
    recorded_at TEXT    NOT NULL,
    bytes_sent  INTEGER NOT NULL DEFAULT 0,
    bytes_recv  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (app_name, minute)
)
"""
_INDEX_V2 = (
    "CREATE INDEX IF NOT EXISTS idx_usage_recorded_app "
    "ON usage(recorded_at, app_name)"
)

_SCHEMA_VERSION = 2  # subir y agregar una entrada en _MIGRATIONS al cambiar esquema

# Migraciones por versión destino; cada una corre en una sola transacción.
_MIGRATIONS: dict[int, tuple[str, ...]] = {
    # v1 → v2: consolida las filas por flush (cada 10 s) en una por (app, minuto).
    2: (
        "DROP TABLE IF EXISTS usage_v2",
        _TABLE_V2.format(name="usage_v2"),
        "INSERT INTO usage_v2 (app_name, minute, recorded_at, bytes_sent, bytes_recv) "
        "SELECT app_name, substr(recorded_at, 1, 16), "
        "substr(recorded_at, 1, 16) || ':00', SUM(bytes_sent), SUM(bytes_recv) "
        "FROM usage GROUP BY app_name, substr(recorded_at, 1, 16)",
        "DROP TABLE usage",
        "ALTER TABLE usage_v2 RENAME TO usage",
        _INDEX_V2,
    ),
}


def _minute_key(dt: datetime) -> str:
    """'YYYY-MM-DDTHH:MM': mismo corte que substr(recorded_at, 1, 16) en SQL."""
    return dt.isoformat()[:16]


class SqliteUsageRepository(UsageRepository):
    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = self._open()

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        try:
            self._migrate(conn)
        except BaseException:
            conn.close()
            raise
        return conn

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Crea el esquema o aplica migraciones pendientes según PRAGMA user_version."""
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'usage'"
        ).fetchone() is not None
        if not has_table:  # DB nueva: esquema actual directo
            conn.execute(_TABLE_V2.format(name="usage"))
            conn.execute(_INDEX_V2)
            conn.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            conn.commit()
            return
        # user_version 0 con tabla = DB pre-versionado, que ya tenía el esquema v1.
        current = conn.execute("PRAGMA user_version").fetchone()[0] or 1
        if current >= _SCHEMA_VERSION:
            return
        for target in range(current + 1, _SCHEMA_VERSION + 1):
            _log.info("Migrando usage.db a esquema v%d...", target)
            conn.execute("BEGIN")
            try:
                for stmt in _MIGRATIONS.get(target, ()):
                    conn.execute(stmt)
                conn.execute(f"PRAGMA user_version = {target}")
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
            _log.info("usage.db migrada a v%d.", target)

    def save_batch(self, records: Iterable[UsageRecord]) -> None:
        rows = []
        for r in records:
            minute = _minute_key(r.recorded_at)
            rows.append((r.app_name, minute, minute + ":00", r.bytes_sent, r.bytes_recv))
        if not rows:
            return
        with self._lock:
            self._conn.executemany(
                "INSERT INTO usage (app_name, minute, recorded_at, bytes_sent, bytes_recv) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (app_name, minute) DO UPDATE SET "
                "bytes_sent = bytes_sent + excluded.bytes_sent, "
                "bytes_recv = bytes_recv + excluded.bytes_recv",
                rows,
            )
            self._conn.commit()
```

Notas para quien implementa:
- `conn.execute("BEGIN")` explícito: en el modo legacy de `sqlite3` el DDL (`CREATE`/`DROP`/`ALTER`) no abre transacción implícita; sin el `BEGIN` un crash entre `DROP TABLE usage` y el `RENAME` perdería datos.
- `idx_usage_app` desaparece con la tabla v1: lo cubre el índice implícito de `UNIQUE(app_name, minute)`. `idx_usage_recorded_at` lo reemplaza `idx_usage_recorded_app(recorded_at, app_name)` (rango por fecha de las SUM de cuota + agrupado por app).
- `usage_between`, `totals_by_app` y `purge_older_than` filtran por `recorded_at` comparando strings ISO: siguen funcionando porque `recorded_at` es ISO de longitud fija y los límites de día/mes que usa `MonitorService` caen en inicio de minuto. Verificado por `test_queries_return_same_totals_after_aggregation`.

En `src/domain/models.py:38` cambiar el docstring:

```python
    """Fila histórica persistida (una por app por minuto)."""
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_sqlite_repository.py tests/test_monitor_service.py tests/test_models.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/sqlite_repository.py src/domain/models.py tests/test_sqlite_repository.py
git commit -m "fix(db): agregar uso por (app, minuto) con UPSERT y migración v2"
```

---

### Task 2: WAL + recuperación de `usage.db` corrupta

**Files:**
- Modify: `src/infrastructure/persistence/sqlite_repository.py` (imports; `__init__` y `_open` de la Task 1; nuevo método `_quarantine`)
- Test: `tests/test_sqlite_repository.py` (agregar al final)

**Interfaces:**
- Consumes: `SqliteUsageRepository._open()` / `_migrate(conn)` de la Task 1.
- Produces: conexión con `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`; ante `SQLITE_CORRUPT`/`SQLITE_NOTADB` al abrir, `usage.db` (+ `-wal`/`-shm`) renombrada a `usage.db.corrupt-YYYYmmdd-HHMMSS[...]`, warning en el logger `src.infrastructure.persistence.sqlite_repository`, y DB v2 nueva.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_sqlite_repository.py`:

```python
# ---- Task 2: WAL + recuperación de DB corrupta ---------------------------

def test_db_runs_in_wal_mode(repo, tmp_path):
    assert _pragma(tmp_path / "usage.db", "journal_mode") == "wal"


def test_corrupt_db_is_renamed_and_recreated(tmp_path, caplog):
    path = tmp_path / "usage.db"
    path.write_bytes(b"esto no es una base sqlite" * 200)

    repo = SqliteUsageRepository(path)
    try:
        repo.save_batch([UsageRecord("chrome", 1, 2, T0)])
        assert len(repo.usage_between(T0 - timedelta(hours=1), T0 + timedelta(hours=1))) == 1
    finally:
        repo.close()

    backups = list(tmp_path.glob("usage.db.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes().startswith(b"esto no es una base sqlite")
    assert "corrupta" in caplog.text


def test_non_corruption_errors_are_not_swallowed(tmp_path, monkeypatch):
    def locked(_conn):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(SqliteUsageRepository, "_migrate", staticmethod(locked))
    path = tmp_path / "usage.db"

    with pytest.raises(sqlite3.OperationalError):
        SqliteUsageRepository(path)
    assert not list(tmp_path.glob("usage.db.corrupt-*"))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/test_sqlite_repository.py -q`
Expected: FAIL — `test_db_runs_in_wal_mode` (`'delete' == 'wal'`) y `test_corrupt_db_is_renamed_and_recreated` (`sqlite3.DatabaseError: file is not a database`). `test_non_corruption_errors_are_not_swallowed` ya pasa: es un guard para que el `except` de este task no se trague `OperationalError`.

- [ ] **Step 3: Implementación mínima**

En los imports de `src/infrastructure/persistence/sqlite_repository.py`, agregar `import os` después de `import logging`:

```python
import logging
import os
import sqlite3
```

Reemplazar `__init__` y `_open` (los de la Task 1) por:

```python
    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        try:
            self._conn = self._open()
        except sqlite3.DatabaseError as exc:
            code = getattr(exc, "sqlite_errorcode", None)
            if code not in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB):
                raise  # p.ej. "database is locked": no es corrupción, no tocar
            self._quarantine(exc)
            self._conn = self._open()

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            self._migrate(conn)
        except BaseException:
            conn.close()  # en Windows no se puede renombrar con la conexión abierta
            raise
        return conn

    def _quarantine(self, exc: sqlite3.DatabaseError) -> None:
        """Aparta la DB corrupta (y su WAL/SHM) para arrancar con una limpia."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        for suffix in ("", "-wal", "-shm"):
            src = Path(f"{self._path}{suffix}")
            if src.exists():
                os.replace(src, f"{self._path}.corrupt-{stamp}{suffix}")
        _log.warning("%s corrupta (%s): renombrada a %s.corrupt-%s y recreada.",
                     self._path.name, exc, self._path.name, stamp)
```

Notas:
- `getattr(..., "sqlite_errorcode", None)`: una `OperationalError` creada a mano (o por un driver viejo) no trae el atributo.
- Se mueven también `-wal`/`-shm`: un WAL viejo junto a una DB nueva es basura que SQLite intentaría reconciliar.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_sqlite_repository.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/sqlite_repository.py tests/test_sqlite_repository.py
git commit -m "fix(db): WAL y recuperación de usage.db corrupta al abrir"
```

---

### Task 3: `auto_vacuum` incremental + purga por lotes

**Files:**
- Modify: `src/infrastructure/persistence/sqlite_repository.py` (`_open`: un PRAGMA más; final de `_migrate`: `VACUUM`; constante `_PURGE_CHUNK`; `purge_older_than`)
- Test: `tests/test_sqlite_repository.py` (agregar al final)

**Interfaces:**
- Consumes: `_open()` de la Task 2, `_migrate(conn)` de la Task 1.
- Produces: `PRAGMA auto_vacuum = 2` (INCREMENTAL) en DBs nuevas y migradas; constante de módulo `_PURGE_CHUNK = 5000`; `purge_older_than(cutoff) -> int` (misma firma, ahora por lotes + `incremental_vacuum`).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_sqlite_repository.py`:

```python
# ---- Task 3: purga por lotes + vacuum incremental ------------------------

def test_fresh_db_uses_incremental_auto_vacuum(repo, tmp_path):
    assert _pragma(tmp_path / "usage.db", "auto_vacuum") == 2  # INCREMENTAL


def test_migrated_db_switches_to_incremental_auto_vacuum(tmp_path):
    path = tmp_path / "usage.db"
    _build_v1(path, 1)
    assert _pragma(path, "auto_vacuum") == 0

    SqliteUsageRepository(path).close()

    assert _pragma(path, "auto_vacuum") == 2


def test_purge_deletes_in_chunks_and_counts_all(repo, monkeypatch):
    monkeypatch.setattr(sr, "_PURGE_CHUNK", 3)
    base = datetime(2026, 1, 1)
    repo.save_batch([UsageRecord("app", 1, 1, base + timedelta(minutes=i)) for i in range(10)])
    cutoff = base + timedelta(minutes=7)

    assert repo.purge_older_than(cutoff) == 7
    left = repo.usage_between(base, base + timedelta(days=1))
    assert [r.recorded_at for r in left] == [base + timedelta(minutes=i) for i in (7, 8, 9)]


def test_purge_releases_free_pages(repo, tmp_path):
    base = datetime(2026, 1, 1)
    repo.save_batch([UsageRecord(f"app-{i:05d}" * 4, 1, 1, base) for i in range(5000)])
    path = tmp_path / "usage.db"

    assert repo.purge_older_than(base + timedelta(days=1)) == 5000

    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        assert conn.execute("PRAGMA freelist_count").fetchone()[0] == 0
    finally:
        conn.close()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/test_sqlite_repository.py -q`
Expected: FAIL — `auto_vacuum` vale 0 en los dos primeros; `test_purge_deletes_in_chunks_and_counts_all` falla con `AttributeError: ... has no attribute '_PURGE_CHUNK'`; `test_purge_releases_free_pages` falla con `freelist_count > 0`.

- [ ] **Step 3: Implementación mínima**

En `_open`, agregar el PRAGMA de `auto_vacuum` ANTES de `journal_mode` (sólo surte efecto si la DB todavía no tiene tablas, o tras un `VACUUM`):

```python
        try:
            # auto_vacuum solo aplica a DBs sin tablas (o tras VACUUM): va primero.
            conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            self._migrate(conn)
```

Al final de `_migrate`, después del `for target in ...` (fuera de la transacción, sólo se alcanza si hubo migración):

```python
        # La tabla se recreó: VACUUM devuelve el espacio y activa auto_vacuum.
        conn.execute("VACUUM")
```

Debajo de `_MIGRATIONS`, agregar:

```python
_PURGE_CHUNK = 5000  # filas por DELETE: no bloquea save_batch mucho tiempo
```

Reemplazar `purge_older_than` por:

```python
    def purge_older_than(self, cutoff: datetime) -> int:
        total = 0
        while True:
            with self._lock:  # lock por lote: save_batch puede intercalarse
                cur = self._conn.execute(
                    "DELETE FROM usage WHERE id IN "
                    "(SELECT id FROM usage WHERE recorded_at < ? LIMIT ?)",
                    (cutoff.isoformat(), _PURGE_CHUNK),
                )
                self._conn.commit()
            deleted = cur.rowcount or 0
            total += deleted
            if deleted < _PURGE_CHUNK:
                break
        if total:
            with self._lock:
                # fetchall: el PRAGMA libera páginas de a un paso por fila.
                self._conn.execute("PRAGMA incremental_vacuum").fetchall()
                self._conn.commit()
        return total
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_sqlite_repository.py tests/test_monitor_service.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/sqlite_repository.py tests/test_sqlite_repository.py
git commit -m "fix(db): purga por lotes con vacuum incremental"
```

---

### Task 4: Inicio de semana exacto en `usage_for_period`

Con `recorded_at` truncado a minuto, el bucket `lunes 00:00:00` compara como menor que el inicio de semana actual (`'...T00:00:00.123456'`, porque `timedelta(hours, minutes, seconds)` no resta microsegundos) y el primer minuto de la semana desaparece de la vista "Semana". Se alinea el inicio a medianoche exacta como ya hacen "day" y "month".

**Files:**
- Modify: `src/application/monitor_service.py:339-340`
- Test: `tests/test_monitor_service.py` (agregar al final)

**Interfaces:**
- Consumes: `FakeRepo`, `make_monitor` de `tests/conftest.py`.
- Produces: `usage_for_period("week")` llama a `totals_by_app(start, ...)` con `start` = lunes 00:00:00.000000.

- [ ] **Step 1: Escribir el test que falla**

Agregar al final de `tests/test_monitor_service.py` (`FakeRepo`, `make_monitor`, `datetime` ya están importados en ese archivo):

```python
class _SpyRepo(FakeRepo):
    def __init__(self) -> None:
        super().__init__()
        self.starts: list[datetime] = []

    def totals_by_app(self, start, end):
        self.starts.append(start)
        return []


def test_week_period_starts_exactly_at_monday_midnight(settings, notifier):
    repo = _SpyRepo()
    m = make_monitor(settings, notifier, repo)

    m.usage_for_period("week")

    start = repo.starts[-1]
    assert start.weekday() == 0
    assert (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/test_monitor_service.py -q -k week_period`
Expected: FAIL — `start.microsecond != 0` (hay una chance de 1 en 10⁶ de que `now()` caiga justo en `.000000`; si pasa, re-correr).

- [ ] **Step 3: Implementación mínima**

En `src/application/monitor_service.py`, dentro de `usage_for_period`, reemplazar las líneas 339-340:

```python
            "week": now - timedelta(days=now.weekday(), hours=now.hour,
                                    minutes=now.minute, seconds=now.second),
```

por:

```python
            "week": (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0),
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m pytest tests/test_monitor_service.py -q`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add src/application/monitor_service.py tests/test_monitor_service.py
git commit -m "fix(service): inicio de semana alineado a medianoche en usage_for_period"
```

---

### Task 5: Escritura atómica de `settings.json`

**Files:**
- Modify: `src/infrastructure/persistence/settings_store.py:1-6` (imports) y `:24-27` (`save`)
- Create: `tests/test_settings_store.py`
- Test: `tests/test_settings_store.py`

**Interfaces:**
- Consumes: `Settings.to_dict()` / `Settings.from_dict()` de `src/domain/models.py`.
- Produces: `JsonSettingsStore.save(settings)` escribe `settings.json.tmp`, hace `fsync` y `os.replace` sobre `settings.json`; ante cualquier error borra el `.tmp`, deja el archivo previo intacto y re-lanza (mismo contrato de error que `write_text` hoy).

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_settings_store.py`:

```python
"""JsonSettingsStore: escritura atómica y load() robusto ante archivos dañados."""
from __future__ import annotations

import pytest

from src.domain.models import Settings
from src.infrastructure.persistence import settings_store as ss
from src.infrastructure.persistence.settings_store import JsonSettingsStore


def test_save_then_load_roundtrip(tmp_path):
    store = JsonSettingsStore(tmp_path / "settings.json")
    store.save(Settings(monthly_quota_gb=50.0, virustotal_api_key="k"))

    loaded = store.load()
    assert loaded.monthly_quota_gb == 50.0
    assert loaded.virustotal_api_key == "k"


def test_save_writes_via_tmp_and_os_replace(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    calls = []
    real_replace = ss.os.replace

    def spy(src, dst):
        calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(ss.os, "replace", spy)
    JsonSettingsStore(path).save(Settings(monthly_quota_gb=1.0))

    assert calls == [(str(path) + ".tmp", str(path))]
    assert not (tmp_path / "settings.json.tmp").exists()


def test_failed_save_keeps_previous_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    store.save(Settings(monthly_quota_gb=50.0, virustotal_api_key="k"))
    before = path.read_bytes()

    def boom(src, dst):
        raise OSError("disco lleno")

    monkeypatch.setattr(ss.os, "replace", boom)
    with pytest.raises(OSError):
        store.save(Settings(monthly_quota_gb=99.0))

    assert path.read_bytes() == before
    assert not (tmp_path / "settings.json.tmp").exists()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/test_settings_store.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'os'` en los dos tests que espían `ss.os.replace` (el módulo aún no importa `os`). `test_save_then_load_roundtrip` pasa (guard del contrato actual).

- [ ] **Step 3: Implementación mínima**

En `src/infrastructure/persistence/settings_store.py`, agregar `import os` a los imports:

```python
import json
import os
from pathlib import Path
```

Reemplazar `save` (L24-27) por:

```python
    def save(self, settings: Settings) -> None:
        # Escritura atómica: tmp + os.replace. Un crash a mitad deja el archivo viejo.
        tmp = self._path.with_name(self._path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(settings.to_dict(), fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_settings_store.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/settings_store.py tests/test_settings_store.py
git commit -m "fix(settings): escritura atómica de settings.json"
```

---

### Task 6: `load()` robusto + respaldo `.bak` del archivo ilegible

`Settings.from_dict` revienta con `TypeError` (`float(None)`, `tuple(5)`) o `AttributeError` (JSON raíz lista o `null` → `.get`), que el `except` actual no atrapa: crash en `MonitorService.__init__` al arrancar. Y cuando sí atrapa (JSON truncado), devuelve defaults en silencio y el próximo `save` pisa la cuota y la API key de VirusTotal sin dejar rastro.

**Files:**
- Modify: `src/infrastructure/persistence/settings_store.py` (imports; `load` L16-22; nuevo `_backup_corrupt`)
- Test: `tests/test_settings_store.py` (agregar al final + `import json`)

**Interfaces:**
- Consumes: `Settings.from_dict(data)` de `src/domain/models.py` (sin cambios).
- Produces: `load()` nunca lanza; ante archivo ilegible copia el original a `settings.json.bak`, loguea warning (logger `src.infrastructure.persistence.settings_store`) y devuelve `Settings()`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar `import json` a los imports de `tests/test_settings_store.py` (junto a `import pytest`):

```python
import json

import pytest
```

Agregar al final del archivo:

```python
@pytest.mark.parametrize("content", [
    '{"monthly_quota_gb": 50',                 # truncado (crash a mitad de write)
    '{"monthly_quota_gb": null}',              # TypeError en float(None)
    '[1, 2, 3]',                               # AttributeError: list.get
    'null',                                    # AttributeError: None.get
    '{"alert_thresholds": 5}',                 # TypeError en tuple(5)
])
def test_unreadable_settings_return_defaults_and_keep_backup(tmp_path, content, caplog):
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")

    loaded = JsonSettingsStore(path).load()

    assert loaded == Settings()
    assert (tmp_path / "settings.json.bak").read_text("utf-8") == content
    assert "settings.json" in caplog.text


def test_valid_settings_do_not_create_backup(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"monthly_quota_gb": 10}), encoding="utf-8")

    assert JsonSettingsStore(path).load().monthly_quota_gb == 10.0
    assert not (tmp_path / "settings.json.bak").exists()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m pytest tests/test_settings_store.py -q`
Expected: FAIL — los casos `null`/lista/`alert_thresholds: 5` lanzan `TypeError`/`AttributeError`; el caso truncado devuelve defaults pero falta `settings.json.bak` (`FileNotFoundError`). `test_valid_settings_do_not_create_backup` pasa (guard).

- [ ] **Step 3: Implementación mínima**

Imports de `src/infrastructure/persistence/settings_store.py` (queda):

```python
import json
import logging
import os
import shutil
from pathlib import Path

from ...domain.models import Settings
from ...domain.ports import SettingsStore

_log = logging.getLogger(__name__)
```

Reemplazar `load` (L16-22) por `load` + `_backup_corrupt`:

```python
    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        try:
            return Settings.from_dict(json.loads(self._path.read_text("utf-8")))
        except Exception as exc:  # noqa: BLE001 — JSON roto/tipos raros: nunca impedir el arranque
            self._backup_corrupt(exc)
            return Settings()

    def _backup_corrupt(self, exc: Exception) -> None:
        """Guarda el archivo ilegible en settings.json.bak antes de usar defaults."""
        bak = self._path.with_name(self._path.name + ".bak")
        try:
            shutil.copy2(self._path, bak)
        except OSError:
            _log.exception("No se pudo respaldar %s", self._path.name)
        _log.warning("%s ilegible (%r): se usan valores por defecto; copia en %s.",
                     self._path.name, exc, bak.name)
```

Nota: un `OSError` al leer (permisos) también cae acá; el `copy2` del backup probablemente falle igual y queda logueado, sin lanzar.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m pytest tests/test_settings_store.py -q`
Expected: PASS (9 tests: 3 de la Task 5 + 5 parametrizados + 1).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/persistence/settings_store.py tests/test_settings_store.py
git commit -m "fix(settings): load() tolera JSON inválido y respalda en settings.json.bak"
```

---

### Task 7: Verificación final

**Files:**
- Test: suite completa (sin cambios de código)

**Interfaces:**
- Consumes: todo lo anterior + plan 01 ya mergeado en la rama.
- Produces: evidencia de suite verde y estable.

- [ ] **Step 1: Suite de persistencia 5 veces seguidas**

Run: `for i in 1 2 3 4 5; do python -m pytest tests/test_sqlite_repository.py tests/test_settings_store.py -q -p no:cacheprovider || break; done`
Expected: 5 × PASS (24 tests cada vez: 15 de sqlite contando los 2 parametrizados, 9 de settings).

- [ ] **Step 2: Suite completa**

Run: `python -m pytest -q`
Expected: PASS. Si falla en colección (`termios`/`pty`) o crashea en `trust.py`, el plan 01 no está aplicado: aplicar el plan 01 primero, NO tocar esos archivos desde este plan.

- [ ] **Step 3: Chequeo manual de la migración sobre una DB real (opcional, recomendado)**

Copiar la `usage.db` real (`%LOCALAPPDATA%\NetGauge\usage.db`) a una carpeta temporal y correr:

```bash
python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('SELECT COUNT(*), SUM(bytes_sent), SUM(bytes_recv) FROM usage').fetchone())" COPIA/usage.db
python -c "import sys; sys.path.insert(0, '.'); from src.infrastructure.persistence.sqlite_repository import SqliteUsageRepository as R; R(sys.argv[1]).close()" COPIA/usage.db
python -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('SELECT COUNT(*), SUM(bytes_sent), SUM(bytes_recv) FROM usage').fetchone())" COPIA/usage.db
```

Expected: las dos sumas idénticas antes y después; `COUNT(*)` baja ~6× (flush de 10 s → bucket de 60 s, por app activa). Anotar el tiempo que tardó para el CHANGELOG / release notes.

Sin commit en esta task.

---

## Self-review contra el spec

- Spec "Agregación": `minute TEXT` + `UNIQUE(app_name, minute)` (Task 1, `_TABLE_V2`) ✔; `INSERT ... ON CONFLICT DO UPDATE SET bytes += excluded` (Task 1, `save_batch`) ✔; migración v2 recrea la tabla con `GROUP BY app_name, substr(recorded_at,1,16)` (Task 1, `_MIGRATIONS[2]`) ✔; `recorded_at` se mantiene como columna (Task 1; queries sin cambios, cubierto por `test_queries_return_same_totals_after_aggregation` y `test_migration_preserves_grand_totals_and_keeps_upserting`) ✔. Alternativa descartada (buffer 60 s en memoria) no se implementa ✔.
- Tabla del spec, fila 2: "WAL + recuperación de DB corrupta" → Task 2 ✔; "`settings.json` atómico y `load()` robusto" → Tasks 5 y 6 ✔; "purge con vacuum incremental" → Task 3 ✔.
- Spec "Testing": strict TDD, test rojo primero en cada task ✔ (los guards que ya pasan están marcados como tales). Ningún test de este plan depende de ctypes ni de plataforma.
- Spec "Resiliencia" (logging a `data_dir/netgauge.log` con rotación) es del plan 03: acá sólo se usa `logging.getLogger(__name__)`, que ese plan va a enrutar al archivo. No se configura logging en este plan ✔.
- Spec "Commits": conventional, uno por work unit, sin atribución de IA ✔.
- Fuera de alcance, a propósito: `main.py` (la migración legacy copia una DB v1 que este plan migra al abrir; verificado que no hay interacción que romper), `FakeRepo` en `conftest.py`, y la resiliencia de `_purge_if_due`/`_flush` en `MonitorService` (plan 03).
