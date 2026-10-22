"""previous_period_total / exe_path_for: lecturas de snapshot, sin IO en la UI."""
from __future__ import annotations

from datetime import datetime, timedelta

from conftest import FakeRepo, make_monitor
from src.domain.models import Settings, UsageRecord


class DateRepo(FakeRepo):
    """Devuelve registros sólo si la ventana termina antes de hoy 00:00."""

    def __init__(self, records, *, only_closed_windows=True) -> None:
        super().__init__(records)
        self.windows: list[tuple[datetime, datetime]] = []

    def totals_by_app(self, start, end):
        self.windows.append((start, end))
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return list(self._records) if end <= midnight else []


class FakeProvider:
    def __init__(self, paths) -> None:
        self._paths = paths

    def exe_paths(self): return self._paths
    def connections(self): return []


def _rec(sent, recv):
    return UsageRecord("a", sent, recv, datetime.now() - timedelta(days=1))


def _service(notifier, repo, provider=None):
    m = make_monitor(Settings(), notifier, repo)
    if provider is not None:
        m._conn_provider = provider
    return m


def test_previous_day_total_sums_yesterday(notifier):
    repo = DateRepo([_rec(100, 50), _rec(10, 5)])
    m = _service(notifier, repo)
    m.usage_for_period("day")
    m.refresh_snapshot()
    assert m.previous_period_total("day") == 165
    start, end = repo.windows[-1]
    assert end - start == timedelta(days=1)


def test_previous_day_breakdown_sums_sent_and_recv_separately(notifier):
    repo = DateRepo([_rec(100, 50), _rec(10, 5)])
    m = _service(notifier, repo)
    assert m.previous_period_breakdown("day") is None  # aún no calculado
    m.usage_for_period("day")
    m.refresh_snapshot()
    assert m.previous_period_breakdown("day") == (110, 55)
    assert m.previous_period_breakdown("session") is None


def test_breakdown_none_when_both_zero(notifier):
    m = _service(notifier, DateRepo([_rec(0, 0)]))
    m.usage_for_period("day")
    m.refresh_snapshot()
    assert m.previous_period_breakdown("day") is None


def test_previous_week_and_month_windows(notifier):
    repo = DateRepo([_rec(1, 1)])
    m = _service(notifier, repo)
    m.usage_for_period("week")
    m.refresh_snapshot()
    start, end = repo.windows[-1]
    assert end - start == timedelta(days=7)
    m.usage_for_period("month")
    m.refresh_snapshot()
    start, end = repo.windows[-1]
    assert start.day == 1 and end.day == 1 and start < end
    assert m.previous_period_total("month") == 2


def test_previous_total_none_for_session_or_empty(notifier):
    m = _service(notifier, DateRepo([]))
    m.usage_for_period("day")
    m.refresh_snapshot()
    assert m.previous_period_total("session") is None
    assert m.previous_period_total("day") is None   # suma 0
    assert m.previous_period_total("week") is None  # nunca calculado


def test_exe_path_for(notifier):
    m = _service(notifier, FakeRepo())
    assert m.exe_path_for("x") is None              # sin provider
    m = _service(notifier, FakeRepo(),
                 FakeProvider({"x": frozenset({"/b/x", "/a/x"})}))
    assert m.exe_path_for("x") is None              # aún sin refrescar
    m._refresh_exe_paths()
    assert m.exe_path_for("x") == "/a/x"
    assert m.exe_path_for("y") is None
