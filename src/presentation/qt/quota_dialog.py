"""Diálogo modal 'Configurar cuota' (pantalla 2 del handoff)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ...domain.models import Settings
from .i18n import t


class QuotaDialog(QDialog):
    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("dlg.quota.title"))
        self.setModal(True)
        self.setFixedWidth(420)
        self._settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(17)

        title = QLabel(t("dlg.quota.title"))
        title.setObjectName("DlgTitle")
        root.addWidget(title)

        self._daily = self._field(root, t("dlg.quota.daily"),
                                  settings.daily_quota_gb)
        self._monthly = self._field(root, t("dlg.quota.monthly"),
                                    settings.monthly_quota_gb)
        self._monthly.setFocus()

        self._day = QSpinBox()
        self._day.setRange(1, 28)
        self._day.setValue(settings.billing_cycle_start_day)
        self._labeled(root, t("dlg.quota.cycle_day"), self._day)

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

    def _field(self, root, label, value) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 100000.0)
        spin.setDecimals(2)
        spin.setSuffix(" GB")
        spin.setValue(float(value))
        self._labeled(root, label, spin)
        return spin

    def _labeled(self, root, label, widget) -> None:
        box = QVBoxLayout()
        box.setSpacing(6)
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        box.addWidget(lbl)
        box.addWidget(widget)
        root.addLayout(box)

    def result_settings(self) -> Settings:
        self._settings.daily_quota_gb = self._daily.value()
        self._settings.monthly_quota_gb = self._monthly.value()
        self._settings.billing_cycle_start_day = self._day.value()
        return self._settings
