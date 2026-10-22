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
# Hash público y conocido (archivo de prueba EICAR) para validar la key sin
# poner la credencial en la URL: 200/404 = key aceptada, 401/403 = rechazada.
_EICAR_SHA256 = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"

_ERROR = "error"       # irrecuperable (p.ej. archivo ilegible); set_api_key lo limpia
_IDLE_TIMEOUT = 60.0   # seg sin trabajo antes de que el worker termine
_BACKOFF_BASE = 300.0  # reintento tras error transitorio: 5 min, x2 por fallo
_BACKOFF_MAX = 3600.0


class VirusTotalReputation(ReputationService):
    def __init__(self, api_key: str = "", clock=time.monotonic) -> None:
        self._api_key = api_key
        self._clock = clock
        self._cache: dict[str, object] = {}   # path -> (m,total) | _UNKNOWN | _ERROR
        self._queued: set[str] = set()
        self._retry_at: dict[str, float] = {}  # path -> instante (clock) del próx. intento
        self._fails: dict[str, int] = {}
        self._lock = threading.Lock()
        self._q: "queue.Queue[str]" = queue.Queue()
        self._worker: threading.Thread | None = None

    def set_api_key(self, key: str) -> None:
        """Cambia la key. Los errores (cacheados o en backoff) se descartan: con
        otra key pueden andar. Los resultados válidos se conservan."""
        with self._lock:
            if key == self._api_key:
                return  # el monitor lo llama cada ciclo: no anular el backoff
            self._api_key = key
            for p in [p for p, v in self._cache.items() if v == _ERROR]:
                del self._cache[p]
            self._retry_at.clear()
            self._fails.clear()

    def test_api_key(self, key: str) -> bool:
        """Valida una key contra VT. La key va SOLO en el header x-apikey.

        Consulta un hash público conocido (EICAR): con key válida VT responde
        200 (o 404); con key inválida, 401/403. Cuesta 1 request de la cuota.
        Cualquier otro resultado o excepción -> False (no se puede confirmar).
        Llamar siempre desde un hilo de fondo: hace I/O de red bloqueante.
        """
        key = (key or "").strip()
        if not key:
            return False
        req = urllib.request.Request(
            _API + _EICAR_SHA256,
            headers={"x-apikey": key, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            return e.code == 404
        except Exception as exc:  # noqa: BLE001 — el hilo llamador debe retornar siempre
            log.debug("test_api_key falló: %s", exc)
            return False

    def lookup(self, exe_path: str) -> tuple[int, int] | None:
        if not exe_path or not self._api_key:
            return None
        with self._lock:
            cached = self._cache.get(exe_path)
            if isinstance(cached, tuple):
                return cached
            if cached is not None:        # _UNKNOWN o _ERROR: no reintentar
                return None
            if exe_path in self._queued:
                return None
            if self._clock() < self._retry_at.get(exe_path, 0.0):
                return None               # en backoff por un error transitorio
            self._queued.add(exe_path)
            # put + asegurar worker BAJO EL MISMO LOCK con el que el worker decide
            # salir por idle: nunca queda un item en la cola sin worker vivo.
            self._q.put(exe_path)
            self._ensure_worker_locked()
        return None

    def _ensure_worker_locked(self) -> None:
        """Arranca el worker si no hay uno vivo. Llamar con self._lock tomado."""
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _run(self) -> None:
        while True:
            try:
                path = self._q.get(timeout=_IDLE_TIMEOUT)
            except queue.Empty:
                with self._lock:
                    if self._q.empty():   # nadie encoló mientras decidíamos salir
                        self._worker = None
                        return
                continue
            self._process(path)
            time.sleep(_MIN_INTERVAL)  # respeta el rate limit del free tier

    def _process(self, path: str) -> None:
        """Consulta un path y actualiza cache/backoff. Los errores de red o HTTP
        (401/403/429/5xx) son transitorios: NO se cachean, se reintenta luego."""
        failed = False
        result: object = None
        try:
            result = self._query(path)
        except Exception as exc:  # noqa: BLE001
            log.debug("VT fallo en %s: %s", path, exc)
            failed = True
        with self._lock:
            self._queued.discard(path)
            if failed:
                n = self._fails.get(path, 0) + 1
                self._fails[path] = n
                delay = min(_BACKOFF_BASE * (2 ** (n - 1)), _BACKOFF_MAX)
                self._retry_at[path] = self._clock() + delay
            else:
                self._fails.pop(path, None)
                self._retry_at.pop(path, None)
                self._cache[path] = result

    def _query(self, path: str):
        sha = _sha256(path)
        if not sha:
            return _ERROR
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
    def test_api_key(self, key: str) -> bool:
        return False
    def lookup(self, exe_path: str) -> tuple[int, int] | None:
        return None
