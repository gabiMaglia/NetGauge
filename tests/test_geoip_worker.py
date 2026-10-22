# tests/test_geoip_worker.py
"""GeoIP: el worker no pierde items al salir por idle."""
from __future__ import annotations

import queue
import time

import pytest

from src.infrastructure.capture import geoip_ipapi as gmod
from src.infrastructure.capture.geoip_ipapi import IpApiGeoIp


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(gmod, "_MIN_INTERVAL", 0.0)


def _wait_until(pred, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


class _RacyQueue(queue.Queue):
    def __init__(self, item):
        super().__init__()
        self._item, self._armed = item, True

    def get(self, block=True, timeout=None):
        if self._armed:
            self._armed = False
            self.put(self._item)   # lookup concurrente encola justo ahora
            raise queue.Empty
        return super().get(block, timeout)


def test_worker_no_pierde_un_item_encolado_mientras_sale_por_idle(monkeypatch):
    monkeypatch.setattr(gmod, "_IDLE_TIMEOUT", 0.01)
    g = IpApiGeoIp()
    monkeypatch.setattr(g, "_query", lambda ip: ("AR", "Telecom"))
    g._q = _RacyQueue("8.8.8.8")
    g._queued.add("8.8.8.8")
    g._run()
    assert g._cache["8.8.8.8"] == ("AR", "Telecom")


def test_worker_se_reinicia_tras_idle(monkeypatch):
    monkeypatch.setattr(gmod, "_IDLE_TIMEOUT", 0.05)
    g = IpApiGeoIp()
    monkeypatch.setattr(g, "_query", lambda ip: ("US", "Google"))
    g.lookup("8.8.8.8")
    assert _wait_until(lambda: isinstance(g._cache.get("8.8.8.8"), tuple))
    assert _wait_until(lambda: g._worker is None)
    g.lookup("1.1.1.1")
    assert _wait_until(lambda: isinstance(g._cache.get("1.1.1.1"), tuple))


def test_lookup_ip_privada_no_encola():
    g = IpApiGeoIp()
    assert g.lookup("192.168.0.5") is None
    assert g._q.qsize() == 0 and g._worker is None


def test_cancel_pending_corta_la_cola(monkeypatch):
    import threading

    g = IpApiGeoIp()
    started, release = threading.Event(), threading.Event()
    calls: list[str] = []

    def fake_query(ip):
        calls.append(ip)
        started.set()
        release.wait(3)
        return ("AR", "Telecom")

    monkeypatch.setattr(g, "_query", fake_query)
    for i in range(1, 6):
        g.lookup(f"8.8.8.{i}")
    assert started.wait(2)          # el worker ya tiene la 1ª en vuelo
    g.cancel_pending()
    assert g._queued == set() and g._q.empty()
    release.set()
    time.sleep(0.2)
    assert len(calls) == 1          # sólo la que ya estaba en vuelo


def test_cancel_pending_descarta_item_ya_sacado_de_la_cola(monkeypatch):
    g = IpApiGeoIp()
    calls: list[str] = []
    monkeypatch.setattr(g, "_query", lambda ip: calls.append(ip))
    g._q.put("8.8.8.8")             # en cola pero cancelado: no está en _queued
    g._q.put("__stop__")
    real_get = g._q.get

    def get(block=True, timeout=None):
        v = real_get(block, timeout)
        if v == "__stop__":
            raise queue.Empty
        return v

    g._q.get = get
    monkeypatch.setattr(gmod, "_IDLE_TIMEOUT", 0.01)
    g._run()
    assert calls == []


def test_is_public_rechaza_cgnat_y_rangos_especiales():
    assert not gmod._is_public("100.64.0.1")      # CGNAT
    assert not gmod._is_public("192.0.2.1")       # TEST-NET
    assert gmod._is_public("8.8.8.8")
