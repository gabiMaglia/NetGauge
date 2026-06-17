"""Tests del dominio puro: formateo, Settings, QuotaStatus, AppUsage."""
from src.domain.models import AppUsage, QuotaStatus, Settings, human_bytes
from datetime import datetime


def test_human_bytes_scales():
    assert human_bytes(0).endswith("B")
    assert "KB" in human_bytes(2048)
    assert "MB" in human_bytes(5 * 1024**2)
    assert "GB" in human_bytes(3 * 1024**3)


def test_app_usage_add_and_total():
    u = AppUsage("X")
    u.add(10, 20)
    u.add(5, 5)
    assert u.bytes_sent == 15 and u.bytes_recv == 25
    assert u.total == 40


def test_quota_status_percent_and_limit():
    s = QuotaStatus(used_bytes=50, limit_bytes=100, cycle_start=datetime.now())
    assert s.has_limit is True
    assert s.percent == 50.0
    sin = QuotaStatus(used_bytes=50, limit_bytes=0, cycle_start=datetime.now())
    assert sin.has_limit is False
    assert sin.percent == 0.0


def test_quota_percent_caps_at_999():
    s = QuotaStatus(used_bytes=10**12, limit_bytes=1, cycle_start=datetime.now())
    assert s.percent == 999.0


def test_settings_roundtrip_preserves_all_fields():
    s = Settings(monthly_quota_gb=50.5, daily_quota_gb=2.0,
                 billing_cycle_start_day=15, preferred_unit="MB",
                 language="pt", retention_days=90, trust_check_enabled=False,
                 virustotal_enabled=True, virustotal_api_key="abc",
                 geoip_enabled=True, anomaly_alerts_enabled=False)
    back = Settings.from_dict(s.to_dict())
    assert back == s


def test_settings_from_dict_uses_defaults_for_missing_keys():
    s = Settings.from_dict({})  # JSON viejo sin campos nuevos
    assert s.language == "es"
    assert s.retention_days == 180
    assert s.trust_check_enabled is True
    assert s.virustotal_enabled is False
    assert s.geoip_enabled is False
    assert s.anomaly_alerts_enabled is True
