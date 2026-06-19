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


# ---- suavizado de la velocidad en vivo (T-012) ------------------------------
def _tick_with(m, sent=0, recv=0):
    """Simula una ventana de 1s de nettop: acumula bytes y dispara _rate_tick
    directamente, sin pasar por threading.Timer (make_monitor no llama start())."""
    m._rate_sent += sent
    m._rate_recv += recv
    m._rate_tick()


def test_live_rate_smooths_0_2x_aliasing():
    """Caso del ticket: nettop entrega ~1 bloque/s pero fuera de fase con
    _rate_tick -> ventanas alternadas [0, 2x, 0, 2x] de bytes crudos. La
    tasa MOSTRADA (live_rate) debe quedar ~estable en torno a x, sin caer
    a 0 ni picar a 2x."""
    from src.domain.models import Settings
    settings = Settings()
    from conftest import FakeNotifier
    notifier = FakeNotifier()
    m = make_monitor(settings, notifier)

    x = 1_000_000  # 1 MB/s sostenido "real"
    raw_windows = [0, 2 * x, 0, 2 * x, 0, 2 * x]
    shown = []
    for raw in raw_windows:
        _tick_with(m, sent=raw, recv=0)
        up, _down = m.live_rate()
        shown.append(up)

    # Las primeras lecturas (ventana de promedio aún llenándose) pueden
    # variar más, pero una vez con historial completo (>= RATE_WINDOW
    # lecturas) la tasa mostrada no debe volver a tocar los extremos 0 o 2x.
    stable = shown[m._RATE_WINDOW - 1:]
    for v in stable:
        assert v != 0
        assert v != 2 * x
        # debe quedar razonablemente cerca del throughput sostenido real
        assert 0.5 * x <= v <= 1.5 * x


def test_live_rate_smoothing_does_not_affect_totals(settings, notifier):
    """El suavizado solo debe tocar _live_up/_live_down. Los totales por
    app (_session/_pending) deben reflejar exactamente los bytes recibidos
    en _on_sample, sin pasar por el promedio móvil."""
    from src.domain.models import TrafficSample
    m = make_monitor(settings, notifier)
    m._on_sample(TrafficSample(1, "App", bytes_sent=0, bytes_recv=2_000_000))
    _tick_with(m, sent=0, recv=2_000_000)
    m._on_sample(TrafficSample(1, "App", bytes_sent=0, bytes_recv=0))
    _tick_with(m, sent=0, recv=0)

    total_recv = m._session["App"].bytes_recv
    assert total_recv == 2_000_000  # exacto, no promediado

    _, down = m.live_rate()
    assert down != 0  # el promedio móvil sigue mostrando algo > 0 (suavizado)


def test_live_rate_responds_to_sustained_change():
    """Responsividad razonable: tras varias ventanas con un nuevo nivel
    sostenido, la tasa mostrada converge a ese nivel (no se queda pegada
    al pasado indefinidamente)."""
    from src.domain.models import Settings
    from conftest import FakeNotifier
    settings = Settings()
    notifier = FakeNotifier()
    m = make_monitor(settings, notifier)

    for _ in range(5):
        _tick_with(m, sent=1_000_000, recv=0)
    for _ in range(m._RATE_WINDOW):
        _tick_with(m, sent=5_000_000, recv=0)

    up, _ = m.live_rate()
    assert up == 5_000_000  # tras RATE_WINDOW ticks al nuevo nivel, converge


def test_check_spike_receives_smoothed_rate(settings, notifier):
    """_check_spike debe recibir la tasa YA suavizada (no el bloque crudo
    de 1s), para no disparar falsos positivos por el aliasing 0/2x."""
    settings.anomaly_alerts_enabled = True
    m = make_monitor(settings, notifier)
    # Prime con ticks crudos alternando 0 / 2*baseline -> tras el suavizado
    # esto NO debería verse como una serie de picos en _rate_history.
    baseline = 100_000
    for _ in range(12):
        _tick_with(m, sent=0, recv=0)
        _tick_with(m, sent=2 * baseline, recv=0)
    # historial de _rate_history está poblado con valores suavizados,
    # ninguno debería ser ni 0 ni 2*baseline crudo si el suavizado entró
    # antes de _check_spike.
    assert all(v != 0 for v in list(m._rate_history)[-5:])
    assert notifier.messages == []  # sin falsos positivos por el aliasing


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
