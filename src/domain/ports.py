"""Puertos (interfaces abstractas). La aplicación depende de estas, no de implementaciones."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Iterable

from .models import Connection, Settings, TrafficSample, TrustInfo, UsageRecord


class CaptureService(ABC):
    """Captura tráfico de red atribuido por proceso."""

    @abstractmethod
    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        """Arranca la captura. Por cada muestra invoca on_sample(sample)."""

    @abstractmethod
    def stop(self) -> None:
        """Detiene la captura y libera recursos (sesión ETW, threads, etc.)."""


class UsageRepository(ABC):
    """Persistencia del consumo histórico."""

    @abstractmethod
    def save_batch(self, records: Iterable[UsageRecord]) -> None: ...

    @abstractmethod
    def usage_between(self, start: datetime, end: datetime) -> list[UsageRecord]: ...

    @abstractmethod
    def totals_by_app(self, start: datetime, end: datetime) -> list[UsageRecord]:
        """Consumo agregado por app dentro del rango."""

    @abstractmethod
    def purge_older_than(self, cutoff: datetime) -> int:
        """Borra registros anteriores a `cutoff`. Devuelve cuántos borró."""

    @abstractmethod
    def close(self) -> None: ...


class ReportGenerator(ABC):
    """Genera informes de sesión a disco."""

    @abstractmethod
    def generate(self, records: Iterable[UsageRecord], destination_hint: str | None = None) -> str:
        """Escribe el informe y devuelve la ruta del archivo creado."""


class Notifier(ABC):
    """Notifica al usuario (toast del sistema, balloon del tray, etc.)."""

    @abstractmethod
    def notify(self, title: str, message: str) -> None: ...


class TrustEvaluator(ABC):
    """Evalúa la confianza de un ejecutable con señales locales reales."""

    @abstractmethod
    def evaluate(self, exe_path: str) -> TrustInfo: ...


class ConnectionProvider(ABC):
    """Enumera conexiones de red activas atribuidas por proceso."""

    @abstractmethod
    def connections(self) -> list[Connection]: ...

    @abstractmethod
    def exe_paths(self) -> dict[str, str]:
        """Mapa app_name -> ruta del ejecutable (para el índice de confianza)."""


class ReputationService(ABC):
    """Reputación externa de un ejecutable (ej. VirusTotal por hash).

    NO bloqueante: lookup() devuelve el resultado cacheado o None si todavía
    no está listo (la consulta de red corre en segundo plano).
    """

    @abstractmethod
    def set_api_key(self, key: str) -> None: ...

    @abstractmethod
    def lookup(self, exe_path: str) -> tuple[int, int] | None:
        """(maliciosos, total_motores) si hay dato; None si no/aún no."""


class GeoIpService(ABC):
    """Resuelve país y proveedor (ASN/org) de una IP remota. No bloqueante."""

    @abstractmethod
    def lookup(self, ip: str) -> tuple[str, str] | None:
        """(country_code, org) si hay dato; None si no/aún no/IP privada."""


class SettingsStore(ABC):
    """Lee/escribe la configuración persistente del usuario."""

    @abstractmethod
    def load(self) -> "Settings": ...

    @abstractmethod
    def save(self, settings: "Settings") -> None: ...
