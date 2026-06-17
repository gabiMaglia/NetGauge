"""Caso de uso central: orquesta captura -> acumulación -> persistencia -> consultas.

Incluye features comerciales: velocidad en vivo, cuota mensual y alertas.
"""
from __future__ import annotations

import threading
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

_SPIKE_FLOOR = 3 * 1024 * 1024     # 3 MB/s: piso para no avisar por ruido
_SPIKE_FACTOR = 3.0                # x veces el promedio reciente
_NEW_APP_BYTES = 5 * 1024 * 1024   # 5 MB enviados para considerar app "nueva en red"


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
        self._exe_paths: dict[str, str] = {}
        self._exe_paths_at: datetime | None = None
        self._last_purge: datetime | None = None
        self._translator: Callable[[str], str] | None = None

        # Detección de anomalías
        self._rate_history: deque[float] = deque(maxlen=30)
        self._last_spike: datetime | None = None
        self._seen_apps: set[str] = set()
        self._baseline_done = False

        self._lock = threading.Lock()
        self._session: dict[str, AppUsage] = {}
        self._pending: dict[str, AppUsage] = {}
        self._flush_timer: threading.Timer | None = None
        self._rate_timer: threading.Timer | None = None
        self._running = False

        # Velocidad en vivo: bytes acumulados en la última ventana de 1s.
        self._rate_sent = 0
        self._rate_recv = 0
        self._live_up = 0.0      # bytes/seg
        self._live_down = 0.0

        self.settings: Settings = settings_store.load()
        self._alerts_fired: set[int] = set()
        self._alert_cycle: datetime | None = None
        self._daily_alerts_fired: set[int] = set()
        self._alert_day: datetime | None = None

    # ---- ciclo de vida -------------------------------------------------
    def start(self) -> None:
        self._running = True
        self._capture.start(self._on_sample)
        self._schedule_flush()
        self._schedule_rate()

    def stop(self) -> None:
        if not self._running:
            return  # idempotente: stop() puede llegar desde quit_app y atexit
        self._running = False
        for t in (self._flush_timer, self._rate_timer):
            if t is not None:
                t.cancel()
        self._flush_timer = None
        self._rate_timer = None
        self._capture.stop()
        self._flush()

    # ---- captura -------------------------------------------------------
    def _on_sample(self, sample: TrafficSample) -> None:
        with self._lock:
            for bucket in (self._session, self._pending):
                usage = bucket.setdefault(sample.app_name, AppUsage(sample.app_name))
                usage.add(sample.bytes_sent, sample.bytes_recv)
            self._rate_sent += sample.bytes_sent
            self._rate_recv += sample.bytes_recv

    # ---- velocidad en vivo (cada 1s) ----------------------------------
    def _schedule_rate(self) -> None:
        if not self._running:
            return
        self._rate_timer = threading.Timer(1.0, self._rate_tick)
        self._rate_timer.daemon = True
        self._rate_timer.start()

    def _rate_tick(self) -> None:
        with self._lock:
            self._live_up = float(self._rate_sent)
            self._live_down = float(self._rate_recv)
            self._rate_sent = 0
            self._rate_recv = 0
        self._check_spike(self._live_up + self._live_down)
        self._schedule_rate()

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
        if not self._running:
            return
        self._flush_timer = threading.Timer(self._flush_interval, self._tick)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _tick(self) -> None:
        self._flush()
        self._check_quota_alerts()
        self._check_new_apps()
        self._purge_if_due()
        self._schedule_flush()

    def _purge_if_due(self) -> None:
        days = self.settings.retention_days
        if days <= 0:
            return
        now = datetime.now()
        # A lo sumo una purga cada 6 horas (barato y suficiente).
        if self._last_purge and (now - self._last_purge) < timedelta(hours=6):
            return
        self._last_purge = now
        try:
            self._repo.purge_older_than(now - timedelta(days=days))
        except Exception:  # noqa: BLE001
            pass

    def _flush(self) -> None:
        with self._lock:
            if not self._pending:
                return
            now = datetime.now()
            records = [
                UsageRecord(u.app_name, u.bytes_sent, u.bytes_recv, now)
                for u in self._pending.values()
            ]
            self._pending.clear()
        self._repo.save_batch(records)

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

    def quota_status(self) -> QuotaStatus:
        start = self._cycle_start()
        limit = int(self.settings.monthly_quota_gb * (1024**3))
        return QuotaStatus(
            used_bytes=self._usage_since(start), limit_bytes=limit, cycle_start=start
        )

    def daily_status(self) -> QuotaStatus:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        limit = int(self.settings.daily_quota_gb * (1024**3))
        return QuotaStatus(
            used_bytes=self._usage_since(start), limit_bytes=limit, cycle_start=start
        )

    def _check_quota_alerts(self) -> None:
        self._check_alerts(self.quota_status(), "monthly",
                           self._alerts_fired, "_alert_cycle")
        self._check_alerts(self.daily_status(), "daily",
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

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        self._settings_store.save(settings)
        self._alerts_fired.clear()  # re-evaluar con la nueva cuota
        self._daily_alerts_fired.clear()

    # ---- consultas para la UI -----------------------------------------
    def session_usage(self) -> list[AppUsage]:
        with self._lock:
            return sorted(self._session.values(), key=lambda u: -u.total)

    def usage_for_period(self, period: str) -> list[UsageRecord]:
        """period in {'day', 'week', 'month'}."""
        now = datetime.now()
        start = {
            "day": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": now - timedelta(days=now.weekday(), hours=now.hour,
                                    minutes=now.minute, seconds=now.second),
            "month": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        }.get(period, now - timedelta(days=1))
        return self._repo.totals_by_app(start, now + timedelta(seconds=1))

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
        """Veredicto de confianza de la app (cacheado por ruta del .exe)."""
        if self._trust is None or not self.settings.trust_check_enabled:
            return TrustInfo(level=TRUST_UNKNOWN)
        self._refresh_exe_paths()
        path = self._exe_paths.get(app_name)
        if not path:
            return TrustInfo(level=TRUST_UNKNOWN)
        info = self._trust.evaluate(path)
        return self._enrich_with_vt(info, path)

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
        if self._conn_provider is None:
            return []
        return self._conn_provider.connections()

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
