# tests/test_branding_strings.py
from pathlib import Path

from src.presentation.qt.i18n import _STR

ROOT = Path(__file__).resolve().parent.parent


def test_about_desc_menciona_windows_y_macos_en_todos_los_idiomas():
    for lang in ("es", "en", "pt"):
        desc = _STR[lang]["dlg.about.desc"]
        assert "Windows" in desc and "macOS" in desc, lang


def test_diagnose_dice_netgauge():
    txt = (ROOT / "diagnose.py").read_text(encoding="utf-8")
    assert "Network Monitor" not in txt
    assert "NetGauge" in txt
