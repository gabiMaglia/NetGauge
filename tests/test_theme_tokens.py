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
