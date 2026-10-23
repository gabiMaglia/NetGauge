import pytest

from src.presentation.qt.viewmodel import (
    AppRateTracker, AppRowData, filter_sort_apps, share_pct, trend_label, trend_pct)


def test_trend_pct():
    assert trend_pct(112, 100) == pytest.approx(12.0)
    assert trend_pct(96, 100) == pytest.approx(-4.0)
    assert trend_pct(50, None) is None
    assert trend_pct(50, 0) is None


def test_trend_label():
    assert trend_label(12.4) == ("▲ 12 %", "up")
    assert trend_label(-4.2) == ("▼ 4 %", "down")
    assert trend_label(0.2) == ("= 0 %", "flat")
    assert trend_label(None) == ("", "none")


def test_trend_label_rounds_half_up():
    assert trend_label(0.5) == ("▲ 1 %", "up")
    assert trend_label(12.5) == ("▲ 13 %", "up")
    assert trend_label(-12.5) == ("▼ 13 %", "down")
    assert trend_label(0.0) == ("= 0 %", "flat")


def test_rate_tracker_computes_bytes_per_second():
    t = AppRateTracker()
    assert t.update({"a": 1000}, now=10.0) == {"a": 0.0}   # primera lectura
    assert t.update({"a": 3000, "b": 500}, now=12.0) == {"a": 1000.0, "b": 0.0}


def test_rate_tracker_counter_drop_is_zero():
    t = AppRateTracker()
    t.update({"a": 5000}, now=0.0)
    assert t.update({"a": 100}, now=1.0) == {"a": 0.0}


def test_filter_sort():
    rows = [AppRowData("Chrome", 10, 90, 5.0), AppRowData("Dropbox", 60, 40, 9.0),
            AppRowData("Slack", 1, 2, 0.0)]
    # Chrome y Dropbox empatan en total (100): desempate por nombre ascendente.
    assert [r.name for r in filter_sort_apps(rows, "", "total")] == ["Chrome", "Dropbox", "Slack"]
    assert [r.name for r in filter_sort_apps(rows, "", "up")][0] == "Dropbox"
    assert [r.name for r in filter_sort_apps(rows, "", "now")][0] == "Dropbox"
    assert [r.name for r in filter_sort_apps(rows, "ch", "total")] == ["Chrome"]


def test_share_pct():
    assert share_pct(25, 100) == 25.0
    assert share_pct(5, 0) == 0.0


# ---- tasa suavizada: nettop entrega snapshots cada 2 s ---------------------
def _feed_stairs(tracker, seconds, step=1400 * 1024, start=0):
    """Acumulado que sólo cambia cada 2ª lectura (una lectura por segundo)."""
    out, total = [], start
    for sec in range(seconds):
        if sec % 2 == 1:
            total += step
        out.append(tracker.update({"curl": total}, now=float(sec))["curl"])
    return out


def test_unwindowed_tracker_alternates_on_two_second_snapshots():
    rates = _feed_stairs(AppRateTracker(), 10)[3:]
    assert 0.0 in rates                      # el síntoma original


def test_windowed_tracker_is_steady_on_two_second_snapshots():
    from src.presentation.qt.viewmodel import AppRateTracker as T
    rates = _feed_stairs(T(window=4.0), 12)[5:]   # ya calentó
    for r in rates:
        assert r > 0 and abs(r - 700 * 1024) / (700 * 1024) <= 0.15


def test_windowed_tracker_counter_drop_then_recovers():
    t = AppRateTracker(window=4.0)
    for s in range(6):
        t.update({"a": s * 1000}, now=float(s))
    assert t.update({"a": 10}, now=6.0)["a"] == 0.0
    assert t.update({"a": 1010}, now=7.0)["a"] == 1000.0


def test_windowed_tracker_decays_to_zero_after_download_stops():
    t = AppRateTracker(window=4.0)
    total = 0
    for s in range(6):
        total += 700
        t.update({"a": total}, now=float(s))
    last = [t.update({"a": total}, now=float(6 + i))["a"] for i in range(5)]
    assert last[0] > 0 and last[-1] == 0.0


def test_windowed_tracker_new_and_vanished_apps():
    t = AppRateTracker(window=4.0)
    t.update({"a": 0, "b": 0}, now=0.0)
    r = t.update({"a": 100, "c": 50}, now=1.0)
    assert r == {"a": 100.0, "c": 0.0}       # app nueva: 0; "b" desapareció
    assert t.update({"a": 200, "c": 150}, now=2.0)["c"] == 100.0
