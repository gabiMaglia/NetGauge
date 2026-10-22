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
