"""Persistencia de Settings en un archivo JSON."""
from __future__ import annotations

import json
from pathlib import Path

from ...domain.models import Settings
from ...domain.ports import SettingsStore


class JsonSettingsStore(SettingsStore):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        try:
            return Settings.from_dict(json.loads(self._path.read_text("utf-8")))
        except (json.JSONDecodeError, OSError, ValueError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self._path.write_text(
            json.dumps(settings.to_dict(), indent=2), encoding="utf-8"
        )
