"""Opt-out del chequeo de actualizaciones: decisión pura + checkbox del diálogo."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.domain.models import Settings  # noqa: E402
from src.presentation.qt.app import should_check_updates  # noqa: E402
from src.presentation.qt.i18n import _STR  # noqa: E402
from src.presentation.qt.settings_dialog import SettingsDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_should_check_updates_on_by_default():
    assert should_check_updates(Settings()) is True


def test_should_check_updates_off_when_disabled():
    assert should_check_updates(Settings(check_updates=False)) is False


def test_should_check_updates_reads_current_value_each_call():
    s = Settings()
    s.check_updates = False
    assert should_check_updates(s) is False
    s.check_updates = True
    assert should_check_updates(s) is True


@pytest.mark.parametrize("lang", sorted(_STR))
def test_update_hint_mentions_github_api(lang):
    assert "api.github.com" in _STR[lang]["dlg.settings.updates_hint"]


@pytest.mark.parametrize("value", [True, False])
def test_dialog_checkbox_reflects_setting(qapp, value):
    dlg = SettingsDialog(Settings(check_updates=value))
    assert dlg._updates.isChecked() is value


def test_dialog_saves_unchecked_checkbox(qapp):
    dlg = SettingsDialog(Settings())
    dlg._updates.setChecked(False)
    assert dlg.result_settings().check_updates is False
