"""Persistencia de Settings en un archivo JSON."""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path

from ...domain.models import Settings
from ...domain.ports import SecretStore, SettingsStore

_log = logging.getLogger(__name__)

_READ_RETRIES = 3
_READ_RETRY_DELAY_S = 0.1
_VT_SECRET = "virustotal_api_key"


class JsonSettingsStore(SettingsStore):
    def __init__(self, path: str | Path, secrets: SecretStore | None = None) -> None:
        self._path = Path(path)
        self._secrets = secrets
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # True si no pudimos LEER un settings.json existente (AV/OneDrive): save()
        # no-op para no pisar la config real con defaults.
        self._read_failed = False

    def _read_text(self) -> str:
        for attempt in range(_READ_RETRIES):
            try:
                return self._path.read_text("utf-8")
            except OSError:
                if attempt == _READ_RETRIES - 1:
                    raise
                time.sleep(_READ_RETRY_DELAY_S)
        raise AssertionError("unreachable")

    def _secrets_ok(self) -> bool:
        return self._secrets is not None and self._secrets.available

    def _with_secret(self, settings: Settings) -> Settings:
        """Completa la API key desde el almacén de secretos (si hay y está disponible)."""
        if self._secrets_ok():
            stored = self._secrets.get(_VT_SECRET)
            if stored:
                settings.virustotal_api_key = stored
        return settings

    def load(self) -> Settings:
        if not self._path.exists():
            return self._with_secret(Settings())
        try:
            text = self._read_text()
        except OSError:
            self._read_failed = True
            _log.warning("No se pudo leer %s (error transitorio): defaults en memoria y "
                         "no se sobrescribe el archivo.", self._path.name, exc_info=True)
            return self._with_secret(Settings())
        self._read_failed = False
        try:
            settings = Settings.from_dict(json.loads(text))
        except Exception as exc:  # noqa: BLE001 — JSON roto/tipos raros: nunca impedir el arranque
            self._backup_corrupt(exc)
            return self._with_secret(Settings())
        self._migrate_plaintext_key(settings)
        return self._with_secret(settings)

    def _migrate_plaintext_key(self, settings: Settings) -> None:
        """Si el JSON trae la key en texto plano y hay almacén, la mueve y reescribe el JSON."""
        plain = settings.virustotal_api_key
        if not plain or not self._secrets_ok():
            return
        self._secrets.set(_VT_SECRET, plain)
        if not self._secrets.available or self._secrets.get(_VT_SECRET) != plain:
            return  # no quedó guardada: se conserva el texto plano
        try:
            self._write(settings, key_in_json=False)
        except OSError:
            _log.warning("No se pudo reescribir %s tras migrar la API key.",
                         self._path.name, exc_info=True)

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
        if self._read_failed:
            _log.warning("Lectura previa fallida: no se guarda %s para no pisar la "
                         "configuración real.", self._path.name)
            return
        key_in_json = True
        if self._secrets_ok():
            self._secrets.set(_VT_SECRET, settings.virustotal_api_key)
            key_in_json = not self._secrets.available
        if key_in_json and settings.virustotal_api_key:
            _log.warning("Almacén de credenciales no disponible: la API key se guarda en "
                         "texto plano en %s.", self._path.name)
        self._write(settings, key_in_json=key_in_json)

    def _write(self, settings: Settings, *, key_in_json: bool) -> None:
        data = settings.to_dict()
        if not key_in_json:
            data[_VT_SECRET] = ""
        # Escritura atómica: tmp + os.replace. Un crash a mitad deja el archivo viejo.
        tmp = self._path.with_name(self._path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
