"""Repositorio SQLite. Thread-safe vía lock; agrega por (app, minuto)."""
from __future__ import annotations

import logging
import os
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

_PURGE_CHUNK = 5000  # filas por DELETE: no bloquea save_batch mucho tiempo


def _minute_key(dt: datetime) -> str:
    """'YYYY-MM-DDTHH:MM': mismo corte que substr(recorded_at, 1, 16) en SQL."""
    return dt.isoformat()[:16]


class SqliteUsageRepository(UsageRepository):
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
            # auto_vacuum solo aplica a DBs sin tablas (o tras VACUUM): va primero.
            conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
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
        # La tabla se recreó: VACUUM devuelve el espacio y activa auto_vacuum.
        conn.execute("VACUUM")

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

    def usage_between(self, start: datetime, end: datetime) -> list[UsageRecord]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT app_name, bytes_sent, bytes_recv, recorded_at FROM usage "
                "WHERE recorded_at >= ? AND recorded_at < ? ORDER BY recorded_at",
                (start.isoformat(), end.isoformat()),
            )
            return [
                UsageRecord(a, s, r, datetime.fromisoformat(ts))
                for a, s, r, ts in cur.fetchall()
            ]

    def totals_by_app(self, start: datetime, end: datetime) -> list[UsageRecord]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT app_name, SUM(bytes_sent), SUM(bytes_recv) FROM usage "
                "WHERE recorded_at >= ? AND recorded_at < ? "
                "GROUP BY app_name ORDER BY SUM(bytes_sent + bytes_recv) DESC",
                (start.isoformat(), end.isoformat()),
            )
            return [
                UsageRecord(a, int(s or 0), int(r or 0), start)
                for a, s, r in cur.fetchall()
            ]

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

    def close(self) -> None:
        with self._lock:
            self._conn.close()
