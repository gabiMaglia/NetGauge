"""JsonSettingsStore: escritura atómica y load() robusto ante archivos dañados."""
from __future__ import annotations

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
