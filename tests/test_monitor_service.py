"""Tests de la lógica de aplicación: cuotas, anomalías, retención, VT."""
from datetime import datetime, timedelta

from conftest import FakeRepo, make_monitor
from src.domain.models import (
    TRUST_SUSPICIOUS, TRUST_TRUSTED, TRUST_UNKNOWN, TrustInfo, UsageRecord,
)


# ---- ciclo de facturación -------------------------------------------------
def test_cycle_start_matches_day_and_not_future(settings, notifier):
    settings.billing_cycle_start_day = 15
    m = make_monitor(settings, notifier)
    start = m._cycle_start()
    assert start.day == 15
    assert start <= datetime.now()


# ---- cuotas ----------------------------------------------------------------
def test_quota_status_sums_repo_usage(settings, notifier):
    settings.monthly_quota_gb = 1.0
    repo = FakeRepo([UsageRecord("A", 100, 200, datetime.now()),
                     UsageRecord("B", 300, 400, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    st = m.quota_status()
    assert st.used_bytes == 1000
    assert st.has_limit is True


def test_quota_alert_fires_once_per_threshold(settings, notifier):
    settings.monthly_quota_gb = 0.0  # mensual sin límite
    settings.daily_quota_gb = 1.0 / (1024**3) * 1000  # límite diario ~1000 bytes
    repo = FakeRepo([UsageRecord("A", 500, 500, datetime.now())])  # 1000 bytes = 100%
    m = make_monitor(settings, notifier, repo)
    m._check_quota_alerts()
    fired_after_first = len(notifier.messages)
    m._check_quota_alerts()  # segunda vez no debe duplicar
    # 100% dispara los umbrales 80 y 100, una sola vez cada uno
    assert fired_after_first == 2
    assert len(notifier.messages) == 2  # la 2ª pasada no agrega nada


# ---- detección de picos ----------------------------------------------------
def _prime(m, value=100_000, n=12):
    for _ in range(n):
        m._check_spike(value)


def test_spike_fires_on_big_jump(settings, notifier):
    m = make_monitor(settings, notifier)
    _prime(m)
    m._check_spike(50_000_000)
    assert any(t == "alert.spike.title" for t, _ in notifier.messages)


def test_spike_respects_cooldown(settings, notifier):
    m = make_monitor(settings, notifier)
    _prime(m)
    m._check_spike(50_000_000)
    m._check_spike(60_000_000)  # dentro del cooldown
    assert sum(t == "alert.spike.title" for t, _ in notifier.messages) == 1


def test_spike_suppressed_when_disabled(settings, notifier):
    settings.anomaly_alerts_enabled = False
    m = make_monitor(settings, notifier)
    _prime(m)
    m._check_spike(50_000_000)
    assert notifier.messages == []


# ---- nuevas apps en la red -------------------------------------------------
def test_new_app_alert_after_baseline(settings, notifier):
    from src.domain.models import AppUsage
    m = make_monitor(settings, notifier)
    m._session = {"Chrome": AppUsage("Chrome", 10, 10)}
    m._check_new_apps()  # baseline: no alerta
    assert notifier.messages == []
    m._session["Sospechosa"] = AppUsage("Sospechosa", 10 * 1024 * 1024, 0)
    m._check_new_apps()
    assert any(t == "alert.newapp.title" for t, _ in notifier.messages)


def test_new_app_below_threshold_no_alert(settings, notifier):
    from src.domain.models import AppUsage
    m = make_monitor(settings, notifier)
    m._session = {"Chrome": AppUsage("Chrome", 10, 10)}
    m._check_new_apps()
    m._session["Chica"] = AppUsage("Chica", 1000, 0)  # < 5 MB
    m._check_new_apps()
    assert notifier.messages == []


# ---- retención -------------------------------------------------------------
def test_purge_runs_when_due(settings, notifier):
    settings.retention_days = 30
    repo = FakeRepo()
    m = make_monitor(settings, notifier, repo)
    m._purge_if_due()
    assert repo.purged_before is not None
    assert repo.purged_before < datetime.now()


def test_purge_skipped_when_disabled(settings, notifier):
    settings.retention_days = 0
    repo = FakeRepo()
    m = make_monitor(settings, notifier, repo)
    m._purge_if_due()
    assert repo.purged_before is None


# ---- enriquecimiento VirusTotal -------------------------------------------
class FakeReputation:
    def __init__(self, result): self._r = result
    def set_api_key(self, k): pass
    def lookup(self, path): return self._r


def test_vt_escalates_level_on_detection(settings, notifier):
    settings.virustotal_enabled = True
    settings.virustotal_api_key = "k"
    m = make_monitor(settings, notifier)
    m._reputation = FakeReputation((6, 72))
    info = TrustInfo(level=TRUST_TRUSTED)
    out = m._enrich_with_vt(info, "C:/x.exe")
    assert out.level == TRUST_SUSPICIOUS
    assert out.vt_malicious == 6 and out.vt_total == 72
    assert "trust.vt_detected" in out.reasons


def test_vt_clean_keeps_level(settings, notifier):
    settings.virustotal_enabled = True
    settings.virustotal_api_key = "k"
    m = make_monitor(settings, notifier)
    m._reputation = FakeReputation((0, 72))
    info = TrustInfo(level=TRUST_TRUSTED)
    out = m._enrich_with_vt(info, "C:/x.exe")
    assert out.level == TRUST_TRUSTED
    assert "trust.vt_clean" in out.reasons


def test_vt_disabled_returns_untouched(settings, notifier):
    settings.virustotal_enabled = False
    m = make_monitor(settings, notifier)
    m._reputation = FakeReputation((9, 72))
    info = TrustInfo(level=TRUST_TRUSTED)
    assert m._enrich_with_vt(info, "C:/x.exe") is info


def test_trust_for_unknown_without_evaluator(settings, notifier):
    m = make_monitor(settings, notifier)  # sin trust_evaluator
    assert m.trust_for("Cualquiera").level == TRUST_UNKNOWN
