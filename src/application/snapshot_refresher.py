"""Worker de fondo que mantiene fresco el snapshot que lee la UI.

Un ÚNICO hilo en la capa de aplicación (decisión del spec de release audit):
la UI nunca hace IO (SQLite, psutil, WinVerifyTrust); sólo lee lo que este
hilo dejó listo. Alternativa descartada: QThreadPool en presentación (mete
lógica de negocio en Qt).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

_log = logging.getLogger(__name__)


class SnapshotRefresher:
    def __init__(self, refresh: Callable[[], None], interval: float = 2.0,
                 on_refreshed: Callable[[], None] | None = None) -> None:
        self._refresh = refresh
        self._interval = interval
        self._on_refreshed = on_refreshed
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_listener(self, callback: Callable[[], None] | None) -> None:
        """Callback tras cada refresco. Corre en ESTE hilo: el receptor (UI)
        es responsable de saltar a su propio hilo (ej. señal Qt encolada)."""
        self._on_refreshed = callback

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="netgauge-snapshot", daemon=True)
        self._thread.start()

    def trigger(self) -> None:
        """Pide un refresco ya, sin esperar al intervalo. No bloquea."""
        self._wake.set()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            # Si un refresco está trabado (ej. WinVerifyTrust lento) no
            # bloqueamos el cierre más de `timeout`: el hilo es daemon.
            thread.join(timeout)
        self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._refresh()
            except Exception:  # noqa: BLE001 — el worker nunca muere en silencio
                _log.exception("Fallo refrescando el snapshot de la UI")
            if self._stop.is_set():
                break
            callback = self._on_refreshed
            if callback is not None:
                try:
                    callback()
                except Exception:  # noqa: BLE001
                    _log.exception("Fallo notificando el snapshot a la UI")
            # Un trigger() que llegó DURANTE el refresco deja el evento puesto:
            # wait() vuelve enseguida y se refresca de nuevo (no se pierde).
            self._wake.wait(self._interval)
            self._wake.clear()
