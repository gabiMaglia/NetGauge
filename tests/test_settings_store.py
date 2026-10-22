"""JsonSettingsStore: escritura atómica y load() robusto ante archivos dañados."""
from __future__ import annotations

import json

import pytest

from src.domain.models import Settings
from src.infrastructure.persistence import settings_store as ss
from src.infrastructure.persistence.settings_store import JsonSettingsStore


def test_save_then_load_roundtrip(tmp_path):
    store = JsonSettingsStore(tmp_path / "settings.json")
    store.save(Settings(monthly_quota_gb=50.0, virustotal_api_key="k"))

    loaded = store.load()
    assert loaded.monthly_quota_gb == 50.0
    assert loaded.virustotal_api_key == "k"


def test_save_writes_via_tmp_and_os_replace(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    calls = []
    real_replace = ss.os.replace

    def spy(src, dst):
        calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(ss.os, "replace", spy)
    JsonSettingsStore(path).save(Settings(monthly_quota_gb=1.0))

    assert calls == [(str(path) + ".tmp", str(path))]
    assert not (tmp_path / "settings.json.tmp").exists()


def test_failed_save_keeps_previous_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    store.save(Settings(monthly_quota_gb=50.0, virustotal_api_key="k"))
    before = path.read_bytes()

    def boom(src, dst):
        raise OSError("disco lleno")

    monkeypatch.setattr(ss.os, "replace", boom)
    with pytest.raises(OSError):
        store.save(Settings(monthly_quota_gb=99.0))

    assert path.read_bytes() == before
    assert not (tmp_path / "settings.json.tmp").exists()


@pytest.mark.parametrize("content", [
    '{"monthly_quota_gb": 50',                 # truncado (crash a mitad de write)
    '{"monthly_quota_gb": null}',              # TypeError en float(None)
    '[1, 2, 3]',                               # AttributeError: list.get
    'null',                                    # AttributeError: None.get
    '{"alert_thresholds": 5}',                 # TypeError en tuple(5)
])
def test_unreadable_settings_return_defaults_and_keep_backup(tmp_path, content, caplog):
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")

    loaded = JsonSettingsStore(path).load()

    assert loaded == Settings()
    assert (tmp_path / "settings.json.bak").read_text("utf-8") == content
    assert "settings.json" in caplog.text


def test_valid_settings_do_not_create_backup(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"monthly_quota_gb": 10}), encoding="utf-8")

    assert JsonSettingsStore(path).load().monthly_quota_gb == 10.0
    assert not (tmp_path / "settings.json.bak").exists()


# ---- re-auditoría A8: error transitorio de lectura no pisa la config real ----
def test_transient_read_error_does_not_overwrite_real_settings(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    JsonSettingsStore(path).save(Settings(monthly_quota_gb=50.0))
    store = JsonSettingsStore(path)
    monkeypatch.setattr(ss.time, "sleep", lambda _s: None, raising=False)
    real_read = type(path).read_text

    def locked(self, *a, **k):
        if self.name == "settings.json":
            raise PermissionError("antivirus")
        return real_read(self, *a, **k)

    monkeypatch.setattr(type(path), "read_text", locked)
    assert store.load() == Settings()          # defaults para poder arrancar
    store.save(Settings(monthly_quota_gb=1.0))  # no debe pisar el archivo real

    monkeypatch.undo()
    assert json.loads(path.read_text("utf-8"))["monthly_quota_gb"] == 50.0


def test_transient_read_error_is_retried(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    JsonSettingsStore(path).save(Settings(monthly_quota_gb=7.0))
    store = JsonSettingsStore(path)
    monkeypatch.setattr(ss.time, "sleep", lambda _s: None, raising=False)
    real_read = type(path).read_text
    state = {"n": 0}

    def flaky(self, *a, **k):
        state["n"] += 1
        if state["n"] < 3:
            raise PermissionError("onedrive")
        return real_read(self, *a, **k)

    monkeypatch.setattr(type(path), "read_text", flaky)
    assert store.load().monthly_quota_gb == 7.0
