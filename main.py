"""Composition Root: arma las dependencias y arranca la app de bandeja.

Aquí (y SOLO aquí) se conoce el detalle concreto de cada capa.
El resto del código depende de las abstracciones de domain/ports.py.
"""
from __future__ import annotations

import atexit
import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import signal
import sys
from pathlib import Path

# Permite ejecutar tanto `python main.py` como el .exe empaquetado.
sys.path.insert(0, str(Path(__file__).parent))

from src.application.monitor_service import MonitorService
from src.domain.ports import UsageRepository
from src.infrastructure.capture.connections import PsutilConnectionProvider
from src.infrastructure.capture.factory import create_capture_service
from src.infrastructure.capture.geoip_ipapi import IpApiGeoIp
from src.infrastructure.capture.reputation_virustotal import VirusTotalReputation
from src.infrastructure.capture.trust import WindowsTrustEvaluator
from src.infrastructure.persistence.settings_store import JsonSettingsStore
from src.infrastructure.persistence.sqlite_repository import SqliteUsageRepository
from src.infrastructure.reporting.report_generator import CsvReportGenerator
from src.infrastructure.reporting.rotation import rotate_reports
from src.infrastructure.reporting.pdf_report_generator import PdfReportGenerator
from src.infrastructure.reporting.xlsx_report_generator import XlsxReportGenerator
from src.presentation.qt.app import QtNotifier, run


_APP_NAME = "NetGauge"
_LEGACY_APP_NAME = "trafficMe"  # nombre previo al rename (T-016); migrar su historial.

# Qué llevar de la carpeta vieja a la nueva al actualizar desde trafficMe.
_MIGRATE_FILES = ("usage.db", "settings.json", "monitor.log")
_MIGRATE_DIRS = ("reports",)

# Log de la app (spec release-audit): rotativo para no crecer sin límite.
_LOG_FILE = "netgauge.log"
_LOG_MAX_BYTES = 1_000_000
_LOG_BACKUPS = 3


def _base_for(app_name: str) -> Path:
    """Ruta del directorio de datos por plataforma para `app_name` (sin crearlo).

    Windows: %LOCALAPPDATA%\\<app> (fallback a ~/AppData/Local). macOS:
    ~/Library/Application Support/<app>. Resto (Linux/CI): ~/.<app>.
    """
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return Path(local) / app_name if local else \
            Path.home() / "AppData" / "Local" / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    return Path.home() / f".{app_name}"


def _migrate_legacy_data(new_base: Path, legacy_base: Path) -> bool:
    """Copia el historial de la instalación previa (trafficMe) a la nueva (NetGauge).

    Idempotente y conservador: solo migra si la instalación nueva está "limpia"
    (sin `usage.db`) y la vieja tiene datos. Copia (no mueve): la carpeta vieja
    queda intacta como respaldo. Devuelve True si migró algo.
    """
    if new_base == legacy_base:
        return False
    if (new_base / "usage.db").exists():  # ya hay datos nuevos: no tocar
        return False
    if not (legacy_base / "usage.db").exists():  # nada que migrar
        return False
    new_base.mkdir(parents=True, exist_ok=True)
    for name in _MIGRATE_FILES:
        src = legacy_base / name
        if src.is_file() and not (new_base / name).exists():
            shutil.copy2(src, new_base / name)
    for name in _MIGRATE_DIRS:
        src = legacy_base / name
        if src.is_dir() and not (new_base / name).exists():
            shutil.copytree(src, new_base / name)
    return True


