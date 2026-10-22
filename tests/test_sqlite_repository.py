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


def test_save_batch_failure_rolls_back_so_retry_is_exact(repo, tmp_path):
    batch = [UsageRecord("a", 100, 0, T0), UsageRecord("b", 50, 0, T0)]
    repo._conn.execute(
        "CREATE TEMP TRIGGER boom BEFORE INSERT ON usage WHEN NEW.app_name='b' "
        "BEGIN SELECT RAISE(ABORT,'x'); END"
    )
    with pytest.raises(sqlite3.DatabaseError):
        repo.save_batch(batch)
    repo._conn.execute("DROP TRIGGER boom")

    repo.save_batch(batch)  # reintento exitoso

    totals = {r.app_name: r.bytes_sent for r in repo.totals_by_app(
        T0 - timedelta(hours=1), T0 + timedelta(hours=1))}
    assert totals == {"a": 100, "b": 50}


# ---- re-auditoría A6/A7 -------------------------------------------------------
def test_extended_corrupt_errorcode_is_quarantined(tmp_path, monkeypatch):
    path = tmp_path / "usage.db"
    path.write_bytes(b"x" * 100)
    real_open = SqliteUsageRepository._open
    state = {"n": 0}

    def open_(self):
        state["n"] += 1
        if state["n"] == 1:
            exc = sqlite3.DatabaseError("malformed index")
            exc.sqlite_errorcode = 779  # SQLITE_CORRUPT_INDEX (extendido de 11)
            raise exc
        return real_open(self)

    monkeypatch.setattr(SqliteUsageRepository, "_open", open_)
    SqliteUsageRepository(path).close()
    assert list(tmp_path.glob("usage.db.corrupt-*"))


def test_failed_vacuum_is_logged_and_does_not_block_open(tmp_path, monkeypatch, caplog):
    path = tmp_path / "usage.db"
    _build_v1(path, 1)

    def boom(_conn):
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(sr, "_vacuum", boom, raising=False)
    repo = SqliteUsageRepository(path)
    repo.close()
    assert _pragma(path, "user_version") == 2
    assert "VACUUM" in caplog.text


def test_vacuum_is_retried_on_next_open_if_auto_vacuum_not_set(tmp_path, monkeypatch):
    path = tmp_path / "usage.db"
    _build_v1(path, 1)
    real = getattr(sr, "_vacuum", None)
    monkeypatch.setattr(sr, "_vacuum", lambda _c: (_ for _ in ()).throw(
        sqlite3.OperationalError("full")), raising=False)
    SqliteUsageRepository(path).close()
    assert _pragma(path, "auto_vacuum") == 0

    monkeypatch.undo()
    SqliteUsageRepository(path).close()
    assert _pragma(path, "auto_vacuum") == 2
