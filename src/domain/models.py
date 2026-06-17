"""Entidades del dominio. Puro Python, sin dependencias de infraestructura."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrafficSample:
    """Una muestra de tráfico atribuida a un proceso en un instante dado."""

    pid: int
    app_name: str
    bytes_sent: int
    bytes_recv: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AppUsage:
    """Consumo agregado de una aplicación."""

    app_name: str
    bytes_sent: int = 0
    bytes_recv: int = 0

    @property
    def total(self) -> int:
        return self.bytes_sent + self.bytes_recv

    def add(self, sent: int, recv: int) -> None:
        self.bytes_sent += sent
        self.bytes_recv += recv


@dataclass
class UsageRecord:
    """Fila histórica persistida (una por app por intervalo de flush)."""

    app_name: str
    bytes_sent: int
    bytes_recv: int
    recorded_at: datetime


@dataclass
class Settings:
    """Preferencias del usuario, persistidas en JSON."""

    monthly_quota_gb: float = 0.0          # 0 = sin límite
    daily_quota_gb: float = 0.0            # 0 = sin límite diario
    billing_cycle_start_day: int = 1       # día del mes en que reinicia el ciclo
    alert_thresholds: tuple[int, ...] = (80, 100)  # % de cuota que disparan aviso
    preferred_unit: str = "Auto"           # Auto | KB | MB | GB
    language: str = "es"                   # es | en | pt
    retention_days: int = 180              # purga histórico más viejo (0 = nunca)
    trust_check_enabled: bool = True       # índice de confianza local (firma/ruta)
    virustotal_enabled: bool = False       # reputación VirusTotal (manda hash)
    virustotal_api_key: str = ""           # API key del usuario
    geoip_enabled: bool = False            # país/proveedor de IPs remotas (ip-api)
    anomaly_alerts_enabled: bool = True    # avisos de picos y apps nuevas en red

    def to_dict(self) -> dict:
        return {
            "monthly_quota_gb": self.monthly_quota_gb,
            "daily_quota_gb": self.daily_quota_gb,
            "billing_cycle_start_day": self.billing_cycle_start_day,
            "alert_thresholds": list(self.alert_thresholds),
            "preferred_unit": self.preferred_unit,
            "language": self.language,
            "retention_days": self.retention_days,
            "trust_check_enabled": self.trust_check_enabled,
            "virustotal_enabled": self.virustotal_enabled,
            "virustotal_api_key": self.virustotal_api_key,
            "geoip_enabled": self.geoip_enabled,
            "anomaly_alerts_enabled": self.anomaly_alerts_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        return cls(
            monthly_quota_gb=float(data.get("monthly_quota_gb", 0.0)),
            daily_quota_gb=float(data.get("daily_quota_gb", 0.0)),
            billing_cycle_start_day=int(data.get("billing_cycle_start_day", 1)),
            alert_thresholds=tuple(data.get("alert_thresholds", [80, 100])),
            preferred_unit=str(data.get("preferred_unit", "Auto")),
            language=str(data.get("language", "es")),
            retention_days=int(data.get("retention_days", 180)),
            trust_check_enabled=bool(data.get("trust_check_enabled", True)),
            virustotal_enabled=bool(data.get("virustotal_enabled", False)),
            virustotal_api_key=str(data.get("virustotal_api_key", "")),
            geoip_enabled=bool(data.get("geoip_enabled", False)),
            anomaly_alerts_enabled=bool(data.get("anomaly_alerts_enabled", True)),
        )


@dataclass
class QuotaStatus:
    """Estado de la cuota mensual."""

    used_bytes: int
    limit_bytes: int        # 0 = sin límite
    cycle_start: datetime

    @property
    def percent(self) -> float:
        if self.limit_bytes <= 0:
            return 0.0
        return min(999.0, self.used_bytes / self.limit_bytes * 100.0)

    @property
    def has_limit(self) -> bool:
        return self.limit_bytes > 0


# Niveles del índice de confianza (NO es un "% de peligrosidad" inventado:
# es un veredicto a partir de señales reales y verificables).
TRUST_TRUSTED = "trusted"      # firmado y válido, en ruta de sistema
TRUST_UNKNOWN = "unknown"      # sin datos suficientes / no evaluado
TRUST_CAUTION = "caution"      # alguna señal floja (sin firma, ruta atípica)
TRUST_SUSPICIOUS = "suspicious"  # varias señales de riesgo


@dataclass
class TrustInfo:
    """Veredicto de confianza de un ejecutable, con el desglose de señales.

    `reasons` son claves i18n (ej. 'trust.signed_by', 'trust.unsigned') que la
    capa de presentación traduce. Nunca se muestra un número mágico.
    """

    level: str = TRUST_UNKNOWN
    signed: bool = False
    signature_valid: bool = False
    signer: str | None = None
    location_ok: bool = False
    has_metadata: bool = False
    exe_path: str | None = None
    reasons: tuple[str, ...] = ()
    vt_malicious: int | None = None   # motores de VirusTotal que lo marcan
    vt_total: int | None = None       # total de motores que analizaron


@dataclass
class Connection:
    """Una conexión de red activa atribuida a un proceso."""

    app_name: str
    pid: int
    raddr: str          # IP remota
    rport: int
    status: str         # ESTABLISHED, LISTEN, etc.


def human_bytes(num: float) -> str:
    """Formatea bytes a una unidad legible (KB, MB, GB...)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"
