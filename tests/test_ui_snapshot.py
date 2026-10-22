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
from src.domain.models import (
    TRUST_TRUSTED, TRUST_UNKNOWN, Connection, TrustInfo, UsageRecord,
)


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


# ---- confianza / conexiones -------------------------------------------------
# Mapa que devuelve el ConnectionProvider fake. Task 6 lo pasa a frozenset.
CHROME_PATHS = {"Chrome": "C:/chrome.exe"}


class BlockingEvaluator:
    """Evaluador que se traba hasta `release`: simula WinVerifyTrust lento."""

    def __init__(self, level=TRUST_TRUSTED) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self._level = level

    def evaluate(self, path):
        self.calls += 1
        self.entered.set()
        self.release.wait(5)
        return TrustInfo(level=self._level, exe_path=path)


class DictEvaluator:
    def __init__(self, levels: dict, fail: set | None = None) -> None:
        self._levels = levels
        self._fail = fail or set()

    def evaluate(self, path):
        if path in self._fail:
            raise OSError("WinVerifyTrust explotó")
        return TrustInfo(level=self._levels.get(path, TRUST_UNKNOWN), exe_path=path)


class FakeConnProvider:
    def __init__(self, paths=None, conns=None) -> None:
        self.paths = paths or {}
        self.conns = conns or []
        self.conn_calls = 0
        self.path_calls = 0

    def exe_paths(self):
        self.path_calls += 1
        return dict(self.paths)

    def connections(self):
        self.conn_calls += 1
        return list(self.conns)


def test_trust_for_unseen_app_returns_fast_without_evaluating(settings, notifier):
    ev = BlockingEvaluator()
    prov = FakeConnProvider(CHROME_PATHS)
    m = _monitor(settings, notifier, trust_evaluator=ev, connection_provider=prov)
    t0 = time.perf_counter()
    info = m.trust_for("Chrome")
    assert time.perf_counter() - t0 < 0.05
    assert info.level == TRUST_UNKNOWN
    assert ev.calls == 0
    assert prov.path_calls == 0          # ni siquiera psutil.process_iter


def test_worker_fills_trust_in_background(settings, notifier):
    ev = BlockingEvaluator()
    m = _monitor(settings, notifier, trust_evaluator=ev,
                 connection_provider=FakeConnProvider(CHROME_PATHS))
    m.trust_for("Chrome")                # encola la app
    m.start()
    try:
        assert ev.entered.wait(2)        # el WORKER está evaluando (trabado)
        t0 = time.perf_counter()
        assert m.trust_for("Chrome").level == TRUST_UNKNOWN   # GUI no se traba
        assert time.perf_counter() - t0 < 0.05
        ev.release.set()
        assert _wait_until(lambda: m.trust_for("Chrome").level == TRUST_TRUSTED)
    finally:
        ev.release.set()
        m.stop()


def test_trust_for_wakes_worker_once_per_app(settings, notifier):
    m = _monitor(settings, notifier, trust_evaluator=DictEvaluator({}),
                 connection_provider=FakeConnProvider(CHROME_PATHS))
    calls: list[int] = []
    m._refresher.trigger = lambda: calls.append(1)
    for _ in range(3):
        m.trust_for("System")            # sin ruta: nunca se resuelve
    assert len(calls) == 1               # sin bucle UI <-> worker
    m.trust_for("Chrome")
    assert len(calls) == 2


def test_trust_disabled_returns_unknown_and_does_not_enqueue(settings, notifier):
    settings.trust_check_enabled = False
    m = _monitor(settings, notifier, trust_evaluator=DictEvaluator({}),
                 connection_provider=FakeConnProvider(CHROME_PATHS))
    assert m.trust_for("Chrome").level == TRUST_UNKNOWN
    assert m._trust_requested == set()


def test_refresh_evaluates_only_requested_apps(settings, notifier):
    ev = DictEvaluator({"C:/chrome.exe": TRUST_TRUSTED})
    prov = FakeConnProvider(CHROME_PATHS)
    m = _monitor(settings, notifier, trust_evaluator=ev, connection_provider=prov)
    m.refresh_snapshot()                 # nadie pidió nada
    assert prov.path_calls == 0
    m.trust_for("Chrome")
    m.refresh_snapshot()
    assert m.trust_for("Chrome").level == TRUST_TRUSTED


def test_evaluator_failure_on_one_app_does_not_block_others(settings, notifier):
    ev = DictEvaluator({"C:/b.exe": TRUST_TRUSTED}, fail={"C:/a.exe"})
    paths = {"A": "C:/a.exe", "B": "C:/b.exe"}
    if isinstance(next(iter(CHROME_PATHS.values())), frozenset):   # Task 6
        paths = {k: frozenset({v}) for k, v in paths.items()}
    m = _monitor(settings, notifier, trust_evaluator=ev,
                 connection_provider=FakeConnProvider(paths))
    m.trust_for("A")
    m.trust_for("B")
    m.refresh_snapshot()
    assert m.trust_for("A").level == TRUST_UNKNOWN
    assert m.trust_for("B").level == TRUST_TRUSTED


def test_connections_read_snapshot_after_demand(settings, notifier):
    conn = Connection("Chrome", 10, "1.2.3.4", 443, "ESTABLISHED")
    prov = FakeConnProvider(conns=[conn])
    m = _monitor(settings, notifier, connection_provider=prov)
    assert m.connections() == []         # sin psutil en el hilo GUI
    assert prov.conn_calls == 0
    m.refresh_snapshot()
    assert prov.conn_calls == 1
    assert m.connections() == [conn]


def test_connections_not_enumerated_without_demand(settings, notifier):
    prov = FakeConnProvider(conns=[Connection("X", 1, "1.1.1.1", 80, "ESTABLISHED")])
    m = _monitor(settings, notifier, connection_provider=prov)
    m.refresh_snapshot()                 # pestaña nunca mirada
    assert prov.conn_calls == 0


def test_connections_demand_wakes_worker_only_when_stale(settings, notifier):
    m = _monitor(settings, notifier, connection_provider=FakeConnProvider())
    calls: list[int] = []
    m._refresher.trigger = lambda: calls.append(1)
    m.connections()
    m.connections()
    assert len(calls) == 1
    m._conn_wanted_at = time.monotonic() - 60   # demanda vencida
    m.connections()
    assert len(calls) == 2
