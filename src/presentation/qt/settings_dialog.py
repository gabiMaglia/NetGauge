"""Diálogo de Ajustes: idioma, retención del histórico e índice de confianza."""
from __future__ import annotations

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
from .i18n import LANGUAGES, t


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("dlg.settings.title"))
        self.setModal(True)
        self.setFixedWidth(420)
        self._settings = settings

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

        self._vt = QCheckBox(t("dlg.settings.vt"))
        self._vt.setChecked(settings.virustotal_enabled)
        root.addWidget(self._vt)
        self._vt_key = QLineEdit(settings.virustotal_api_key)
        self._vt_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._labeled(root, t("dlg.settings.vt_key"), self._vt_key)

        self._geoip = QCheckBox(t("dlg.settings.geoip"))
        self._geoip.setChecked(settings.geoip_enabled)
        root.addWidget(self._geoip)

        self._anomaly = QCheckBox(t("dlg.settings.anomaly"))
        self._anomaly.setChecked(settings.anomaly_alerts_enabled)
        root.addWidget(self._anomaly)

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
