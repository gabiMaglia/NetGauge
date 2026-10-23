"""Renderiza MainWindow offscreen con datos falsos y guarda PNGs (verificación visual)."""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from src.presentation.qt import theme  # noqa: E402

theme.load_app_fonts()
from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from datetime import datetime  # noqa: E402

from src.domain.models import Connection, Settings, TrafficSample, UsageRecord  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402

APPS = [("Google Chrome", 1, 900e6, 60e6), ("Dropbox", 2, 300e6, 250e6),
        ("Docker", 3, 400e6, 30e6), ("Spotify", 4, 120e6, 2e6),
        ("Slack", 5, 80e6, 40e6), ("Zoom", 6, 60e6, 55e6)]


CONNS = [
    Connection("Google Chrome", 1, "142.250.78.14", 443, "ESTABLISHED"),
    Connection("Google Chrome", 1, "2800:3f0:4002:80c::200e", 443, "ESTABLISHED"),
    Connection("Dropbox", 2, "162.125.2.14", 443, "ESTABLISHED"),
    Connection("Docker", 3, "104.18.123.25", 443, "TIME_WAIT"),
    Connection("Slack", 5, "3.209.62.201", 443, "CLOSE_WAIT"),
    Connection("Spotify", 4, "0.0.0.0", 57621, "LISTEN"),
    Connection("Zoom", 6, "170.114.52.2", 8801, "SYN_SENT"),
]
GEO = {"142.250.78.14": ("AR", "Google LLC"), "162.125.2.14": ("US", "Dropbox, Inc."),
       "104.18.123.25": ("US", "Cloudflare"), "3.209.62.201": ("US", "Amazon")}


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    random.seed(1)
    for _ in range(3):
        for name, pid, rx, tx in APPS:
            m._on_sample(TrafficSample(pid, name, bytes_sent=int(tx * random.random() / 3),
                                       bytes_recv=int(rx * random.random() / 3)))
    w = MainWindow(m, per_process=True)
    w.show()
    app.processEvents()
    state = {"conns": []}
    m.connections = lambda: list(state["conns"])  # type: ignore[method-assign]
    m.geo_for = lambda ip: GEO.get(ip)  # type: ignore[method-assign]
    for idx, name in enumerate(("global", "apps")):
        w._tabs.setCurrentIndex(idx)
        w._refresh()
        app.processEvents()
        w.grab().save(str(out / f"ui_{name}.png"))
    w._monitor.settings.hide_localhost = False
    w._hide_local_cb.setChecked(True)
    w._tabs.setCurrentIndex(2)
    app.processEvents()
    w.grab().save(str(out / "ui_conexiones_empty.png"))
    state["conns"] = list(CONNS)
    w._refresh()
    app.processEvents()
    w.grab().save(str(out / "ui_conexiones.png"))
    w._hide_local_cb.setChecked(False)
    state["conns"] = []
    # Fila con badge de confianza (Chrome) y fila con VirusTotal (Dropbox): comprueba que no
    # desalinean las columnas derechas.
    from src.domain.models import TRUST_CAUTION, TRUST_TRUSTED, TrustInfo
    real_trust = m.trust_for
    m.trust_for = lambda a: (  # type: ignore[method-assign]
        TrustInfo(level=TRUST_TRUSTED, signed=True, signer="Google LLC") if a == "Google Chrome"
        else TrustInfo(level=TRUST_CAUTION, vt_total=70, vt_malicious=0) if a == "Dropbox"
        else real_trust(a))
    w._tabs.setCurrentIndex(1)
    w._refresh()
    app.processEvents()
    w.grab().save(str(out / "ui_apps_badges.png"))
    m.trust_for = real_trust  # type: ignore[method-assign]
    w._refresh()
    # Vista "Día" con tendencias: el FakeRepo no tiene período previo, se simula aquí.
    mb = 1024 * 1024
    m.previous_period_breakdown = lambda period: (400 * mb, 700 * mb)  # type: ignore[method-assign]
    m.previous_period_total = lambda period: 1100 * mb  # type: ignore[method-assign]
    m.usage_for_period = lambda period: [  # type: ignore[method-assign]
        UsageRecord(u.app_name, u.bytes_sent, u.bytes_recv, datetime.now())
        for u in m.session_usage()]
    w._tabs.setCurrentIndex(0)
    w._set_period("day")
    app.processEvents()
    w.grab().save(str(out / "ui_global_day.png"))
    print("ok", out)


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ng_ui"))
