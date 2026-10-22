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

from src.domain.models import Settings, TrafficSample, UsageRecord  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402

APPS = [("Google Chrome", 1, 900e6, 60e6), ("Dropbox", 2, 300e6, 250e6),
        ("Docker", 3, 400e6, 30e6), ("Spotify", 4, 120e6, 2e6),
        ("Slack", 5, 80e6, 40e6), ("Zoom", 6, 60e6, 55e6)]


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
    for idx, name in enumerate(("global", "apps", "conexiones")):
        w._tabs.setCurrentIndex(idx)
        w._refresh()
        app.processEvents()
        w.grab().save(str(out / f"ui_{name}.png"))
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
