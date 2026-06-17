"""Reputación vía VirusTotal API v3 (opt-in, por hash, no bloqueante).

Privacidad: solo se envía el SHA-256 del ejecutable (nunca el archivo).
Límite del free tier: 4 req/min y 500/día → un único worker serial con throttle.
"""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import time
import urllib.error
import urllib.request

from ...domain.ports import ReputationService

log = logging.getLogger(__name__)

_API = "https://www.virustotal.com/api/v3/files/"
_MIN_INTERVAL = 16.0   # seg entre consultas (≈4/min, dentro del free tier)
_UNKNOWN = "unknown"   # VT no conoce el archivo


class VirusTotalReputation(ReputationService):
    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._cache: dict[str, object] = {}   # path -> (m,total) | _UNKNOWN | "error"
        self._queued: set[str] = set()
        self._lock = threading.Lock()
        self._q: "queue.Queue[str]" = queue.Queue()
        self._worker: threading.Thread | None = None

    def set_api_key(self, key: str) -> None:
        self._api_key = key

    def lookup(self, exe_path: str) -> tuple[int, int] | None:
        if not exe_path or not self._api_key:
            return None
        with self._lock:
            cached = self._cache.get(exe_path)
            if isinstance(cached, tuple):
                return cached
            if cached is not None:        # _UNKNOWN o "error": no reintentar
                return None
            if exe_path in self._queued:
                return None
            self._queued.add(exe_path)
        self._ensure_worker()
        self._q.put(exe_path)
        return None

    def _ensure_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while True:
            try:
                path = self._q.get(timeout=60)
            except queue.Empty:
                return
            try:
                result = self._query(path)
            except Exception as exc:  # noqa: BLE001
                log.debug("VT fallo en %s: %s", path, exc)
                result = "error"
            with self._lock:
                self._cache[path] = result
                self._queued.discard(path)
            time.sleep(_MIN_INTERVAL)  # respeta el rate limit del free tier

    def _query(self, path: str):
        sha = _sha256(path)
        if not sha:
            return "error"
        req = urllib.request.Request(
            _API + sha, headers={"x-apikey": self._api_key,
                                 "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return _UNKNOWN      # VT no tiene el archivo
            raise
        stats = (data.get("data", {}).get("attributes", {})
                 .get("last_analysis_stats", {}))
        if not stats:
            return _UNKNOWN
        malicious = int(stats.get("malicious", 0)) + int(stats.get("suspicious", 0))
        total = sum(int(v) for v in stats.values())
        return (malicious, total)


def _sha256(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


class NullReputation(ReputationService):
    def set_api_key(self, key: str) -> None: ...
    def lookup(self, exe_path: str) -> tuple[int, int] | None:
        return None
