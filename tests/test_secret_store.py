"""KeyringSecretStore: nunca propaga errores del backend; jamás toca el keyring real."""
from __future__ import annotations

import keyring
import keyring.errors

from src.infrastructure.persistence import keyring_secret_store as kss
from src.infrastructure.persistence.keyring_secret_store import KeyringSecretStore


def _boom(*_a, **_k):
    raise keyring.errors.NoKeyringError("sin backend")


def test_set_and_get_use_service_and_name(monkeypatch):
    data = {}
    monkeypatch.setattr(kss.keyring, "set_password", lambda s, n, v: data.__setitem__((s, n), v))
    monkeypatch.setattr(kss.keyring, "get_password", lambda s, n: data.get((s, n)))
    store = KeyringSecretStore(service="Svc")

    store.set("vt", "abc")

    assert data == {("Svc", "vt"): "abc"}
    assert store.get("vt") == "abc"
    assert store.available is True


def test_empty_value_deletes(monkeypatch):
    deleted = []
    monkeypatch.setattr(kss.keyring, "delete_password", lambda s, n: deleted.append((s, n)))
    KeyringSecretStore(service="Svc").set("vt", "")
    assert deleted == [("Svc", "vt")]


def test_delete_missing_is_silent(monkeypatch):
    def missing(*_a):
        raise keyring.errors.PasswordDeleteError("no existe")

    monkeypatch.setattr(kss.keyring, "delete_password", missing)
    store = KeyringSecretStore(service="Svc")
    store.set("vt", "")
    assert store.available is True


def test_backend_failure_marks_unavailable_without_raising(monkeypatch, caplog):
    monkeypatch.setattr(kss.keyring, "get_password", _boom)
    monkeypatch.setattr(kss.keyring, "set_password", _boom)
    store = KeyringSecretStore(service="Svc")

    assert store.get("vt") is None
    assert store.available is False
    store.set("vt", "abc")  # no lanza
    assert "keyring" in caplog.text.lower()
