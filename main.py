"""Composition Root: arma las dependencias y arranca la app de bandeja.

Aquí (y SOLO aquí) se conoce el detalle concreto de cada capa.
El resto del código depende de las abstracciones de domain/ports.py.
"""
from __future__ import annotations

import atexit
import logging
import os
import shutil
import sys
from pathlib import Path

# Permite ejecutar tanto `python main.py` como el .exe empaquetado.
sys.path.insert(0, str(Path(__file__).parent))

from src.application.monitor_service import MonitorService
from src.infrastructure.capture.connections import PsutilConnectionProvider
from src.infrastructure.capture.factory import create_capture_service
from src.infrastructure.capture.geoip_ipapi import IpApiGeoIp
from src.infrastructure.capture.reputation_virustotal import VirusTotalReputation
from src.infrastructure.capture.trust import WindowsTrustEvaluator
from src.infrastructure.persistence.settings_store import JsonSettingsStore
from src.infrastructure.persistence.sqlite_repository import SqliteUsageRepository
from src.infrastructure.reporting.report_generator import CsvReportGenerator
from src.infrastructure.reporting.pdf_report_generator import PdfReportGenerator
from src.infrastructure.reporting.xlsx_report_generator import XlsxReportGenerator
from src.presentation.qt.app import QtNotifier, run


_APP_NAME = "NetGauge"
_LEGACY_APP_NAME = "trafficMe"  # nombre previo al rename (T-016); migrar su historial.

# Qué llevar de la carpeta vieja a la nueva al actualizar desde trafficMe.
_MIGRATE_FILES = ("usage.db", "settings.json", "monitor.log")
_MIGRATE_DIRS = ("reports",)


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


def main() -> None:
    data_dir = _data_dir()

    # Migración única desde la instalación previa "trafficMe" (rename T-016): si el
    # usuario actualiza, traemos su historial para que no "desaparezca". Antes de
    # configurar logging para que el monitor.log viejo también se preserve.
    migrated = False
    try:
        migrated = _migrate_legacy_data(data_dir, _base_for(_LEGACY_APP_NAME))
    except Exception:  # noqa: BLE001 — la migración nunca debe impedir el arranque
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=str(data_dir / "monitor.log"),
    )
    if migrated:
        logging.info("Historial migrado desde la instalación previa (trafficMe).")

    capture, per_process = create_capture_service(prefer_etw=True)
    repository = SqliteUsageRepository(_data_dir() / "usage.db")
    reporter = CsvReportGenerator(_data_dir() / "reports")
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
        try:
            monitor.generate_session_report()
        except Exception:  # noqa: BLE001
            logging.exception("Fallo generando informe de cierre")
        monitor.stop()
        repository.close()

    atexit.register(_on_exit)

    run(monitor, per_process, notifier)


if __name__ == "__main__":
    main()
