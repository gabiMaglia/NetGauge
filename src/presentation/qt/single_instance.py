"""Garantiza una sola instancia. Si ya hay una abierta, le pide que se muestre.

Usa QLocalServer/QLocalSocket (named pipe en Windows): la 1ª instancia abre un
servidor con una clave fija; las siguientes detectan que ya existe, le envían un
mensaje para que traiga su ventana al frente, y se cierran.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtNetwork import QLocalServer, QLocalSocket

_KEY = "trafficMe.single-instance.v1"
_PING = b"show"


class SingleInstance:
    def __init__(self, key: str = _KEY) -> None:
        self._key = key
        self._server: QLocalServer | None = None

    def already_running(self) -> bool:
        """True si otra instancia respondió. Le manda 'mostrate' de paso."""
        sock = QLocalSocket()
        sock.connectToServer(self._key)
        if sock.waitForConnected(250):
            sock.write(_PING)
            sock.flush()
            sock.waitForBytesWritten(250)
            sock.disconnectFromServer()
            return True
        return False

    def listen(self, on_show: Callable[[], None]) -> None:
        """Arranca el servidor de esta instancia (la primera)."""
        QLocalServer.removeServer(self._key)  # limpia un pipe huérfano si quedó
        self._server = QLocalServer()
        self._server.listen(self._key)
        self._server.newConnection.connect(
            lambda: self._on_connection(on_show))

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
