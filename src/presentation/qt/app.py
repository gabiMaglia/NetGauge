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

import threading
from collections import deque

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ...application.monitor_service import MonitorService
from ...domain.models import human_bytes
from ...infrastructure.update.github_updater import check_latest
from ...version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO
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


def _fix_dpi_rounding_policy() -> None:
    """Fija la política de escalado DPI ANTES de crear QApplication.

    Sin esto, con escalado fraccional de Windows (125%/150%/175% — frecuente
    en notebooks, no tanto en monitores de escritorio) Qt puede redondear el
    factor de escala de forma distinta a como lo hace win32 puro. El chrome
    nativo de la ventana (native_window.py) recibe coordenadas FÍSICAS de
    WM_NCHITTEST y las convierte a lógicas con QWindow.mapFromGlobal(); si la
    política de redondeo no es consistente, ese mapeo queda desalineado y los
    botones del header / bordes de resize "apuntan" al lugar equivocado
    -> ventana inmóvil, sin resize y con los botones muertos pese a que el
    resto de la UI (que no usa coordenadas físicas) funciona normal.
    PassThrough preserva el factor de escala real (sin redondear a entero),
    que es lo que necesita la conversión física<->lógica en native_window.py.
    """
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:  # noqa: BLE001 — best-effort, no debe impedir el arranque
        pass


def run(monitor: MonitorService, per_process: bool, notifier: QtNotifier) -> int:
    _set_app_user_model_id()
    _fix_dpi_rounding_policy()
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
    export_menu = QMenu(t("tray.export"))

    def export(fmt: str) -> None:
        try:
            path = monitor.generate_session_report(fmt)
        except Exception as exc:  # noqa: BLE001 — dependencia faltante / I/O
            tray.showMessage("trafficMe", t("tray.report_error", err=str(exc)),
                             QSystemTrayIcon.MessageIcon.Warning, 6000)
            return
        msg = t("tray.report_saved", path=path) if path else t("tray.report_empty")
        tray.showMessage("trafficMe", msg,
                         QSystemTrayIcon.MessageIcon.Information, 5000)

    for label, fmt in (("CSV", "csv"), ("Excel (.xlsx)", "xlsx"), ("PDF", "pdf")):
        act = QAction(label, app)
        act.triggered.connect(lambda _checked=False, f=fmt: export(f))
        export_menu.addAction(act)

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
    menu.addMenu(export_menu)
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

    # Chequeo de actualización contra GitHub Releases (en segundo plano).
    def check_updates() -> None:
        found = check_latest(GITHUB_OWNER, GITHUB_REPO, APP_VERSION)
        if found:
            ver, url = found
            notifier.notify(t("alert.update.title"),
                            t("alert.update.body", v=ver, url=url))
    threading.Thread(target=check_updates, daemon=True).start()

    tray.show()
    monitor.start()
    window.show()  # arranca ENTERA y visible
    rc = app.exec()
    guard.close()
    return rc
