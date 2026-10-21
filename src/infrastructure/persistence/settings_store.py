"""Persistencia de Settings en un archivo JSON."""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from ...domain.models import Settings
from ...domain.ports import SettingsStore

_log = logging.getLogger(__name__)


class JsonSettingsStore(SettingsStore):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        try:
            return Settings.from_dict(json.loads(self._path.read_text("utf-8")))
        except Exception as exc:  # noqa: BLE001 — JSON roto/tipos raros: nunca impedir el arranque
            self._backup_corrupt(exc)
            return Settings()

    def _backup_corrupt(self, exc: Exception) -> None:
        """Guarda el archivo ilegible en settings.json.bak antes de usar defaults."""
        bak = self._path.with_name(self._path.name + ".bak")
        try:
            shutil.copy2(self._path, bak)
        except OSError:
            _log.exception("No se pudo respaldar %s", self._path.name)
        _log.warning("%s ilegible (%r): se usan valores por defecto; copia en %s.",
                     self._path.name, exc, bak.name)

    def save(self, settings: Settings) -> None:
        # Escritura atómica: tmp + os.replace. Un crash a mitad deja el archivo viejo.
        tmp = self._path.with_name(self._path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(settings.to_dict(), fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
