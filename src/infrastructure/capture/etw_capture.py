"""Captura por proceso usando ETW (Event Tracing for Windows).

Consume el provider de kernel `Microsoft-Windows-Kernel-Network`
(GUID {7DD42A49-5329-4832-8DFD-43D979153A88}), que emite un evento por
cada operación TCP/UDP con el PID origen y la cantidad de bytes.

REQUISITOS:
  - Ejecutar como Administrador (las sesiones de kernel ETW lo exigen).
  - Paquete `pywintrace` instalado (expone el módulo `etw`).

Si algo de eso falta, esta clase lanza CaptureUnavailable y la fábrica
cae automáticamente al PsutilCaptureService (medición global).
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from ...domain.models import TrafficSample
from ...domain.ports import CaptureService
from .app_names import friendly_name

log = logging.getLogger(__name__)


class CaptureUnavailable(RuntimeError):
    """ETW no se puede inicializar en este entorno."""


# IDs de evento del provider Microsoft-Windows-Kernel-Network, VALIDADOS contra
# captura real (2026-06-17, ver diagnose.py):
#   10/26 = TCP send IPv4/IPv6   ·   11/27 = TCP recv IPv4/IPv6 ("bytes received")
#   42/58 = UDP send IPv4/IPv6   ·   43/59 = UDP recv IPv4/IPv6
# Los eventos 12/28 (connect) traen size=0 y se ignoran.
# IMPORTANTE: 18/34 ("bytes copied in protocol on behalf of user") son un SEGUNDO
# conteo de lo ya recibido en 11/27 — se EXCLUYEN para no duplicar la bajada.
_SENT_EVENTS = {10, 26}   # TCP send IPv4/IPv6
_RECV_EVENTS = {11, 27}   # TCP recv IPv4/IPv6
_UDP_SENT = {42, 58}
_UDP_RECV = {43, 59}


class EtwCaptureService(CaptureService):
    KERNEL_NETWORK_GUID = "{7DD42A49-5329-4832-8DFD-43D979153A88}"

    def __init__(self) -> None:
        self._etw = None
        self._thread: threading.Thread | None = None
        self._on_sample: Callable[[TrafficSample], None] | None = None
        self._sample_errors = 0
        # Salud: si la sesión ETW muere, failed=True y se avisa a on_failure
        # (lo engancha FallbackCaptureService para degradar a psutil).
        self.failed = False
        self.on_failure: Callable[[], None] | None = None

    def _resolve_name(self, pid: int) -> str:
        # Corre DENTRO del callback de ETW. El primer evento de un PID hace IO
        # (psutil + version.dll); los siguientes son hits O(1) del cache de
        # app_names, re-verificado por create_time cada pocos segundos.
        return friendly_name(pid)

    def _build_session(self):
        try:
            from etw import ETW, ProviderInfo  # type: ignore
            from etw.GUID import GUID  # type: ignore
        except ImportError as exc:  # pywintrace ausente
            raise CaptureUnavailable(
                "pywintrace no está instalado; no se puede usar ETW."
            ) from exc

        providers = [ProviderInfo("Kernel-Network", GUID(self.KERNEL_NETWORK_GUID))]
        return ETW(providers=providers, event_callback=self._on_event)

    def _on_event(self, event) -> None:
        # pywintrace entrega (event_id, {campos})
        try:
            event_id, data = event
            pid = int(data.get("PID", data.get("ProcessId", 0)))
            size = int(data.get("size", data.get("Size", 0)))
        except (ValueError, TypeError, AttributeError):
            return
        on_sample = self._on_sample
        if pid <= 0 or size <= 0 or on_sample is None:
            return

        sent = size if event_id in _SENT_EVENTS or event_id in _UDP_SENT else 0
        recv = size if event_id in _RECV_EVENTS or event_id in _UDP_RECV else 0
        if sent == 0 and recv == 0:
            return

        try:
            on_sample(
                TrafficSample(
                    pid=pid,
                    app_name=self._resolve_name(pid),
                    bytes_sent=sent,
                    bytes_recv=recv,
                )
            )
        except Exception:  # noqa: BLE001
            # Nunca propagar al callback de pywintrace (puede matar el consumer).
            # Log con throttle: ETW emite cientos de eventos por segundo.
            if self._sample_errors % 1000 == 0:
                log.exception("ETW: on_sample falló (%d errores)", self._sample_errors + 1)
            self._sample_errors += 1

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self._on_sample = on_sample
        self.failed = False
        self._etw = self._build_session()
        self._thread = threading.Thread(
            target=self._run, args=(self._etw,), daemon=True
        )
        self._thread.start()

    def _run(self, session) -> None:
        try:
            session.start()
        except Exception:  # noqa: BLE001
            log.exception("ETW: la sesión de captura falló")
            self.failed = True
            callback = self.on_failure
            if callback is not None:
                try:
                    callback()
                except Exception:  # noqa: BLE001
                    log.exception("ETW: fallo activando el fallback")

    def stop(self) -> None:
        session, self._etw = self._etw, None
        if session is not None:
            try:
                session.stop()
            except Exception:  # noqa: BLE001
                log.debug("ETW: fallo al detener la sesión", exc_info=True)
        thread, self._thread = self._thread, None
        # on_failure -> FallbackCaptureService -> stop() corre en el propio hilo.
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._on_sample = None
