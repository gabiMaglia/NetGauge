"""VT: carrera del worker, errores transitorios y set_api_key (HTTP falso)."""
from __future__ import annotations

import json
import queue
import time
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.capture import reputation_virustotal as vtmod
from src.infrastructure.capture.reputation_virustotal import VirusTotalReputation


def _wait_until(pred, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


def _resp(body: bytes):
    m = MagicMock()
    m.__enter__.return_value = m
    m.read.return_value = body
    m.status = 200
    return m


def _http_error(code):
    return urllib.error.HTTPError("https://vt", code, "x", {}, None)


@pytest.fixture
def exe(tmp_path):
    p = tmp_path / "a.exe"
    p.write_bytes(b"MZ-fake")
    return str(p)


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(vtmod, "_MIN_INTERVAL", 0.0)


class _RacyQueue(queue.Queue):
    """Simula la carrera: el 1er get() ve la cola vacía y, justo antes de que el
    worker decida salir, otro hilo encola un item."""

    def __init__(self, item):
        super().__init__()
        self._item = item
        self._armed = True

    def get(self, block=True, timeout=None):
        if self._armed:
            self._armed = False
            self.put(self._item)
            raise queue.Empty
        return super().get(block, timeout)


def test_worker_no_pierde_un_item_encolado_mientras_sale_por_idle(monkeypatch):
    monkeypatch.setattr(vtmod, "_IDLE_TIMEOUT", 0.01)
    vt = VirusTotalReputation("key")
    monkeypatch.setattr(vt, "_query", lambda p: (2, 70))
    vt._q = _RacyQueue("C:/x.exe")
    vt._queued.add("C:/x.exe")
    vt._run()   # sincrónico: debe procesar el item aunque get() levantó Empty
    assert vt._cache["C:/x.exe"] == (2, 70)


def test_worker_se_reinicia_tras_idle(monkeypatch):
    monkeypatch.setattr(vtmod, "_IDLE_TIMEOUT", 0.05)
    vt = VirusTotalReputation("key")
    monkeypatch.setattr(vt, "_query", lambda p: (0, 70))
    vt.lookup("a")
    assert _wait_until(lambda: isinstance(vt._cache.get("a"), tuple))
    assert _wait_until(lambda: vt._worker is None)   # salió por idle
    vt.lookup("b")
    assert _wait_until(lambda: isinstance(vt._cache.get("b"), tuple))


def test_error_http_transitorio_no_se_cachea_y_hace_backoff(monkeypatch, exe):
    now = [1000.0]
    vt = VirusTotalReputation("key", clock=lambda: now[0])
    monkeypatch.setattr(VirusTotalReputation, "_ensure_worker_locked",
                        lambda self: None)
    assert vt.lookup(exe) is None
    assert vt._q.get_nowait() == exe
    with patch("urllib.request.urlopen", side_effect=_http_error(429)):
        vt._process(exe)
    assert exe not in vt._cache                  # NO queda "error" para siempre
    assert exe not in vt._queued
    assert vt.lookup(exe) is None and vt._q.qsize() == 0   # en backoff: no reencola
    now[0] += vtmod._BACKOFF_BASE + 1
    assert vt.lookup(exe) is None and vt._q.qsize() == 1   # pasó el backoff


@pytest.mark.parametrize("code", [401, 403, 500, 503])
def test_otros_http_no_404_tampoco_se_cachean(monkeypatch, exe, code):
    vt = VirusTotalReputation("key")
    monkeypatch.setattr(VirusTotalReputation, "_ensure_worker_locked",
                        lambda self: None)
    with patch("urllib.request.urlopen", side_effect=_http_error(code)):
        vt._process(exe)
    assert exe not in vt._cache


def test_backoff_es_exponencial(exe):
    now = [0.0]
    vt = VirusTotalReputation("key", clock=lambda: now[0])
    with patch("urllib.request.urlopen", side_effect=_http_error(429)):
        vt._process(exe)
        assert vt._retry_at[exe] - now[0] == vtmod._BACKOFF_BASE
        vt._process(exe)
        assert vt._retry_at[exe] - now[0] == vtmod._BACKOFF_BASE * 2


def test_404_se_cachea_como_unknown(exe):
    vt = VirusTotalReputation("key")
    with patch("urllib.request.urlopen", side_effect=_http_error(404)):
        vt._process(exe)
    assert vt._cache[exe] == vtmod._UNKNOWN


def test_200_se_cachea_con_resultado(exe):
    vt = VirusTotalReputation("key")
    body = json.dumps({"data": {"attributes": {"last_analysis_stats": {
        "malicious": 2, "suspicious": 1, "harmless": 60, "undetected": 7}}}})
    with patch("urllib.request.urlopen", return_value=_resp(body.encode())):
        vt._process(exe)
    assert vt._cache[exe] == (3, 70)


def test_set_api_key_limpia_errores_y_backoffs_pero_no_resultados():
    vt = VirusTotalReputation("old")
    vt._cache.update({"x": "error", "y": (1, 2), "z": vtmod._UNKNOWN})
    vt._retry_at["w"] = 99999.0
    vt._fails["w"] = 3
    vt.set_api_key("new")
    assert "x" not in vt._cache
    assert vt._cache["y"] == (1, 2) and vt._cache["z"] == vtmod._UNKNOWN
    assert vt._retry_at == {} and vt._fails == {}
    assert vt._api_key == "new"


# --- test_api_key -------------------------------------------------------
_EICAR = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"


def test_api_key_200_es_valida():
    vt = VirusTotalReputation()
    with patch("urllib.request.urlopen", return_value=_resp(b"{}")):
        assert vt.test_api_key("k") is True


def test_api_key_404_es_valida():
    vt = VirusTotalReputation()
    with patch("urllib.request.urlopen", side_effect=_http_error(404)):
        assert vt.test_api_key("k") is True


@pytest.mark.parametrize("code", [401, 403, 429, 500])
def test_api_key_otros_http_es_invalida(code):
    vt = VirusTotalReputation()
    with patch("urllib.request.urlopen", side_effect=_http_error(code)):
        assert vt.test_api_key("k") is False


@pytest.mark.parametrize("exc", [
    TimeoutError("t"), ConnectionResetError("r"), ValueError("v"),
    OSError("o"), RuntimeError("cualquier cosa")])
def test_api_key_cualquier_excepcion_devuelve_false(exc):
    vt = VirusTotalReputation()
    with patch("urllib.request.urlopen", side_effect=exc):
        assert vt.test_api_key("k") is False


def test_api_key_no_va_en_la_url_sino_en_el_header():
    vt = VirusTotalReputation()
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["url"] = req.full_url
        seen["key"] = req.get_header("X-apikey")
        return _resp(b"{}")
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        assert vt.test_api_key("SECRETA") is True
    assert "SECRETA" not in seen["url"]
    assert seen["url"].endswith(_EICAR)
    assert seen["key"] == "SECRETA"


def test_api_key_vacia_no_toca_la_red():
    vt = VirusTotalReputation()
    with patch("urllib.request.urlopen") as m:
        assert vt.test_api_key("   ") is False
    m.assert_not_called()


def test_set_api_key_same_key_keeps_backoff():
    vt = VirusTotalReputation(api_key="K")
    vt._retry_at["x.exe"] = 999.0
    vt._fails["x.exe"] = 2
    vt._cache["e.exe"] = vtmod._ERROR
    vt.set_api_key("K")
    assert vt._retry_at == {"x.exe": 999.0}
    assert vt._fails == {"x.exe": 2}
    assert vt._cache["e.exe"] == vtmod._ERROR


def test_set_api_key_different_key_clears_backoff():
    vt = VirusTotalReputation(api_key="K")
    vt._retry_at["x.exe"] = 999.0
    vt._fails["x.exe"] = 2
    vt._cache["e.exe"] = vtmod._ERROR
    vt.set_api_key("OTHER")
    assert vt._retry_at == {} and vt._fails == {} and "e.exe" not in vt._cache
