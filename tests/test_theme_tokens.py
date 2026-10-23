from src.presentation.qt import theme

REQUIRED = {"down", "upload", "accent", "warning", "danger", "selected_bg",
            "selected_bd", "text", "text_muted", "window_bg", "card_bg", "border"}


def test_both_themes_share_new_keys():
    for t in (theme.DARK, theme.LIGHT):
        assert REQUIRED <= set(t)
    assert set(theme.DARK) == set(theme.LIGHT)


def test_dark_palette_matches_approved_design():
    d = theme.DARK
    assert d["window_bg"] == "#0b0f17"
    assert d["card_bg"] == "#111826"
    assert d["border"] == "#1c2740"
    assert d["accent"] == "#458bf8"
    assert d["down"] == "#5aa9ff"
    assert d["upload"] == "#34d5a3"
    assert d["text_muted"] == "#93a6c1"


def _luminance(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_muted_text_has_aa_contrast_on_cards():
    d = theme.DARK
    assert _contrast(d["text_muted"], d["card_bg"]) >= 4.5
    assert _contrast(d["text_muted"], d["window_bg"]) >= 4.5


def test_font_family_has_no_segoe_on_stack():
    assert "Segoe UI" not in theme.FONT_FAMILY
    assert "JetBrains Mono" in theme.MONO_FAMILY


def test_light_text_has_aa_contrast():
    t = theme.LIGHT
    for fg in ("text", "text_strong", "text_muted", "text_secondary", "accent_text"):
        for bg in ("card_bg", "window_bg"):
            assert _contrast(t[fg], t[bg]) >= 4.5, (fg, bg)


def test_light_semantic_colours_readable_as_text():
    t = theme.LIGHT
    for fg in ("upload", "warning", "down", "total_fg", "total_fg2"):
        assert _contrast(t[fg], t["card_bg"]) >= 4.5, fg
        assert _contrast(t[fg], t["window_bg"]) >= 4.5, fg
    assert _contrast(t["total_fg2"], t["selected_bg"]) >= 4.5
    assert _contrast(t["on_accent"], t["accent"]) >= 4.5   # chip seleccionado


def test_dark_accent_and_secondary_text_contrast():
    t = theme.DARK
    for fg in ("text", "text_secondary", "accent_text"):
        for bg in ("card_bg", "window_bg"):
            assert _contrast(t[fg], t[bg]) >= 4.5, (fg, bg)


def test_load_app_fonts_registers_jetbrains_mono():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from pathlib import Path

    import pytest
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    fonts = Path(theme.__file__).resolve().parents[3] / "assets" / "fonts"
    if not list(fonts.glob("JetBrainsMono-*.ttf")):
        pytest.skip("no hay fuentes bundleadas")
    if QFontDatabase.addApplicationFont(str(next(fonts.glob("JetBrainsMono-*.ttf")))) == -1:
        pytest.skip("la plataforma headless no registra fuentes (addApplicationFont = -1)")
    theme.load_app_fonts()
    assert "JetBrains Mono" in QFontDatabase.families()
    assert "Plus Jakarta Sans" in QFontDatabase.families()
