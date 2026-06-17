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

import threading
from typing import Callable

from ...domain.models import TrafficSample
from ...domain.ports import CaptureService
from .app_names import friendly_name


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

    def _resolve_name(self, pid: int) -> str:
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
        if pid <= 0 or size <= 0 or self._on_sample is None:
            return

        sent = size if event_id in _SENT_EVENTS or event_id in _UDP_SENT else 0
        recv = size if event_id in _RECV_EVENTS or event_id in _UDP_RECV else 0
        if sent == 0 and recv == 0:
            return

        self._on_sample(
            TrafficSample(
                pid=pid,
                app_name=self._resolve_name(pid),
                bytes_sent=sent,
                bytes_recv=recv,
            )
        )

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self._on_sample = on_sample
        self._etw = self._build_session()
        self._thread = threading.Thread(target=self._etw.start, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._etw is not None:
            try:
                self._etw.stop()
            except Exception:
                pass
            self._etw = None
