"""Caso de uso central: orquesta captura -> acumulación -> persistencia -> consultas.

Incluye features comerciales: velocidad en vivo, cuota mensual y alertas.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Callable

from ..domain.models import (
    TRUST_SUSPICIOUS,
    TRUST_UNKNOWN,
    AppUsage,
    Connection,
    QuotaStatus,
    Settings,
    TrafficSample,
    TrustInfo,
    UsageRecord,
    human_bytes,
    worst_trust,
)
from ..domain.ports import (
    CaptureService,
    ConnectionProvider,
    GeoIpService,
    Notifier,
    ReportGenerator,
    ReputationService,
    SettingsStore,
    TrustEvaluator,
    UsageRepository,
)
from .snapshot_refresher import SnapshotRefresher

log =logging.getLogger(__name__)

_SPIKE_FLOOR =3 * 1024 * 1024     # 3 MB/s: piso para no avisar por ruido
_SPIKE_FACTOR = 3.0                # x veces el promedio reciente
_NEW_APP_BYTES = 5 * 1024 * 1024   # 5 MB enviados para considerar app "nueva en red"
# Las conexiones sólo se enumeran mientras la UI las pidió en los últimos
# N segundos (MainWindow sólo las pide con la pestaña visible).
_CONN_DEMAND_S = 10.0

# T-024: nombres de helpers INTERNOS de la propia app que NO deben aparecer
# en "Por aplicación" ni contar como una app del usuario (es infraestructura
# de captura, no algo que el usuario abrió). Hoy solo `nettop` en macOS
# (NettopCaptureService lo reporta a sí mismo dentro de su propia salida);
# en Windows el helper es ETW in-process y no genera una fila propia, pero
# el set queda genérico/extensible para futuros helpers de cualquier OS.
_INTERNAL_HELPER_NAMES = frozenset({"nettop"})


def _is_internal_helper(app_name: str) -> bool:
    return app_name.lower() in _INTERNAL_HELPER_NAMES


class MonitorService:
    def __init__(
        self,
        capture: CaptureService,
        repository: UsageRepository,
        reporter: ReportGenerator,
        settings_store: SettingsStore,
        notifier: Notifier,
        flush_interval: float = 10.0,
        trust_evaluator: TrustEvaluator | None = None,
        connection_provider: ConnectionProvider | None = None,
        reputation: ReputationService | None = None,
        geoip: GeoIpService | None = None,
        snapshot_interval: float = 2.0,
    ) -> None:
        self._capture = capture
        self._repo = repository
        self._reporter = reporter
        self._reporters = {"csv": reporter}  # otros formatos se registran aparte
        self._settings_store = settings_store
        self._notifier = notifier
        self._flush_interval = flush_interval
        self._trust = trust_evaluator
        self._conn_provider = connection_provider
        self._reputation = reputation
        self._geoip = geoip
        self._exe_paths: dict[str, frozenset[str]] = {}
        self._exe_paths_at: datetime | None = None
        self._last_purge: datetime | None = None
        self._translator: Callable[[str], str] | None = None

        # Detección de anomalías
        self._rate_history: deque[float] = deque(maxlen=30)
        self._last_spike: datetime | None = None
        self._seen_apps: set[str] = set()
        self._baseline_done = False

        self._lock = threading.Lock()
        # _sched_lock: protege _running y los timers (start/stop vs. ticks).
        # _tick_lock: serializa _tick con el flush final de stop(), para que
        # nada toque el repositorio después de que stop() retorna.
        # Orden: nunca tomar _sched_lock teniendo _tick_lock.
        self._sched_lock = threading.Lock()
        self._tick_lock = threading.Lock()
        self._session: dict[str, AppUsage] = {}
        self._pending: dict[str, AppUsage] = {}
        self._flush_timer: threading.Timer | None = None
        self._rate_timer: threading.Timer | None = None
        self._running = False

        # Velocidad en vivo: bytes acumulados en la última ventana de 1s.
        self._rate_sent = 0
        self._rate_recv = 0
        self._live_up = 0.0      # bytes/seg (suavizado, lo que se muestra)
        self._live_down = 0.0
        # Suavizado de la tasa mostrada (T-012): nettop entrega ~1 bloque/s
        # pero su reloj no está en fase con _rate_tick (también 1s) -> deltas
        # tipo [0, 2x, 0, 2x] (aliasing). Promedio móvil de las últimas 3
        # lecturas crudas de 1s absorbe esa alternancia sin introducir
        # demasiado lag (responde a un cambio real en ~3s).
        self._RATE_WINDOW = 3
        self._raw_up_history: deque[float] = deque(maxlen=self._RATE_WINDOW)
        self._raw_down_history: deque[float] = deque(maxlen=self._RATE_WINDOW)

        self.settings: Settings = settings_store.load()
        self._alerts_fired: set[int] = set()
        self._alert_cycle: datetime | None = None
        self._daily_alerts_fired: set[int] = set()
        self._alert_settings_key = self._alert_key(self.settings)
        self._alert_day: datetime | None = None

        # ---- snapshot para la UI (plan 04) ------------------------------
        # La UI SÓLO lee estos campos (getters baratos, sin IO). Los llena el
        # worker de fondo vía refresh_snapshot(). Lock propio: _lock es el del
        # camino caliente de captura y no queremos contención con la UI.
        # Regla: nunca hacer IO con _snap_lock tomado.
        self._snap_lock = threading.Lock()
        self._snap_daily: QuotaStatus | None = None
        self._snap_monthly: QuotaStatus | None = None
        self._snap_periods: dict[str, list[UsageRecord]] = {}
        self._wanted_period: str | None = None
        self._snap_trust: dict[str, TrustInfo] = {}
        self._trust_requested: set[str] = set()
        self._snap_connections: list[Connection] = []
        self._conn_wanted_at: float | None = None
        self._refresher = SnapshotRefresher(self.refresh_snapshot,
                                            interval=snapshot_interval)

    @property
    def reputation_service(self) -> ReputationService | None:
        """Acceso de solo lectura para la capa de presentación (ej. probar
        la API key de VirusTotal en Settings sin esperar a un proceso real)."""
        return self._reputation

    # ---- ciclo de vida -------------------------------------------------
    def start(self) -> None:
        with self._sched_lock:
            self._running = True
        self._capture.start(self._on_sample)
        self._schedule_flush()
        self._schedule_rate()
        self._refresher.start()

    def stop(self) -> None:
        with self._sched_lock:
            if not self._running:
                return  # idempotente: stop() puede llegar desde quit_app y atexit
            self._running = False
            timers = (self._flush_timer, self._rate_timer)
            self._flush_timer = None
            self._rate_timer = None
        for t in timers:
            if t is not None:
                t.cancel()
        # Fuera de _sched_lock (el join puede tardar hasta su timeout) y antes
        # del flush final: el worker lee del repo y no debe correr después.
        try:
            self._refresher.stop()
        except Exception:  # noqa: BLE001
            log.exception("Fallo deteniendo el worker del snapshot")
        try:
            self._capture.stop()
        except Exception:  # noqa: BLE001
            log.exception("Fallo deteniendo la captura")
        # Espera un _tick en curso y hace el flush final.
        with self._tick_lock:
            try:
                self._flush()
            except Exception:  # noqa: BLE001
                log.exception("Fallo en el flush final al detener el monitor")

    # ---- captura -------------------------------------------------------
    def _on_sample(self, sample: TrafficSample) -> None:
        if _is_internal_helper(sample.app_name):
            return  # T-024: el helper de captura (nettop) no es una app del usuario
        with self._lock:
            for bucket in (self._session, self._pending):
                usage = bucket.setdefault(sample.app_name, AppUsage(sample.app_name))
                usage.add(sample.bytes_sent, sample.bytes_recv)
            self._rate_sent += sample.bytes_sent
            self._rate_recv += sample.bytes_recv

    # ---- velocidad en vivo (cada 1s) ----------------------------------
    def _schedule_rate(self) -> None:
        with self._sched_lock:
            if not self._running:
                return
            self._rate_timer = threading.Timer(1.0, self._rate_tick)
            self._rate_timer.daemon = True
            self._rate_timer.start()

    def _rate_tick(self) -> None:
        try:
            with self._lock:
                raw_up = float(self._rate_sent)
                raw_down = float(self._rate_recv)
                self._rate_sent = 0
                self._rate_recv = 0
                # Suavizado (T-012): promedio móvil sobre las últimas
                # _RATE_WINDOW lecturas crudas de 1s. Solo afecta lo MOSTRADO
                # (_live_up/_live_down); los totales/persistencia ya quedaron
                # actualizados en _on_sample y no se tocan aquí.
                self._raw_up_history.append(raw_up)
                self._raw_down_history.append(raw_down)
                self._live_up = sum(self._raw_up_history) / len(self._raw_up_history)
                self._live_down = sum(self._raw_down_history) / len(self._raw_down_history)
                smoothed_total = self._live_up + self._live_down
            self._check_spike(smoothed_total)
        except Exception:  # noqa: BLE001
            log.exception("Fallo en el tick de velocidad; sigo")
        finally:
            self._schedule_rate()  # la velocidad en vivo nunca se congela

    # ---- i18n de avisos -----------------------------------------------
    def set_translator(self, translator: Callable[[str], str]) -> None:
        self._translator = translator

    def _tr(self, key: str, **kw) -> str:
        base = self._translator(key) if self._translator else key
        return base.format(**kw) if kw else base

    # ---- anomalías -----------------------------------------------------
    def _check_spike(self, total_rate: float) -> None:
        history = list(self._rate_history)
        self._rate_history.append(total_rate)
        if not self.settings.anomaly_alerts_enabled or len(history) < 10:
            return
        avg = sum(history) / len(history)
        if avg <= 0 or total_rate < max(_SPIKE_FLOOR, _SPIKE_FACTOR * avg):
            return
        now = datetime.now()
        if self._last_spike and (now - self._last_spike) < timedelta(seconds=120):
            return
        self._last_spike = now
        self._notifier.notify(
            self._tr("alert.spike.title"),
            self._tr("alert.spike.body", rate=human_bytes(total_rate),
                     x=f"{total_rate / avg:.0f}"))

    def _check_new_apps(self) -> None:
        if not self.settings.anomaly_alerts_enabled:
            return
        with self._lock:
            current = list(self._session.values())
        if not self._baseline_done:
            self._seen_apps = {u.app_name for u in current}
            self._baseline_done = True
            return
        for u in current:
            if u.app_name in self._seen_apps:
                continue
            if u.bytes_sent >= _NEW_APP_BYTES:
                self._seen_apps.add(u.app_name)
                self._notifier.notify(
                    self._tr("alert.newapp.title"),
                    self._tr("alert.newapp.body", app=u.app_name,
                             sent=human_bytes(u.bytes_sent)))

    def live_rate(self) -> tuple[float, float]:
        """(subida, bajada) en bytes/segundo de la última ventana."""
        with self._lock:
            return self._live_up, self._live_down

    # ---- flush periódico ----------------------------------------------
    def _schedule_flush(self) -> None:
        with self._sched_lock:
            if not self._running:
                return
            self._flush_timer = threading.Timer(self._flush_interval, self._tick)
            self._flush_timer.daemon = True
            self._flush_timer.start()

    def _tick(self) -> None:
        try:
            with self._tick_lock:
                if not self._running:
                    return  # stop() ya corrió: no tocar el repositorio
                # Cada paso aislado: si falla el flush (DB bloqueada) igual corren
                # cuotas, apps nuevas y purga; el batch queda pendiente.
                for step in (self._flush, self._check_quota_alerts,
                             self._check_new_apps, self._purge_if_due):
                    try:
                        step()
                    except Exception:  # noqa: BLE001
                        log.exception("Fallo en %s; se reintenta en el próximo tick",
                                      step.__name__)
        finally:
            self._schedule_flush()  # fuera de _tick_lock; no-op si ya no corre

    def _purge_if_due(self) -> None:
        days = self.settings.retention_days
        if days <= 0:
            return
        now = datetime.now()
        # A lo sumo una purga cada 6 horas (barato y suficiente).
        if self._last_purge and (now - self._last_purge) < timedelta(hours=6):
            return
        try:
            self._repo.purge_older_than(now - timedelta(days=days))
        except Exception:  # noqa: BLE001
            log.exception("Fallo purgando el histórico; se reintenta en el próximo tick")
            return
        self._last_purge = now  # sólo si tuvo éxito

    def _flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            batch, self._pending = self._pending, {}
            now = datetime.now()
            records = [
                UsageRecord(u.app_name, u.bytes_sent, u.bytes_recv, now)
                for u in batch.values()
            ]
        try:
            self._repo.save_batch(records)
        except Exception:
            # No perder el batch: vuelve a pendientes, SUMADO a lo que haya
            # llegado mientras tanto; se reintenta en el próximo tick.
            with self._lock:
                for name, usage in batch.items():
                    pending = self._pending.setdefault(name, AppUsage(name))
                    pending.add(usage.bytes_sent, usage.bytes_recv)
            raise

    # ---- cuota mensual -------------------------------------------------
    def _cycle_start(self) -> datetime:
        now = datetime.now()
        day = max(1, min(28, self.settings.billing_cycle_start_day))
        start = now.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
        if start > now:  # el día de corte aún no llegó este mes
            start = (start - timedelta(days=32)).replace(day=day)
        return start

    def _usage_since(self, start: datetime) -> int:
        now = datetime.now()
        records = self._repo.totals_by_app(start, now + timedelta(seconds=1))
        return sum(r.bytes_sent + r.bytes_recv for r in records)

    @staticmethod
    def _day_start() -> datetime:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def _monthly_limit(self) -> int:
        return int(self.settings.monthly_quota_gb * (1024**3))

    def _daily_limit(self) -> int:
        return int(self.settings.daily_quota_gb * (1024**3))

    def _compute_quota_status(self) -> QuotaStatus:
        """Consulta SQLite: SÓLO desde hilos de fondo (worker / timer de flush)."""
        start = self._cycle_start()
        return QuotaStatus(used_bytes=self._usage_since(start),
                           limit_bytes=self._monthly_limit(), cycle_start=start)

    def _compute_daily_status(self) -> QuotaStatus:
        """Consulta SQLite: SÓLO desde hilos de fondo (worker / timer de flush)."""
        start = self._day_start()
        return QuotaStatus(used_bytes=self._usage_since(start),
                           limit_bytes=self._daily_limit(), cycle_start=start)

    @staticmethod
    def _from_snapshot(snap: QuotaStatus | None, start: datetime,
                       limit: int) -> QuotaStatus:
        # Si el snapshot es de otro ciclo/día (recién cambió), 0 hasta el
        # próximo refresco antes que mostrar el consumo del período anterior.
        used = snap.used_bytes if snap is not None and snap.cycle_start == start else 0
        return QuotaStatus(used_bytes=used, limit_bytes=limit, cycle_start=start)

    def quota_status(self) -> QuotaStatus:
        """Para la UI: lee el snapshot (sin IO). El límite sale de los settings
        actuales para reflejar un cambio de cuota sin esperar al worker."""
        with self._snap_lock:
            snap = self._snap_monthly
        return self._from_snapshot(snap, self._cycle_start(), self._monthly_limit())

    def daily_status(self) -> QuotaStatus:
        """Para la UI: lee el snapshot (sin IO)."""
        with self._snap_lock:
            snap = self._snap_daily
        return self._from_snapshot(snap, self._day_start(), self._daily_limit())

    def _check_quota_alerts(self) -> None:
        # Corre en el timer de flush (fuera del hilo GUI): consulta directo.
        self._check_alerts(self._compute_quota_status(), "monthly",
                           self._alerts_fired, "_alert_cycle")
        self._check_alerts(self._compute_daily_status(), "daily",
                           self._daily_alerts_fired, "_alert_day")

    def _check_alerts(self, status: QuotaStatus, scope: str,
                      fired: set[int], cycle_attr: str) -> None:
        if not status.has_limit:
            return
        # Reinicia los avisos cuando arranca un nuevo ciclo/día.
        if getattr(self, cycle_attr) != status.cycle_start:
            setattr(self, cycle_attr, status.cycle_start)
            fired.clear()

        scope_label = self._tr("alert.scope." + scope)
        for threshold in sorted(self.settings.alert_thresholds):
            if status.percent >= threshold and threshold not in fired:
                fired.add(threshold)
                self._notifier.notify(
                    self._tr("alert.quota.title", scope=scope_label),
                    self._tr("alert.quota.body", pct=threshold, scope=scope_label,
                             used=human_bytes(status.used_bytes),
                             limit=human_bytes(status.limit_bytes)))

    @staticmethod
    def _alert_key(s: Settings) -> tuple:
        return (s.monthly_quota_gb, s.daily_quota_gb, s.billing_cycle_start_day,
                tuple(s.alert_thresholds))

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        self._settings_store.save(settings)
        if not settings.geoip_enabled and self._geoip is not None:
            self._geoip.cancel_pending()   # apagar GeoIP corta la cola ya
        # Rearmar avisos sólo si cambió algo que los afecta: guardar la geometría
        # al ocultar la ventana no debe repetir los toasts 80/100 %. Se compara
        # contra una copia (los llamadores mutan el mismo objeto Settings).
        key = self._alert_key(settings)
        if key != self._alert_settings_key:
            self._alert_settings_key = key
            self._alerts_fired.clear()
            self._daily_alerts_fired.clear()
        self._refresher.trigger()  # límites/flags nuevos: refrescar ya

    # ---- snapshot para la UI (worker de fondo, plan 04) ----------------
    def set_snapshot_listener(self, callback: Callable[[], None] | None) -> None:
        """Avisa tras cada refresco. Corre en el hilo del worker: la UI debe
        saltar a su hilo (señal Qt encolada)."""
        self._refresher.set_listener(callback)

    def refresh_snapshot(self) -> None:
        """Un ciclo del worker: hace TODO el IO que antes hacía la UI y lo
        publica. Cada paso es independiente: si uno falla, los demás siguen.
        Público para poder testearlo de forma síncrona."""
        for step in (self._refresh_quota_snapshot, self._refresh_period_snapshot,
                     self._refresh_connections_snapshot, self._refresh_trust_snapshot):
            try:
                step()
            except Exception:  # noqa: BLE001
                log.exception("Fallo refrescando %s", step.__name__)

    def _refresh_quota_snapshot(self) -> None:
        daily = self._compute_daily_status()
        monthly = self._compute_quota_status()
        with self._snap_lock:
            self._snap_daily = daily
            self._snap_monthly = monthly

    def _refresh_period_snapshot(self) -> None:
        with self._snap_lock:
            period = self._wanted_period
        if period is None:
            return
        rows = self._compute_usage_for_period(period)
        with self._snap_lock:
            self._snap_periods[period] = rows

    # ---- consultas para la UI -----------------------------------------
    def session_usage(self) -> list[AppUsage]:
        with self._lock:
            return sorted(self._session.values(), key=lambda u: -u.total)

    @staticmethod
    def _period_start(period: str) -> datetime:
        now = datetime.now()
        return {
            "day": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0),
            "month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        }.get(period, now - timedelta(days=1))

    def _compute_usage_for_period(self, period: str) -> list[UsageRecord]:
        """Consulta SQLite: SÓLO desde el worker."""
        now = datetime.now()
        return self._repo.totals_by_app(self._period_start(period),
                                        now + timedelta(seconds=1))

    def usage_for_period(self, period: str) -> list[UsageRecord]:
        """Para la UI. period in {'day', 'week', 'month'}. Lee el snapshot (sin
        IO); si es un período nuevo despierta al worker UNA vez y devuelve lo
        último conocido (o vacío) hasta que llegue el dato."""
        with self._snap_lock:
            rows = self._snap_periods.get(period)
            changed = period != self._wanted_period
            self._wanted_period = period
        if changed:
            self._refresher.trigger()
        return list(rows) if rows is not None else []

    # ---- índice de confianza / conexiones -----------------------------
    def _refresh_exe_paths(self) -> None:
        if self._conn_provider is None:
            return
        now = datetime.now()
        if self._exe_paths_at and (now - self._exe_paths_at) < timedelta(seconds=30):
            return
        try:
            self._exe_paths = self._conn_provider.exe_paths()
            self._exe_paths_at = now
        except Exception:  # noqa: BLE001
            pass

    def trust_for(self, app_name: str) -> TrustInfo:
        """Para la UI: veredicto del snapshot (sin IO). Una app nunca vista
        devuelve UNKNOWN ("evaluando") y queda encolada para el worker."""
        if self._trust is None or not self.settings.trust_check_enabled:
            return TrustInfo(level=TRUST_UNKNOWN)
        with self._snap_lock:
            info = self._snap_trust.get(app_name)
            is_new = app_name not in self._trust_requested
            self._trust_requested.add(app_name)
        if is_new:
            # Una sola vez por app: una app sin ruta ("System", "PID n")
            # nunca se resuelve y no debe despertar al worker en cada repintado.
            self._refresher.trigger()
        return info if info is not None else TrustInfo(level=TRUST_UNKNOWN)

    def _refresh_trust_snapshot(self) -> None:
        """Worker: evalúa las apps pedidas por la UI. El evaluador cachea por
        ruta, así que sólo la PRIMERA evaluación de cada .exe es cara; VT se
        re-aplica cada ciclo porque su lookup es asíncrono (llega después)."""
        if self._trust is None or not self.settings.trust_check_enabled:
            return
        with self._snap_lock:
            wanted = sorted(self._trust_requested)
        if not wanted:
            return
        self._refresh_exe_paths()
        for app in wanted:
            paths = self._exe_paths.get(app)
            if not paths:
                continue   # sin .exe conocido: queda lo último (o UNKNOWN)
            try:
                # VT por ruta ANTES de combinar: una detección en cualquiera
                # de los homónimos vuelve sospechosa la fila.
                info = worst_trust(
                    self._enrich_with_vt(self._trust.evaluate(p), p)
                    for p in sorted(paths))
            except Exception:  # noqa: BLE001 — una app rota no frena a las demás
                log.exception("Fallo evaluando confianza de %s", app)
                continue
            with self._snap_lock:
                self._snap_trust[app] = info   # de a una: la UI ve progreso

    def _enrich_with_vt(self, info: TrustInfo, path: str) -> TrustInfo:
        if (self._reputation is None or not self.settings.virustotal_enabled
                or not self.settings.virustotal_api_key):
            return info
        self._reputation.set_api_key(self.settings.virustotal_api_key)
        vt = self._reputation.lookup(path)
        if vt is None:
            return info                      # aún no hay dato (consulta en curso)
        malicious, total = vt
        reason = "trust.vt_detected" if malicious > 0 else "trust.vt_clean"
        level = TRUST_SUSPICIOUS if malicious > 0 else info.level
        return replace(info, vt_malicious=malicious, vt_total=total,
                       level=level, reasons=info.reasons + (reason,))

    def connections(self) -> list[Connection]:
        """Para la UI: conexiones del snapshot (sin psutil en el hilo GUI).
        Llamarla marca demanda; el worker sólo enumera mientras haya demanda."""
        if self._conn_provider is None:
            return []
        now = time.monotonic()
        with self._snap_lock:
            stale = (self._conn_wanted_at is None
                     or now - self._conn_wanted_at > _CONN_DEMAND_S)
            self._conn_wanted_at = now
            conns = list(self._snap_connections)
        if stale:
            self._refresher.trigger()
        return conns

    def _refresh_connections_snapshot(self) -> None:
        if self._conn_provider is None:
            return
        with self._snap_lock:
            wanted_at = self._conn_wanted_at
        if wanted_at is None or time.monotonic() - wanted_at > _CONN_DEMAND_S:
            return
        conns = self._conn_provider.connections()
        with self._snap_lock:
            self._snap_connections = conns

    def geo_for(self, ip: str) -> tuple[str, str] | None:
        """(country_code, org) de una IP remota, o None si no/aún no."""
        if self._geoip is None or not self.settings.geoip_enabled:
            return None
        return self._geoip.lookup(ip)

    def register_reporter(self, fmt: str, generator: ReportGenerator) -> None:
        self._reporters[fmt] = generator

    def generate_session_report(self, fmt: str = "csv") -> str:
        now = datetime.now()
        records = [
            UsageRecord(u.app_name, u.bytes_sent, u.bytes_recv, now)
            for u in self.session_usage()
        ]
        if not records:
            return ""  # sin datos (p.ej. 2ª instancia que salió enseguida)
        reporter = self._reporters.get(fmt, self._reporter)
        return reporter.generate(records)
