"""GeoIP/ASN vía ip-api.com (gratis, sin key, opt-in, no bloqueante).

Devuelve país y proveedor (ISP/org) de una IP remota. Las IPs privadas (LAN,
loopback) se saltean: no tienen geo. Cachea por IP y respeta el rate limit.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import queue
import threading
import time
import urllib.request

from ...domain.ports import GeoIpService

log = logging.getLogger(__name__)

# HTTP (el endpoint HTTPS de ip-api es de pago); fields: status,countryCode,isp,org,as
_URL = "http://ip-api.com/json/{ip}?fields=status,countryCode,isp,org,as"
_MIN_INTERVAL = 1.5   # seg entre consultas (free tier: 45/min)


def _is_public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return not (addr.is_private or addr.is_loopback or addr.is_link_local
                    or addr.is_multicast or addr.is_reserved)
    except ValueError:
        return False


class IpApiGeoIp(GeoIpService):
    def __init__(self) -> None:
        self._cache: dict[str, object] = {}   # ip -> (cc, org) | "error"
        self._queued: set[str] = set()
        self._lock = threading.Lock()
        self._q: "queue.Queue[str]" = queue.Queue()
        self._worker: threading.Thread | None = None

    def lookup(self, ip: str) -> tuple[str, str] | None:
        if not ip or not _is_public(ip):
            return None
        with self._lock:
            cached = self._cache.get(ip)
            if isinstance(cached, tuple):
                return cached
            if cached is not None:        # "error": no reintentar
                return None
            if ip in self._queued:
                return None
            self._queued.add(ip)
        self._ensure_worker()
        self._q.put(ip)
        return None

    def _ensure_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while True:
            try:
                ip = self._q.get(timeout=60)
            except queue.Empty:
                return
            try:
                result = self._query(ip)
            except Exception as exc:  # noqa: BLE001
                log.debug("GeoIP fallo en %s: %s", ip, exc)
                result = "error"
            with self._lock:
                self._cache[ip] = result
                self._queued.discard(ip)
            time.sleep(_MIN_INTERVAL)

    def _query(self, ip: str):
        req = urllib.request.Request(_URL.format(ip=ip),
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "success":
            return "error"
        cc = data.get("countryCode") or "?"
        org = data.get("org") or data.get("isp") or data.get("as") or ""
        return (cc, org)


class NullGeoIp(GeoIpService):
    def lookup(self, ip: str) -> tuple[str, str] | None:
        return None
