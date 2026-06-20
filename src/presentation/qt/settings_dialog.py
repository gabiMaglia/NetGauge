"""Diálogo de Ajustes: idioma, retención del histórico e índice de confianza."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ...domain.models import Settings
from ...domain.ports import ReputationService
from .i18n import LANGUAGES, t

_VT_SIGNUP_URL = "https://www.virustotal.com/gui/join-us"

# Estados del LED de conexión VT.
_LED_UNTESTED = "untested"
_LED_OK = "ok"
_LED_ERROR = "error"
_LED_TESTING = "testing"

_LED_COLOR = {
    _LED_UNTESTED: "#6b7280",   # gris
    _LED_TESTING: "#f59e0b",   # ámbar mientras consulta
    _LED_OK: "#10b981",        # verde
    _LED_ERROR: "#ef4444",     # rojo
}


class _VtKeyTester(QObject):
    """Corre test_api_key() en un hilo de fondo y emite el resultado a la UI.

    Mismo patrón que QtNotifier/check_updates en app.py: threading.Thread
    daemon + Signal de Qt para volver al hilo principal sin bloquear la UI.
    """

    finished = Signal(str, bool)  # (api_key probada, es_valida)

    def __init__(self, reputation: ReputationService) -> None:
        super().__init__()
        self._reputation = reputation

    def test(self, key: str) -> None:
        def run() -> None:
            ok = False
            try:
                ok = self._reputation.test_api_key(key)
            except Exception:  # noqa: BLE001 — nunca tirar abajo la UI por esto
                ok = False
            self.finished.emit(key, ok)
        threading.Thread(target=run, daemon=True).start()


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None,
                 reputation: ReputationService | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("dlg.settings.title"))
        self.setModal(True)
        # 480 (antes 420): a 420 el label de VT ("VirusTotal: reputación
        # online (envía solo el hash)") se corta y solo se lee completo con
        # hover -> el PO no se daba cuenta de que el checkbox ya estaba bien
        # tildado (T-014, causa raíz #1).
        self.setFixedWidth(480)
        self._settings = settings
        self._reputation = reputation
        self._tester = _VtKeyTester(reputation) if reputation else None
        if self._tester:
            self._tester.finished.connect(self._on_vt_test_result)
        # Debounce: no dispara una request por cada tecla, espera a que el
        # usuario deje de tipear/pegar (igual de espíritu al throttle de VT
        # en reputation_virustotal.py, pero acá es solo UX, no rate-limit).
        self._vt_debounce = QTimer(self)
        self._vt_debounce.setSingleShot(True)
        self._vt_debounce.setInterval(700)
        self._vt_debounce.timeout.connect(self._test_current_key)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(17)

        title = QLabel(t("dlg.settings.title"))
        title.setObjectName("DlgTitle")
        root.addWidget(title)

        self._lang = QComboBox()
        self._lang_codes = list(LANGUAGES.keys())
        for code in self._lang_codes:
            self._lang.addItem(LANGUAGES[code], code)
        if settings.language in self._lang_codes:
            self._lang.setCurrentIndex(self._lang_codes.index(settings.language))
        self._labeled(root, t("dlg.settings.language"), self._lang)

        self._retention = QSpinBox()
        self._retention.setRange(0, 3650)
        self._retention.setValue(settings.retention_days)
        self._labeled(root, t("dlg.settings.retention"), self._retention)

        self._trust = QCheckBox(t("dlg.settings.trust"))
        self._trust.setChecked(settings.trust_check_enabled)
        root.addWidget(self._trust)

        vt_row = QHBoxLayout()
        vt_row.setSpacing(8)
        self._vt = QCheckBox(t("dlg.settings.vt"))
        self._vt.setChecked(settings.virustotal_enabled)
        vt_row.addWidget(self._vt)
        vt_row.addStretch()
        self._vt_led = QLabel()
        self._vt_led.setFixedSize(12, 12)
        self._vt_led.setToolTip(t("dlg.settings.vt_led.untested"))
        vt_row.addWidget(self._vt_led)
        root.addLayout(vt_row)
        self._set_led(_LED_UNTESTED)

        self._vt_key = QLineEdit(settings.virustotal_api_key)
        self._vt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._vt_key.textChanged.connect(self._on_vt_key_changed)
        self._labeled(root, t("dlg.settings.vt_key"), self._vt_key)

        vt_link = QLabel(
            f'<a href="{_VT_SIGNUP_URL}">{t("dlg.settings.vt_signup")}</a>')
        vt_link.setObjectName("FieldLabel")
        vt_link.setOpenExternalLinks(True)
        vt_link.linkActivated.connect(
            lambda url: QDesktopServices.openUrl(QUrl(url)))
        root.addWidget(vt_link)

        # Si ya hay una key guardada, probarla al abrir el diálogo (sin
        # esperar a que se evalúe un proceso real).
        if self._tester and settings.virustotal_api_key:
            self._set_led(_LED_TESTING)
            self._tester.test(settings.virustotal_api_key)

        self._geoip = QCheckBox(t("dlg.settings.geoip"))
        self._geoip.setChecked(settings.geoip_enabled)
        root.addWidget(self._geoip)

        self._anomaly = QCheckBox(t("dlg.settings.anomaly"))
        self._anomaly.setChecked(settings.anomaly_alerts_enabled)
        root.addWidget(self._anomaly)

        privacy = QLabel(t("dlg.settings.privacy"))
        privacy.setObjectName("FieldLabel")
        privacy.setWordWrap(True)
        root.addWidget(privacy)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton(t("btn.cancel"))
        cancel.setObjectName("GhostBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton(t("btn.save"))
        save.setObjectName("PrimaryBtn")
        save.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

    def _set_led(self, state: str) -> None:
        color = _LED_COLOR[state]
        self._vt_led.setStyleSheet(
            f"background:{color}; border-radius:6px;")
        self._vt_led.setToolTip(t(f"dlg.settings.vt_led.{state}"))

    def _on_vt_key_changed(self, _text: str) -> None:
        self._set_led(_LED_UNTESTED)
        self._vt_debounce.start()

    def _test_current_key(self) -> None:
        key = self._vt_key.text().strip()
        if not key or not self._tester:
            self._set_led(_LED_UNTESTED)
            return
        self._set_led(_LED_TESTING)
        self._tester.test(key)

    def _on_vt_test_result(self, tested_key: str, ok: bool) -> None:
        # Si el usuario sigue tipeando, descartar resultados de keys viejas.
        if tested_key != self._vt_key.text().strip():
            return
        self._set_led(_LED_OK if ok else _LED_ERROR)

    def _labeled(self, root, label, widget) -> None:
        box = QVBoxLayout()
        box.setSpacing(6)
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        box.addWidget(lbl)
        box.addWidget(widget)
        root.addLayout(box)

    def result_settings(self) -> Settings:
        self._settings.language = self._lang_codes[self._lang.currentIndex()]
        self._settings.retention_days = self._retention.value()
        self._settings.trust_check_enabled = self._trust.isChecked()
        self._settings.virustotal_enabled = self._vt.isChecked()
        self._settings.virustotal_api_key = self._vt_key.text().strip()
        self._settings.geoip_enabled = self._geoip.isChecked()
        self._settings.anomaly_alerts_enabled = self._anomaly.isChecked()
        return self._settings
