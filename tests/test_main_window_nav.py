"""Estructura de la fila de navegación (pestañas + período + unidad); corre offscreen en cualquier SO."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QFrame, QLabel  # noqa: E402

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


def _row_item_containing(row, widget):
    """Índice del ítem de la fila que es `widget` o lo contiene (-1 si ninguno)."""
    for i in range(row.count()):
        w = row.itemAt(i).widget()
        if w is not None and (w is widget or w.isAncestorOf(widget)):
            return i
    return -1


def test_tabbar_period_and_unit_in_nav_row(win):
    row = win._nav_row
    bar_i = _row_item_containing(row, win._tabs.bar)
    seg_i = _row_item_containing(row, win._seg_group.buttons()[0])
    unit_i = _row_item_containing(row, win._unit_box)
    assert 0 <= bar_i < seg_i < unit_i
    assert len(win._seg_group.buttons()) == 4


def _geo_in_body(win, widget):
    return widget.mapTo(win.findChild(QFrame, "Body"), widget.rect().topLeft()), widget.size()


def test_nav_geometry_stable_across_tab_switches(win):
    win.show()
    app = QApplication.instance()
    app.processEvents()
    seg = win._seg_group.buttons()[0].parent()
    rule = win.findChild(QFrame, "NavRule")
    for idx in (0, 1, 2, 0):
        win._tabs.setCurrentIndex(idx)
        app.processEvents()
        bar = win._tabs.bar
        pos, size = _geo_in_body(win, bar)
        assert (pos.x(), pos.y()) == (20, 14)
        bar_rect = QRect(pos, size)
        seg_pos, seg_size = _geo_in_body(win, seg)
        assert not bar_rect.intersects(QRect(seg_pos, seg_size))
        rule_y = rule.mapTo(win.findChild(QFrame, "Body"), rule.rect().topLeft()).y()
        # la pestaña apoya su subrayado sobre la línea divisoria
        assert bar_rect.bottom() + 1 == rule_y
        page = win._tabs.stack.currentWidget()
        page_y = page.mapTo(win.findChild(QFrame, "Body"), page.rect().topLeft()).y()
        assert 0 <= page_y - (rule_y + 1) <= 20


def test_narrow_saved_geometry_is_raised_to_minimum():
    app = QApplication.instance() or QApplication([])
    m = MonitorService(FakeCapture(), FakeRepo(), FakeReporter(),
                       FakeStore(Settings(window_geometry="50,50,500,600")),
                       FakeNotifier())
    w = MainWindow(m, per_process=True)
    w.show()
    app.processEvents()
    assert w.width() >= 680
    w.close()


def test_unit_caption_and_tabs_still_switch(win):
    caps = [lb for lb in win.findChildren(QLabel) if lb.objectName() == "UnitCaption"]
    assert len(caps) == 1 and caps[0].text() == "Unidad"
    win._tabs.setCurrentIndex(2)
    assert win._tabs.currentIndex() == 2
