"""Diálogo 'Acerca de' con datos de la app y botón de donación (Ko-fi)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ...version import APP_VERSION
from .i18n import t
from .widgets import BarsLogo

KOFI_URL = "https://ko-fi.com/gabrielmaglia"
AUTHOR = "Gabriel Maglia"


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("btn.about"))
        self.setModal(True)
        self.setFixedWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(12)
        head.addWidget(BarsLogo(40, 11))
        name_box = QVBoxLayout()
        name_box.setSpacing(2)
        name = QLabel('traffic<span style="color:#3b82f6;">Me</span>')
        name.setObjectName("DlgTitle")
        ver = QLabel(t("about.version", v=APP_VERSION))
        ver.setObjectName("FieldLabel")
        name_box.addWidget(name)
        name_box.addWidget(ver)
        head.addLayout(name_box)
        head.addStretch()
        root.addLayout(head)

        desc = QLabel(t("dlg.about.desc"))
        desc.setObjectName("FieldLabel")
        desc.setWordWrap(True)
        root.addWidget(desc)

        author = QLabel(t("dlg.about.made_by", author=AUTHOR))
        author.setObjectName("FieldLabel")
        author.setWordWrap(True)
        root.addWidget(author)

        support = QLabel(t("dlg.about.support"))
        support.setObjectName("FieldLabel")
        support.setWordWrap(True)
        root.addWidget(support)

        btns = QHBoxLayout()
        kofi = QPushButton(t("btn.kofi"))
        kofi.setCursor(Qt.CursorShape.PointingHandCursor)
        kofi.setStyleSheet(
            "QPushButton { background:#13C3FF; color:#0b1220; border:none;"
            " border-radius:10px; padding:11px 18px; font-weight:800; }"
            "QPushButton:hover { background:#00b4f0; }")
        kofi.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(KOFI_URL)))
        btns.addWidget(kofi)
        btns.addStretch()
        close = QPushButton(t("btn.close"))
        close.setObjectName("GhostBtn")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        root.addLayout(btns)
