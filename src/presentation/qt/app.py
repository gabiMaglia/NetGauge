"""Arranque de la app PySide6: ventana + tray + notifier, todo cableado."""
from __future__ import annotations

import sys

# Windows agrupa la app en la barra de tareas por este ID; sin él, usa el ícono
# del proceso host (genérico) en vez del de la ventana. Debe ir ANTES de crear
# cualquier ventana.
_APP_ID = "GabrielMaglia.trafficMe.NetworkMonitor"


def _set_app_user_model_id() -> None:
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_ID)
    except Exception:  # noqa: BLE001 — no es Windows o falló: no es crítico
        pass

from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ...application.monitor_service import MonitorService
from ...domain.models import human_bytes
from .i18n import t
from .main_window import MainWindow
from .single_instance import SingleInstance
from .widgets import make_app_qicon, make_sparkline_icon


class QtNotifier(QObject):
    """Notifier thread-safe (implementa el puerto Notifier por duck typing).

    No hereda de Notifier(ABC) a propósito: QObject trae su propia metaclase
    (sip) y mezclarla con ABCMeta da 'metaclass conflict'. Cumple el contrato
    con el método notify().

    El monitor llama notify() desde un hilo de fondo; la señal marshalea al
    hilo GUI para mostrar el toast del tray de forma segura."""

    _signal = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self._tray: QSystemTrayIcon | None = None
        self._signal.connect(self._show)

    def bind_tray(self, tray: QSystemTrayIcon) -> None:
        self._tray = tray

    def notify(self, title: str, message: str) -> None:
        self._signal.emit(title, message)

    def _show(self, title: str, message: str) -> None:
        if self._tray is not None:
            self._tray.showMessage(title, message,
                                   QSystemTrayIcon.MessageIcon.Information, 6000)


def run(monitor: MonitorService, per_process: bool, notifier: QtNotifier) -> int:
    _set_app_user_model_id()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # cerrar la ventana NO cierra la app
    app_icon = make_app_qicon()
    app.setWindowIcon(app_icon)  # ícono de marca en diálogos (About, Cuota)

    # Instancia única: si ya hay una corriendo, le pedimos que se muestre y salimos.
    guard = SingleInstance()
    if guard.already_running():
        return 0

    monitor.set_translator(t)  # avisos (cuota/anomalías) en el idioma elegido

    window = MainWindow(monitor, per_process)
    window.setWindowIcon(app_icon)

    tray = QSystemTrayIcon(app_icon, app)
    tray.setToolTip("trafficMe")
    notifier.bind_tray(tray)

    menu = QMenu()
    act_open = QAction(t("tray.metrics"), app)
    act_open.triggered.connect(lambda: (window.showNormal(), window.raise_(),
                                        window.activateWindow()))
    act_report = QAction(t("tray.export"), app)

    def export() -> None:
        path = monitor.generate_session_report()
        msg = t("tray.report_saved", path=path) if path else t("tray.report_empty")
        tray.showMessage("trafficMe", msg,
                         QSystemTrayIcon.MessageIcon.Information, 5000)
    act_report.triggered.connect(export)

    act_about = QAction(t("tray.about"), app)
    act_about.triggered.connect(window._open_about)

    act_quit = QAction(t("tray.quit"), app)

    def quit_app() -> None:
        # El informe lo genera el atexit de main.py (una sola vez).
        monitor.stop()
        guard.close()
        tray.hide()
        app.quit()
    act_quit.triggered.connect(quit_app)

    def show_window() -> None:
        window.showNormal()
        window.raise_()
        window.activateWindow()

    menu.addAction(act_open)
    menu.addAction(act_report)
    menu.addSeparator()
    menu.addAction(act_about)
    menu.addAction(act_quit)
    tray.setContextMenu(menu)

    def on_activate(reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # clic izquierdo
            window.showNormal()
            window.raise_()
            window.activateWindow()
    tray.activated.connect(on_activate)

    # Cuando una 2ª instancia toca el pipe, traemos esta ventana al frente.
    guard.listen(show_window)

    # Mini-gráfico en el tray + tooltip con velocidad y app top (cada 2s).
    spark: deque[float] = deque([0.0] * 24, maxlen=24)

    def update_tray() -> None:
        up, down = monitor.live_rate()
        spark.append(up + down)
        tray.setIcon(make_sparkline_icon(list(spark)))
        session = monitor.session_usage()
        top = session[0].app_name if session else "—"
        tray.setToolTip(
            f"trafficMe\n↓ {human_bytes(down)}/s   ↑ {human_bytes(up)}/s\n{top}")
    tray_timer = QTimer(window)
    tray_timer.timeout.connect(update_tray)
    tray_timer.start(2000)

    tray.show()
    monitor.start()
    window.show()  # arranca ENTERA y visible
    rc = app.exec()
    guard.close()
    return rc
