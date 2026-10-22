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
