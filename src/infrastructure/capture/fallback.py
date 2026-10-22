"""Captura con degradación: si el backend nativo por proceso (ETW / nettop)
no arranca o muere en runtime, pasa a psutil (global) en vez de dejar la app
sin medir.

Contrato duck-typed con el primario: expone un atributo `on_failure` que el
primario llama desde su propio hilo cuando ya no puede capturar. No va al
puerto de dominio a propósito (solo los backends nativos lo necesitan).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from ...domain.models import TrafficSample
from ...domain.ports import CaptureService

log = logging.getLogger(__name__)


class FallbackCaptureService(CaptureService):
    def __init__(self, primary: CaptureService,
                 make_fallback: Callable[[], CaptureService]) -> None:
        self._primary = primary
        self._make_fallback = make_fallback
        self._active: CaptureService = primary
        self._on_sample: Callable[[TrafficSample], None] | None = None
        self._lock = threading.Lock()
        self._stopped = True
        primary.on_failure = self._switch  # type: ignore[attr-defined]

    @property
    def primary(self) -> CaptureService:
        return self._primary

    @property
    def degraded(self) -> bool:
        return self._active is not self._primary

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        with self._lock:
            self._on_sample = on_sample
            self._stopped = False
        try:
            self._primary.start(on_sample)
        except Exception:  # noqa: BLE001
            log.exception("La captura nativa no arrancó; uso psutil (global)")
            self._switch()

    def _switch(self) -> None:
        with self._lock:
            if self._stopped or self.degraded or self._on_sample is None:
                return
            log.warning("Captura nativa caída: paso a psutil (medición global).")
            try:
                self._primary.stop()
            except Exception:  # noqa: BLE001
                log.exception("Fallo deteniendo la captura nativa caída")
            fallback = self._make_fallback()
            fallback.start(self._on_sample)
            self._active = fallback

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            active = self._active
        active.stop()
