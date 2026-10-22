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


# ---- arranque: log de fallos y orden single-instance (re-auditoría A3/A4) ----
import sqlite3

import pytest


@pytest.fixture
def boot(monkeypatch, tmp_path):
    """Aísla main(): sin Qt, sin datos reales, registrando el orden de llamadas."""
    import main as m

    calls: list[str] = []

    class FakeGuard:
        running = False

        def already_running(self):
            calls.append("guard")
            return FakeGuard.running

    def fake_repo(_path):
        calls.append("repo")
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(m, "_data_dir", lambda: tmp_path)
    monkeypatch.setattr(m, "_migrate_legacy_data", lambda *a: False)
    monkeypatch.setattr(m, "_setup_logging", lambda d: None)
    monkeypatch.setattr(m, "create_app", lambda: object())
    monkeypatch.setattr(m, "SingleInstance", FakeGuard)
    monkeypatch.setattr(m, "create_capture_service", lambda **k: (object(), True))
    monkeypatch.setattr(m, "SqliteUsageRepository", fake_repo)
    shown = []
    monkeypatch.setattr(m, "_show_fatal", lambda exc: shown.append(exc))
    monkeypatch.setattr(m.sys, "excepthook", m.sys.excepthook)  # restaura al salir
    return m, calls, FakeGuard, shown


def test_main_logs_startup_failure_and_returns_nonzero(boot, caplog):
    m, _calls, _guard, shown = boot
    with caplog.at_level(logging.ERROR):
        rc = m.main()
    assert rc != 0
    assert any(r.exc_info and "locked" in str(r.exc_info[1]) for r in caplog.records)
    assert len(shown) == 1


def test_main_checks_single_instance_before_opening_repo(boot):
    m, calls, _guard, _shown = boot
    m.main()
    assert calls == ["guard", "repo"]


def test_main_second_instance_exits_zero_without_touching_db(boot):
    m, calls, guard, _shown = boot
    guard.running = True
    assert m.main() == 0
    assert calls == ["guard"]


def test_main_installs_excepthook_that_logs(boot, caplog):
    m, _calls, _guard, _shown = boot
    m.main()
    assert m.sys.excepthook is m._log_uncaught
    with caplog.at_level(logging.CRITICAL):
        try:
            raise ValueError("boom-hook")
        except ValueError:
            m.sys.excepthook(*m.sys.exc_info())
    assert any("boom-hook" in str(r.exc_info[1]) for r in caplog.records if r.exc_info)
