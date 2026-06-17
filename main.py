"""Composition Root: arma las dependencias y arranca la app de bandeja.

Aquí (y SOLO aquí) se conoce el detalle concreto de cada capa.
El resto del código depende de las abstracciones de domain/ports.py.
"""
from __future__ import annotations

import atexit
import logging
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
from src.presentation.qt.app import QtNotifier, run


def _data_dir() -> Path:
    base = Path.home() / "AppData" / "Local" / "NetworkMonitor"
    base.mkdir(parents=True, exist_ok=True)
    return base


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=str(_data_dir() / "monitor.log"),
    )

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
