"""Snapshot de la UI (plan 04): los getters que usa MainWindow._refresh NO
hacen IO; el worker de fondo (refresh_snapshot) es el único que consulta
SQLite / psutil / el evaluador de confianza."""
from __future__ import annotations

import threading
import time
from datetime import datetime

from conftest import (
    FakeCapture, FakeRepo, FakeReporter, FakeStore, make_monitor,
)
from src.application.monitor_service import MonitorService
from src.domain.models import UsageRecord


class SpyRepo(FakeRepo):
    def __init__(self, records=None) -> None:
        super().__init__(records)
        self.queries = 0

    def totals_by_app(self, start, end):
        self.queries += 1
        return super().totals_by_app(start, end)


def _monitor(settings, notifier, repo=None, **kw) -> MonitorService:
    m = MonitorService(FakeCapture(), repo or FakeRepo(), FakeReporter(),
                       FakeStore(settings), notifier, **kw)
    m.set_translator(lambda k: k)
    return m


def _wait_until(pred, timeout=2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


# ---- cuotas / períodos ------------------------------------------------------
def test_ui_getters_never_touch_repository(settings, notifier):
    repo = SpyRepo([UsageRecord("A", 100, 200, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    m.quota_status()
    m.daily_status()
    m.usage_for_period("day")
    m.usage_for_period("week")
    assert repo.queries == 0


def test_refresh_snapshot_fills_quotas(settings, notifier):
    settings.monthly_quota_gb = 1.0
    settings.daily_quota_gb = 1.0
    repo = SpyRepo([UsageRecord("A", 100, 200, datetime.now()),
                    UsageRecord("B", 300, 400, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    assert m.quota_status().used_bytes == 0     # aún sin snapshot
    m.refresh_snapshot()
    assert m.quota_status().used_bytes == 1000
    assert m.daily_status().used_bytes == 1000
    assert m.quota_status().has_limit
    before = repo.queries
    m.quota_status()
    m.daily_status()
    assert repo.queries == before               # leer no consulta


def test_quota_limit_follows_settings_without_refresh(settings, notifier):
    settings.monthly_quota_gb = 1.0
    repo = SpyRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    m.refresh_snapshot()
    before = repo.queries
    settings.monthly_quota_gb = 2.0
    m.update_settings(settings)
    st = m.quota_status()
    assert st.limit_bytes == 2 * 1024**3
    assert st.used_bytes == 1000
    assert repo.queries == before


def test_period_snapshot_after_request(settings, notifier):
    repo = SpyRepo([UsageRecord("A", 1, 2, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    assert m.usage_for_period("week") == []     # pedido nuevo: vacío y despierta
    m.refresh_snapshot()
    assert [r.app_name for r in m.usage_for_period("week")] == ["A"]


def test_period_request_wakes_worker_once(settings, notifier):
    m = make_monitor(settings, notifier)
    calls: list[int] = []
    m._refresher.trigger = lambda: calls.append(1)
    m.usage_for_period("day")
    m.usage_for_period("day")
    m.usage_for_period("day")
    assert len(calls) == 1
    m.usage_for_period("month")
    assert len(calls) == 2


def test_start_runs_worker_and_notifies(settings, notifier):
    settings.monthly_quota_gb = 1.0
    repo = SpyRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = _monitor(settings, notifier, repo, snapshot_interval=60)
    ready = threading.Event()
    m.set_snapshot_listener(ready.set)
    m.start()
    try:
        assert ready.wait(2)
        assert m.quota_status().used_bytes == 1000
    finally:
        m.stop()
    assert not m._refresher.running