def _data_dir() -> Path:
    """Directorio de datos de NetGauge por plataforma (logs, DB, settings, reportes)."""
    base = _base_for(_APP_NAME)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _setup_logging(data_dir: Path) -> logging.Handler:
    """Instala el log rotativo `data_dir/netgauge.log` en el root logger.

    Idempotente: si ya está instalado devuelve el mismo handler. No usa
    basicConfig porque es no-op si el root ya tiene handlers.
    """
    path = os.path.abspath(data_dir / _LOG_FILE)
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, RotatingFileHandler) and h.baseFilename == path:
            return h
    handler = RotatingFileHandler(
        path, maxBytes=_LOG_MAX_BYTES, backupCount=_LOG_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler


def _shutdown(monitor: MonitorService, repository: UsageRepository) -> None:
    """Cierre ordenado: informe de sesión, stop del monitor y cierre de la DB.

    El repositorio se cierra SIEMPRE, aunque stop() falle (antes, una
    excepción en stop() dejaba la DB abierta).
    """
    try:
        try:
            monitor.generate_session_report()
        except Exception:  # noqa: BLE001
            logging.exception("Fallo generando informe de cierre")
        monitor.stop()
    except Exception:  # noqa: BLE001
        logging.exception("Fallo deteniendo el monitor")
    finally:
        repository.close()


def main() -> None:
    data_dir = _data_dir()

    # Migración única desde la instalación previa "trafficMe" (rename T-016): si el
    # usuario actualiza, traemos su historial para que no "desaparezca". Antes de
    # configurar logging para que el monitor.log de trafficMe también se preserve.
    migrated = False
    try:
        migrated = _migrate_legacy_data(data_dir, _base_for(_LEGACY_APP_NAME))
    except Exception:  # noqa: BLE001 — la migración nunca debe impedir el arranque
        pass

    _setup_logging(data_dir)
    if migrated:
        logging.info("Historial migrado desde la instalación previa (trafficMe).")

    capture, per_process = create_capture_service(prefer_etw=True)
    repository = SqliteUsageRepository(_data_dir() / "usage.db")
    reporter = CsvReportGenerator(_data_dir() / "reports")
    # Informes de sesiones anteriores: conservar solo los últimos 20 (el de esta
    # sesión se genera al cerrar, así que quedan <= 21 tras el cierre).
    try:
        rotate_reports(_data_dir() / "reports", keep=20)
    except Exception:  # noqa: BLE001 — la limpieza nunca debe impedir el arranque
        logging.exception("Fallo rotando informes viejos")
    settings_store = JsonSettingsStore(_data_dir() / "settings.json")

    # Notifier Qt: thread-safe vía señal; se enlaza al tray dentro de run().
    notifier = QtNotifier()

    # Índice de confianza local (firma/ubicación), conexiones activas por app
    # y reputación VirusTotal opt-in (apagada salvo que el usuario la active).
    trust_evaluator = WindowsTrustEvaluator()
    connection_provider = PsutilConnectionProvider()
    reputation = VirusTotalReputation()
    geoip = IpApiGeoIp()

    monitor = MonitorService(
        capture, repository, reporter, settings_store, notifier,
        flush_interval=10.0,
        trust_evaluator=trust_evaluator,
        connection_provider=connection_provider,
        reputation=reputation,
        geoip=geoip,
    )
    # Formatos de export adicionales (CSV ya viene por defecto).
    monitor.register_reporter("xlsx", XlsxReportGenerator(_data_dir() / "reports"))
    monitor.register_reporter("pdf", PdfReportGenerator(_data_dir() / "reports"))

    # Red de seguridad: informe + flush ante cierre del sistema o crash controlado.
    def _on_exit() -> None:
        _shutdown(monitor, repository)

    atexit.register(_on_exit)

    # Cierre robusto ante SIGTERM/SIGINT (T-023): solo macOS. En Windows la
    # semántica de estas señales es distinta (no hay un SIGTERM "de verdad" -
    # Python las simula parcialmente, y closeEvent/atexit ya cubren el cierre
    # normal de la ventana), así que el handler NO se instala ahí para no
    # alterar el comportamiento existente. `SIGKILL` sigue sin ser atrapable
    # en ningún caso; la red de seguridad final es el reap al arrancar
    # (NettopCaptureService.reap_orphans, en el path nettop de macOS).
    if sys.platform == "darwin":
        def _on_signal(signum: int, _frame) -> None:
            logging.info("Señal %s recibida: cerrando de forma ordenada.", signum)
            atexit.unregister(_on_exit)  # evita correr el cleanup dos veces
            _on_exit()
            sys.exit(0)

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)

    run(monitor, per_process, notifier)


if __name__ == "__main__":
    main()
