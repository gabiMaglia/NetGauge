"""Estructura de la fila de navegación (pestañas + período + unidad); corre offscreen en cualquier SO."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from conftest import FakeCapture, FakeNotifier, FakeRepo, FakeReporter, FakeStore  # noqa: E402
from src.application.monitor_service import MonitorService  # noqa: E402
from src.domain.models import Settings  # noqa: E402
from src.presentation.qt.main_window import MainWindow  # noqa: E402


@pytest.fixture
def win():
    app = QApplication.instance() or QApplication([])
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings()), FakeNotifier())
    w = MainWindow(m, per_process=True)
    yield w
    w.close()
    app.processEvents()


def test_quota_button_removed(win):
    assert not hasattr(win, "_quota_btn")
    assert hasattr(win, "_open_quota")


def test_tabbar_and_period_share_nav_row(win):
    row = win._nav_row
    assert row.indexOf(win._tabs.tabBar()) >= 0
    assert row.indexOf(win._seg_group.buttons()[0].parent().parent()) >= 0 or \
        any(row.itemAt(i).widget() is not None and
            row.itemAt(i).widget().isAncestorOf(win._seg_group.buttons()[0])
            for i in range(row.count()))
    assert any(row.itemAt(i).widget() is not None and
               row.itemAt(i).widget().isAncestorOf(win._unit_box)
               for i in range(row.count()))
    assert len(win._seg_group.buttons()) == 4


def test_unit_caption_and_tabs_still_switch(win):
    caps = [lb for lb in win.findChildren(QLabel) if lb.objectName() == "UnitCaption"]
    assert len(caps) == 1 and caps[0].text() == "Unidad"
    win._tabs.setCurrentIndex(2)
    assert win._tabs.currentIndex() == 2
