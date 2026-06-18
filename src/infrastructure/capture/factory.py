"""Fábrica de captura: por plataforma intenta el backend por-proceso nativo
(ETW en Windows, nettop en macOS) y cae a psutil (global) si no está disponible.
"""
from __future__ import annotations

import logging
import sys

from ...domain.ports import CaptureService
from .psutil_fallback import PsutilCaptureService

log = logging.getLogger(__name__)


def _is_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _create_windows(prefer_etw: bool) -> tuple[CaptureService, bool]:
    from .etw_capture import CaptureUnavailable, EtwCaptureService

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


def _create_macos(prefer_native: bool) -> tuple[CaptureService, bool]:
    from .nettop_capture import CaptureUnavailable, NettopCaptureService

    if prefer_native:
        try:
            if not NettopCaptureService.is_available():
                raise CaptureUnavailable("`nettop` no está disponible.")
            log.info("Captura nettop por proceso activada (best-effort).")
            return NettopCaptureService(), True
        except CaptureUnavailable as exc:
            log.warning("nettop no disponible (%s). Uso fallback psutil.", exc)
        except Exception as exc:  # noqa: BLE001
            log.warning("Fallo inicializando nettop (%s). Uso fallback psutil.", exc)

    return PsutilCaptureService(), False


def create_capture_service(prefer_etw: bool = True) -> tuple[CaptureService, bool]:
    """Devuelve (servicio, es_por_proceso).

    es_por_proceso=True => backend nativo por-proceso activo (ETW en Windows,
    nettop en macOS): desglose real por app.
    es_por_proceso=False => fallback global con psutil.
    """
    if sys.platform == "darwin":
        return _create_macos(prefer_etw)
    if sys.platform == "win32":
        return _create_windows(prefer_etw)

    log.warning("Plataforma %s sin backend nativo: uso fallback psutil.", sys.platform)
    return PsutilCaptureService(), False
