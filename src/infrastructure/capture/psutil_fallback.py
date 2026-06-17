"""Fallback de captura GLOBAL usando psutil.

Importante: psutil NO mide tráfico por proceso. Esta implementación reparte
el delta global de la red en una pseudo-app "Sistema (global)". Sirve para que
la app funcione sin privilegios de Administrador o sin ETW, dejando claro al
usuario que el desglose por aplicación requiere el modo ETW.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

import psutil

from ...domain.models import TrafficSample
from ...domain.ports import CaptureService

_GLOBAL_APP = "Sistema (global)"


class PsutilCaptureService(CaptureService):
    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, args=(on_sample,), daemon=True
        )
        self._thread.start()

    def _loop(self, on_sample: Callable[[TrafficSample], None]) -> None:
        prev = psutil.net_io_counters()
        while not self._stop_event.is_set():
            time.sleep(self._interval)
            cur = psutil.net_io_counters()
            sent = max(0, cur.bytes_sent - prev.bytes_sent)
            recv = max(0, cur.bytes_recv - prev.bytes_recv)
            prev = cur
            if sent or recv:
                on_sample(
                    TrafficSample(
                        pid=0, app_name=_GLOBAL_APP, bytes_sent=sent, bytes_recv=recv
                    )
                )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)
