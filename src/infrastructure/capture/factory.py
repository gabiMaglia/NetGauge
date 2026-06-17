"""Fábrica de captura: intenta ETW (por proceso) y cae a psutil (global)."""
from __future__ import annotations

import ctypes
import logging

from ...domain.ports import CaptureService
from .etw_capture import CaptureUnavailable, EtwCaptureService
from .psutil_fallback import PsutilCaptureService

log = logging.getLogger(__name__)


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def create_capture_service(prefer_etw: bool = True) -> tuple[CaptureService, bool]:
    """Devuelve (servicio, es_por_proceso).

    es_por_proceso=True => ETW activo (desglose real por app).
    es_por_proceso=False => fallback global con psutil.
    """
    if prefer_etw and _is_admin():
        try:
            service = EtwCaptureService()
            # Validamos que pywintrace exista antes de comprometernos.
            service._build_session().stop()
            log.info("Captura ETW por proceso activada.")
            return EtwCaptureService(), True
        except CaptureUnavailable as exc:
            log.warning("ETW no disponible (%s). Uso fallback psutil.", exc)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fallo inicializando ETW (%s). Uso fallback psutil.", exc)
    elif prefer_etw:
        log.warning("Sin privilegios de Administrador: no se puede usar ETW.")

    return PsutilCaptureService(), False
