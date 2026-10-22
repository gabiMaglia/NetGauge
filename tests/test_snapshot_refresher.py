"""Worker único de fondo que refresca el snapshot de la UI (plan 04)."""
from __future__ import annotations

import logging
import threading

from src.application.snapshot_refresher import SnapshotRefresher


def test_first_refresh_is_immediate_and_notifies():
    refreshed = threading.Event()
    notified = threading.Event()
    r = SnapshotRefresher(refreshed.set, interval=60, on_refreshed=notified.set)
    r.start()
    try:
        assert refreshed.wait(1)
        assert notified.wait(1)
    finally:
        r.stop()


def test_trigger_wakes_before_interval():
    calls: list[int] = []
    second = threading.Event()

    def refresh():
        calls.append(1)
        if len(calls) >= 2:
            second.set()

    r = SnapshotRefresher(refresh, interval=60)
    r.start()
    try:
        r.trigger()
        assert second.wait(1)   # no esperó los 60 s
    finally:
        r.stop()


def test_exception_does_not_kill_loop(caplog):
    calls: list[int] = []
    recovered = threading.Event()

    def refresh():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        recovered.set()

    r = SnapshotRefresher(refresh, interval=0.01)
    with caplog.at_level(logging.ERROR):
        r.start()
        try:
            assert recovered.wait(1)
        finally:
            r.stop()
    assert "Fallo refrescando el snapshot" in caplog.text


def test_listener_exception_does_not_kill_loop():
    calls: list[int] = []
    again = threading.Event()

    def refresh():
        calls.append(1)
        if len(calls) >= 2:
            again.set()

    def bad_listener():
        raise RuntimeError("widget ya destruido")

    r = SnapshotRefresher(refresh, interval=0.01, on_refreshed=bad_listener)
    r.start()
    try:
        assert again.wait(1)
    finally:
        r.stop()


def test_set_listener_after_construction():
    notified = threading.Event()
    r = SnapshotRefresher(lambda: None, interval=60)
    r.set_listener(notified.set)
    r.start()
    try:
        assert notified.wait(1)
    finally:
        r.stop()


def test_stop_joins_and_is_idempotent():
    r = SnapshotRefresher(lambda: None, interval=60)
    r.stop()                 # sin start: no-op
    r.start()
    assert r.running
    r.stop()
    assert not r.running
    r.stop()                 # dos veces: no-op
