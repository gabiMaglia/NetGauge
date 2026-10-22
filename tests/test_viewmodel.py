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
