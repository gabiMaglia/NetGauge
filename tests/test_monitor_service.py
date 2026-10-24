"""Tests de la lógica de aplicación: cuotas, anomalías, retención, VT."""
import sqlite3
import threading
from datetime import datetime, timedelta

import pytest

from conftest import FakeNotifier, FakeRepo, make_monitor
from src.domain.models import (
    TRUST_SUSPICIOUS, TRUST_TRUSTED, TRUST_UNKNOWN, TrafficSample, TrustInfo,
    UsageRecord,
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
    m.refresh_snapshot()   # plan 04: quota_status() lee el snapshot
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
    directamente, sin pasar por threading.Timer (make_monitor no llama start()).
    Usa un reloj falso que avanza 1 s por llamada (la tasa se calcula con tiempos)."""
    t = getattr(m, "_fake_t", 1000.0) + 1.0
    m._fake_t = t
    m._clock = lambda: t
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
    stable = shown[3:]
    for v in stable:
        assert v != 0
        assert v != 2 * x
        # debe quedar razonablemente cerca del throughput sostenido real
        assert 0.85 * x <= v <= 1.15 * x   # con marcas de tiempo es casi exacta


def test_internal_helper_excluded_from_apps(settings, notifier):
    """T-024: el helper de captura (nettop) no debe figurar como una app del
    usuario ni sumar su tráfico a totales/tasa; una app real sí."""
    from src.domain.models import TrafficSample
    m = make_monitor(settings, notifier)
    m._on_sample(TrafficSample(1, "nettop", bytes_sent=1000, bytes_recv=2000))
    m._on_sample(TrafficSample(2, "Chrome", bytes_sent=10, bytes_recv=20))
    assert "nettop" not in m._session and "nettop" not in m._pending
    assert "Chrome" in m._session
    assert m._rate_sent == 10 and m._rate_recv == 20  # nettop no sumó a la tasa


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
    assert down != 0  # el suavizado sigue mostrando algo > 0 un tick después


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
    for _ in range(3):
        _tick_with(m, sent=5_000_000, recv=0)

    up, _ = m.live_rate()
    assert up == 5_000_000  # a los ~3 s del nuevo nivel, converge


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



class _SpyRepo(FakeRepo):
    def __init__(self) -> None:
        super().__init__()
        self.starts: list[datetime] = []

    def totals_by_app(self, start, end):
        self.starts.append(start)
        return []


def test_week_period_starts_exactly_at_monday_midnight(settings, notifier):
    repo = _SpyRepo()
    m = make_monitor(settings, notifier, repo)

    m.usage_for_period("week")
    m.refresh_snapshot()   # plan 04: la consulta ocurre en el worker

    start = repo.starts[-1]
    assert start.weekday() == 0
    assert (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)


# ---- resiliencia de persistencia (plan 03) --------------------------------
class FlakyRepo(FakeRepo):
    """save_batch falla `failures` veces (p.ej. 'database is locked') y después anda."""

    def __init__(self, failures: int = 1) -> None:
        super().__init__()
        self.failures = failures

    def save_batch(self, records):
        if self.failures > 0:
            self.failures -= 1
            raise sqlite3.OperationalError("database is locked")
        super().save_batch(records)


def _totals(records) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for r in records:
        sent, recv = out.get(r.app_name, (0, 0))
        out[r.app_name] = (sent + r.bytes_sent, recv + r.bytes_recv)
    return out


def test_flush_failure_keeps_batch_for_retry(settings, notifier):
    repo = FlakyRepo(failures=1)
    m = make_monitor(settings, notifier, repo)
    m._on_sample(TrafficSample(1, "A", bytes_sent=100, bytes_recv=200))
    with pytest.raises(sqlite3.OperationalError):
        m._flush()
    # Llegan más bytes mientras la DB estaba caída: se suman al batch pendiente.
    m._on_sample(TrafficSample(1, "A", bytes_sent=1, bytes_recv=2))
    m._flush()
    assert _totals(repo.saved) == {"A": (101, 202)}


@pytest.fixture
def running_monitor(settings, notifier):
    """MonitorService marcado como corriendo, sin start() (sin captura ni
    timers iniciales). Los timers que reprogramen los ticks se cancelan en
    stop(); intervalo de flush enorme para que ninguno dispare durante el test."""
    made = []

    def _make(repo=None, notifier_=None):
        m = make_monitor(settings, notifier_ or notifier, repo)
        m._flush_interval = 3600.0
        m._running = True
        made.append(m)
        return m

    yield _make
    for m in made:
        m.stop()


class BoomNotifier(FakeNotifier):
    def notify(self, title, message):
        raise RuntimeError("toast caído")


def test_tick_survives_save_error_and_retries(running_monitor):
    repo = FlakyRepo(failures=1)
    m = running_monitor(repo)
    m._on_sample(TrafficSample(1, "A", bytes_sent=100, bytes_recv=200))
    m._tick()                             # save_batch revienta: no debe propagar
    assert m._flush_timer is not None     # la cadena de timers sigue viva
    assert repo.saved == []
    m._tick()                             # reintento: persiste lo pendiente
    assert _totals(repo.saved) == {"A": (100, 200)}


def test_tick_notifier_error_does_not_skip_purge(settings, running_monitor):
    settings.monthly_quota_gb = 0.0
    settings.daily_quota_gb = 1.0 / (1024**3) * 1000   # ~1000 bytes -> 100%
    settings.retention_days = 30
    repo = FakeRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = running_monitor(repo, BoomNotifier())
    m._tick()                             # la alerta de cuota revienta en notify
    assert repo.purged_before is not None  # pero la purga igual corrió
    assert m._flush_timer is not None


def test_rate_tick_survives_notifier_error_and_reschedules(running_monitor):
    m = running_monitor(notifier_=BoomNotifier())
    for _ in range(12):
        m._check_spike(100_000)           # historial estable, sin pico
    m._rate_sent = 50_000_000             # pico -> notify revienta
    m._rate_tick()
    assert m._rate_timer is not None      # la velocidad en vivo no se congela


def test_tick_after_stop_does_not_touch_repository(settings, notifier):
    repo = FakeRepo()
    m = make_monitor(settings, notifier, repo)
    m.start()
    m._on_sample(TrafficSample(1, "A", bytes_sent=10, bytes_recv=10))
    m.stop()                               # flush final: 1 registro
    saved_at_stop = len(repo.saved)
    m._on_sample(TrafficSample(1, "A", bytes_sent=5, bytes_recv=5))  # muestra tardía
    m._tick()                              # un Timer que ya había disparado
    assert len(repo.saved) == saved_at_stop
    assert m._flush_timer is None


def test_stop_waits_for_in_progress_tick(settings, notifier):
    entered, release = threading.Event(), threading.Event()

    class SlowRepo(FakeRepo):
        def save_batch(self, records):
            entered.set()
            release.wait(5)
            super().save_batch(records)

    repo = SlowRepo()
    m = make_monitor(settings, notifier, repo)
    m.start()
    m._on_sample(TrafficSample(1, "A", bytes_sent=10, bytes_recv=10))
    ticker = threading.Thread(target=m._tick)
    ticker.start()
    assert entered.wait(5)                 # el tick está adentro de save_batch
    stopper = threading.Thread(target=m.stop)
    stopper.start()
    stopper.join(0.3)
    try:
        assert stopper.is_alive(), "stop() debe esperar al tick en curso"
    finally:
        release.set()
        ticker.join(5)
        stopper.join(5)
    assert not stopper.is_alive()
    assert m._flush_timer is None          # el tick terminó sin reprogramarse
    assert _totals(repo.saved) == {"A": (10, 10)}


# ---- update_settings no re-dispara alertas (re-auditoría A2) ---------------
def _fired_monitor(settings, notifier):
    settings.daily_quota_gb = 1.0 / (1024**3) * 1000
    repo = FakeRepo([UsageRecord("A", 500, 500, datetime.now())])
    m = make_monitor(settings, notifier, repo)
    m._check_quota_alerts()
    assert len(notifier.messages) == 2
    return m


def test_update_settings_unrelated_change_keeps_fired_alerts(settings, notifier):
    import dataclasses
    m = _fired_monitor(settings, notifier)
    m.update_settings(dataclasses.replace(m.settings, window_geometry="1,2,3,4",
                                          preferred_unit="MB"))
    m._check_quota_alerts()
    assert len(notifier.messages) == 2


def test_update_settings_quota_change_rearms_alerts(settings, notifier):
    import dataclasses
    m = _fired_monitor(settings, notifier)
    m.update_settings(dataclasses.replace(
        m.settings, daily_quota_gb=m.settings.daily_quota_gb * 0.9))
    m._check_quota_alerts()
    assert len(notifier.messages) == 4


# ---- purga fallida: se loguea y se reintenta (re-auditoría A9) --------------
class _BoomPurgeRepo(FakeRepo):
    def purge_older_than(self, cutoff):
        raise sqlite3.OperationalError("database is locked")


def test_failed_purge_is_logged_and_not_marked_done(settings, notifier, caplog):
    import logging
    settings.retention_days = 30
    m = make_monitor(settings, notifier, _BoomPurgeRepo())
    with caplog.at_level(logging.ERROR):
        m._purge_if_due()
    assert "locked" in caplog.text
    assert m._last_purge is None   # reintenta en el próximo tick


# ---- listener del snapshot se desengancha (re-auditoría A11) ----------------
def test_snapshot_listener_none_stops_notifying(settings, notifier):
    import threading
    m = make_monitor(settings, notifier)
    called = threading.Event()
    m.set_snapshot_listener(called.set)
    m.set_snapshot_listener(None)
    m._refresher.start()
    try:
        m.refresh_snapshot()
        m._refresher.trigger()
        assert not called.wait(0.3)
    finally:
        m._refresher.stop()


def test_update_settings_geoip_off_cancels_pending(settings, notifier):
    class _Geo:
        cancelled = 0

        def lookup(self, ip): return None
        def cancel_pending(self): self.cancelled += 1

    m = make_monitor(settings, notifier)
    geo = _Geo()
    m._geoip = geo
    settings.geoip_enabled = True
    m.update_settings(settings)
    assert geo.cancelled == 0
    settings.geoip_enabled = False
    m.update_settings(settings)
    assert geo.cancelled == 1



# ---- velocidad en vivo con snapshots cada 2 s (marcas de tiempo) ------------
def _stairs(m, seconds, per_snapshot=1_400_000):
    """Un tick por segundo; nettop entrega bytes sólo cada 2º segundo."""
    shown = []
    for sec in range(seconds):
        _tick_with(m, recv=per_snapshot if sec % 2 == 1 else 0)
        shown.append(m.live_rate()[1])
    return shown


def test_live_rate_is_steady_with_two_second_snapshots(settings, notifier):
    m = make_monitor(settings, notifier)
    shown = _stairs(m, 20)[4:]            # ya calentó
    for v in shown:
        assert 0.9 * 700_000 <= v <= 1.1 * 700_000


def test_live_rate_decays_to_zero_after_traffic_stops(settings, notifier):
    m = make_monitor(settings, notifier)
    _stairs(m, 10)
    tail = []
    for _ in range(6):
        _tick_with(m)
        tail.append(m.live_rate()[1])
    assert tail[-1] == 0.0 and tail[-2] == 0.0   # 0 a los ~4 s
    assert tail[0] > 0                           # no se corta de golpe


def test_live_rate_first_snapshot_does_not_overshoot(settings, notifier):
    """El primer bloque (2 s de tráfico) no debe mostrarse como el doble ni
    disparar el detector de picos."""
    m = make_monitor(settings, notifier)
    _tick_with(m)
    _tick_with(m, recv=1_400_000)
    assert m.live_rate()[1] <= 700_000 * 1.01


def test_live_rate_tracks_up_and_down_independently(settings, notifier):
    m = make_monitor(settings, notifier)
    for sec in range(10):
        _tick_with(m, sent=200_000 if sec % 2 else 0, recv=0 if sec % 2 else 600_000)
    up, down = m.live_rate()
    assert 80_000 <= up <= 120_000 and 270_000 <= down <= 330_000


def _simulate(m, arrivals, seconds, rate=700_000):
    """Reloj falso: un _rate_tick por segundo y snapshots de nettop en `arrivals`
    (con jitter); cada snapshot trae los bytes del intervalo desde el anterior."""
    from src.domain.models import TrafficSample
    events = sorted([(t, "snap") for t in arrivals] +
                    [(float(s), "tick") for s in range(1, seconds + 1)], key=lambda e: (e[0], e[1] == "tick"))
    now = {"t": 0.0}
    m._clock = lambda: now["t"]
    prev, shown = 0.0, []
    for t, kind in events:
        now["t"] = t
        if kind == "snap":
            m._on_sample(TrafficSample(1, "curl", bytes_sent=0,
                                       bytes_recv=int(rate * (t - prev))))
            prev = t
        else:
            m._rate_tick()
            shown.append(m.live_rate()[1])
    return shown


def test_live_rate_is_steady_with_jittered_snapshots(settings, notifier):
    """Caso real medido: los snapshots llegan cada ~2 s con jitter y caen en
    distinto tick; el promedio de 4 bins crudos oscilaba 0.5x-2.5x."""
    m = make_monitor(settings, notifier)
    arrivals = [1.2, 3.0, 5.4, 7.1, 8.9, 11.3, 13.0, 15.2, 17.4, 19.0, 21.3, 23.1]
    shown = _simulate(m, arrivals, 24)[7:22]
    assert max(shown) <= 1.25 * 700_000 and min(shown) >= 0.75 * 700_000
