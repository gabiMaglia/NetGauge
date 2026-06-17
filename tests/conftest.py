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
