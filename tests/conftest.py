"""Fakes y fixtures para testear la capa de aplicación/dominio sin Qt ni Windows."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.application.monitor_service import MonitorService
from src.domain.models import Settings, UsageRecord


class FakeCapture:
    def start(self, on_sample): pass
    def stop(self): pass


class FakeRepo:
    def __init__(self, records: list[UsageRecord] | None = None) -> None:
        self._records = records or []
        self.saved: list = []
        self.purged_before: datetime | None = None

    def save_batch(self, records): self.saved.extend(records)
    def usage_between(self, start, end): return list(self._records)
    def totals_by_app(self, start, end): return list(self._records)

    def purge_older_than(self, cutoff) -> int:
        self.purged_before = cutoff
        return 0

    def close(self): pass


class FakeReporter:
    def generate(self, records, destination_hint=None): return "report.csv"


class FakeStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.saved: list[Settings] = []

    def load(self): return self._settings
    def save(self, s): self.saved.append(s)


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def notify(self, title, message): self.messages.append((title, message))


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


def make_monitor(settings: Settings, notifier: FakeNotifier,
                 repo: FakeRepo | None = None) -> MonitorService:
    m = MonitorService(FakeCapture(), repo or FakeRepo(), FakeReporter(),
                       FakeStore(settings), notifier)
    m.set_translator(lambda k: k)  # mensajes determinísticos (devuelve la clave)
    return m


BUNDLED_FONTS = ("Plus Jakarta Sans", "JetBrains Mono")


@pytest.fixture(scope="session", autouse=True)
def bundled_fonts():
    """Una única QApplication para toda la sesión, con las fuentes bundleadas
    registradas igual que la app (app.run -> load_app_fonts).

    Sin fuentes Qt cae a la genérica del SO (mucho más ancha en Windows) y los tests
    de layout miden otra cosa. Devuelve si ambas familias quedaron registradas.

    Al terminar hace el cierre en orden: ventanas, ciclos de GC y pixmaps cacheados
    mueren ANTES que la QApplication; si no, en el cierre del intérprete se destruyen
    objetos Qt sin app y el proceso aborta (Linux 134, macOS 139, Windows 1)."""
    import gc
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from src.presentation.qt import app_icons, theme
    app = QApplication.instance() or QApplication([])   # referencia viva hasta el final
    theme.load_app_fonts()
    families = set(QFontDatabase.families())
    yield all(f in families for f in BUNDLED_FONTS)

    for w in QApplication.topLevelWidgets():
        w.close()
        w.deleteLater()
    for _ in range(3):
        app.processEvents()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()   # ventanas en ciclo con su MonitorService (listener -> señal)
    app_icons.clear_cache()
    gc.collect()
