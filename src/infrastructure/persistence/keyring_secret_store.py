"""SecretStore sobre el almacén de credenciales del SO (Credential Manager / Keychain)."""
from __future__ import annotations

import logging

import keyring
import keyring.errors

from ...domain.ports import SecretStore

_log = logging.getLogger(__name__)


class KeyringSecretStore(SecretStore):
    def __init__(self, service: str = "NetGauge") -> None:
        self._service = service
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    def _fail(self, op: str, exc: Exception) -> None:
        self._available = False
        _log.warning("keyring no disponible (%s): %r", op, exc)

    def get(self, name: str) -> str | None:
        try:
            return keyring.get_password(self._service, name)
        except Exception as exc:  # noqa: BLE001 — sin backend / keychain bloqueado
            self._fail("get", exc)
            return None

    def set(self, name: str, value: str) -> None:
        try:
            if value:
                keyring.set_password(self._service, name, value)
            else:
                try:
                    keyring.delete_password(self._service, name)
                except keyring.errors.PasswordDeleteError:
                    pass  # ya no existía
        except Exception as exc:  # noqa: BLE001
            self._fail("set", exc)
