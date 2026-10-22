# tests/test_single_instance.py
"""Instancia única: clave por usuario, listen() verificado."""
from __future__ import annotations

from src.presentation.qt import single_instance as si
from src.presentation.qt.single_instance import SingleInstance, build_key


def test_key_incluye_el_usuario():
    assert build_key("alice") != build_key("bob")
    assert build_key("alice").endswith(".alice")


def test_key_sanitiza_caracteres_raros():
    k = build_key("DOMINIO\\gab riel")
    assert "\\" not in k and " " not in k


def test_key_usa_getuser_por_defecto(monkeypatch):
    monkeypatch.setattr(si.getpass, "getuser", lambda: "carol")
    assert build_key().endswith(".carol")


def test_key_fallback_si_getuser_falla(monkeypatch):
    def boom():
        raise OSError("sin usuario")
    monkeypatch.setattr(si.getpass, "getuser", boom)
    assert build_key().endswith(".user")


class _FakeSignal:
    def connect(self, _f):
        pass


class _FakeServer:
    """Falla `fail_times` veces en listen() y después anda."""
    removed: list[str] = []

    def __init__(self, fail_times: int) -> None:
        self._fail = fail_times
        self.listen_calls = 0
        self.newConnection = _FakeSignal()

    def removeServer(self, key):  # en Qt es estático; acá basta por instancia
        _FakeServer.removed.append(key)

    def listen(self, key):
        self.listen_calls += 1
        if self._fail > 0:
            self._fail -= 1
            return False
        return True

    def close(self):
        pass


def _guard(fail_times):
    _FakeServer.removed = []
    servers = []

    def factory():
        s = _FakeServer(fail_times)
        servers.append(s)
        return s
    g = SingleInstance(key="k", server_factory=factory)
    return g, servers


def test_listen_ok_a_la_primera():
    g, servers = _guard(0)
    assert g.listen(lambda: None) is True
    assert servers[0].listen_calls == 1


def test_listen_reintenta_una_vez_tras_removeServer():
    # Cada server falso falla su 1er listen; el reintento usa un server nuevo
    # con fail_times=1 también, así que modelamos "falla una vez en total":
    _FakeServer.removed = []
    state = {"n": 0}
    servers = []

    def factory():
        s = _FakeServer(1 if state["n"] == 0 else 0)
        state["n"] += 1
        servers.append(s)
        return s
    g = SingleInstance(key="k", server_factory=factory)
    assert g.listen(lambda: None) is True
    assert len(servers) == 2                       # server nuevo en el reintento
    assert _FakeServer.removed.count("k") >= 1     # limpieza del pipe huérfano tras el fallo


def test_listen_falla_dos_veces_devuelve_false():
    g, _ = _guard(5)
    assert g.listen(lambda: None) is False


def test_listen_no_borra_el_socket_si_hay_instancia_viva(monkeypatch):
    g, servers = _guard(5)
    monkeypatch.setattr(g, "already_running", lambda: True)
    assert g.listen(lambda: None) is False
    assert _FakeServer.removed == []               # borraría el socket vivo (macOS)
    assert len(servers) == 1


def test_listen_limpia_huerfano_si_nadie_responde(monkeypatch):
    g, servers = _guard(5)
    monkeypatch.setattr(g, "already_running", lambda: False)
    assert g.listen(lambda: None) is False
    assert _FakeServer.removed.count("k") >= 1


class _FakeGuard:
    def __init__(self, running): self._running = running
    def already_running(self): return self._running


def test_listen_fallido_con_otra_instancia_sale_con_0():
    from src.presentation.qt.app import should_exit_after_listen_failure
    assert should_exit_after_listen_failure(_FakeGuard(True)) is True


def test_listen_fallido_sin_otra_instancia_continua_con_warning(caplog):
    import logging
    from src.presentation.qt.app import should_exit_after_listen_failure
    with caplog.at_level(logging.WARNING):
        assert should_exit_after_listen_failure(_FakeGuard(False)) is False
    assert any("instancia única" in r.getMessage() for r in caplog.records)
