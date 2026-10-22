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


# ---- combinación de veredictos de confianza (plan 04) ----------------------
from src.domain.models import (  # noqa: E402
    TRUST_CAUTION, TRUST_SUSPICIOUS, TRUST_TRUSTED, TRUST_UNKNOWN, TrustInfo,
    worst_trust,
)


def test_worst_trust_picks_most_severe():
    real = TrustInfo(level=TRUST_TRUSTED,
                     exe_path="C:/Program Files/Google/Chrome/chrome.exe")
    fake = TrustInfo(level=TRUST_CAUTION, exe_path="C:/Users/x/AppData/chrome.exe")
    assert worst_trust([real, fake]) is fake
    assert worst_trust([fake, real]) is fake


def test_worst_trust_suspicious_beats_everything():
    infos = [TrustInfo(level=TRUST_TRUSTED), TrustInfo(level=TRUST_SUSPICIOUS),
             TrustInfo(level=TRUST_CAUTION), TrustInfo(level=TRUST_UNKNOWN)]
    assert worst_trust(infos).level == TRUST_SUSPICIOUS


def test_worst_trust_unknown_is_worse_than_trusted():
    # "no sé" nunca debe pasar por bueno
    infos = [TrustInfo(level=TRUST_TRUSTED), TrustInfo(level=TRUST_UNKNOWN)]
    assert worst_trust(infos).level == TRUST_UNKNOWN


def test_worst_trust_empty_is_unknown():
    assert worst_trust([]).level == TRUST_UNKNOWN


def test_worst_trust_tie_keeps_first():
    a = TrustInfo(level=TRUST_CAUTION, exe_path="a")
    b = TrustInfo(level=TRUST_CAUTION, exe_path="b")
    assert worst_trust([a, b]) is a
