"""Garantiza una sola instancia POR USUARIO. Si ya hay una abierta, le pide que se muestre.

Usa QLocalServer/QLocalSocket (named pipe en Windows): la 1ª instancia abre un
servidor; las siguientes detectan que ya existe, le envían un mensaje para que
traiga su ventana al frente, y se cierran.

La clave incluye el usuario: en Windows el named pipe es global a la máquina, y
con varias sesiones (RDP / cambio rápido de usuario) el usuario B le mandaría
"show" a la instancia del usuario A y se cerraría sin abrir la suya.
"""
from __future__ import annotations

import getpass
import re
from typing import Callable

from PySide6.QtNetwork import QLocalServer, QLocalSocket

_KEY_PREFIX = "NetGauge.single-instance.v1"
_PING = b"show"
_CONNECT_TIMEOUT_MS = 1000


def build_key(user: str | None = None) -> str:
    """Clave del pipe: prefijo fijo + usuario sanitizado (solo [A-Za-z0-9_.-])."""
    if user is None:
        try:
            user = getpass.getuser()
        except Exception:  # noqa: BLE001 — sin usuario resoluble: clave genérica
            user = "user"
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", user or "") or "user"
    return f"{_KEY_PREFIX}.{safe}"


class SingleInstance:
    def __init__(self, key: str | None = None,
                 server_factory: Callable[[], QLocalServer] = QLocalServer) -> None:
        self._key = key or build_key()
        self._server_factory = server_factory
        self._server: QLocalServer | None = None

    def already_running(self) -> bool:
        """True si otra instancia respondió. Le manda 'mostrate' de paso."""
        sock = QLocalSocket()
        sock.connectToServer(self._key)
        if sock.waitForConnected(_CONNECT_TIMEOUT_MS):
            sock.write(_PING)
            sock.flush()
            sock.waitForBytesWritten(_CONNECT_TIMEOUT_MS)
            sock.disconnectFromServer()
            return True
        return False

    def listen(self, on_show: Callable[[], None]) -> bool:
        """Arranca el servidor de esta instancia (la primera).

        Devuelve True si quedó escuchando. Si `listen` falla, primero verifica que
        no haya otra instancia viva (removeServer borraría su socket en macOS); si
        nadie responde, limpia el pipe huérfano con removeServer y reintenta UNA vez.
        """
        for _attempt in range(2):
            server = self._server_factory()
            if server.listen(self._key):
                self._server = server
                server.newConnection.connect(
                    lambda: self._on_connection(on_show))
                return True
            if self.already_running():
                return False  # hay dueño vivo: no tocar su socket
            server.removeServer(self._key)  # pipe huérfano
        return False

    def _on_connection(self, on_show: Callable[[], None]) -> None:
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        on_show()
        conn.disconnectFromServer()
        conn.deleteLater()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
