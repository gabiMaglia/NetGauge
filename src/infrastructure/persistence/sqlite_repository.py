"""Repositorio SQLite. Thread-safe vía lock; agrega por (app, minuto)."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ...domain.models import UsageRecord
from ...domain.ports import UsageRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name    TEXT    NOT NULL,
    bytes_sent  INTEGER NOT NULL,
    bytes_recv  INTEGER NOT NULL,
    recorded_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_recorded_at ON usage(recorded_at);
CREATE INDEX IF NOT EXISTS idx_usage_app ON usage(app_name);
"""


class SqliteUsageRepository(UsageRepository):
    def __init__(self, db_path: str | Path) -> None:
        self._path = str(db_path)
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save_batch(self, records: Iterable[UsageRecord]) -> None:
        rows = [
            (r.app_name, r.bytes_sent, r.bytes_recv, r.recorded_at.isoformat())
            for r in records
        ]
        if not rows:
            return
        with self._lock:
            self._conn.executemany(
                "INSERT INTO usage (app_name, bytes_sent, bytes_recv, recorded_at) "
                "VALUES (?, ?, ?, ?)",
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
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM usage WHERE recorded_at < ?", (cutoff.isoformat(),)
            )
            self._conn.commit()
            return cur.rowcount or 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()
