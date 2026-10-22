"""Tokens de diseño (NetGauge · Panel) + generador de QSS para PySide6.

Vendoreado desde design_handoff_traficMe_panel/palette.py para que la app
no dependa de la carpeta de handoff. Tema claro y oscuro.
"""
from __future__ import annotations

LIGHT = {
    "is_dark": False,
    "app_bg": "#e4e8ee", "window_bg": "#ffffff", "titlebar_bg": "#fbfcfe",
    "card_bg": "#f8fafc", "chart_bg": "#fbfcfe", "input_bg": "#ffffff",
    "segment_bg": "#f1f4f8", "row_hover_bg": "#f8fafc",
    "border": "#e7ebf0", "hairline": "#eef1f5", "input_border": "#e3e8ef",
    "grid_line": "#eef1f5", "track": "#eef1f5",
    "text": "#0f172a", "text_strong": "#1e293b", "text_muted": "#64748b",
    "text_faint": "#94a3b8", "text_secondary": "#475569",
    "down": "#2563eb", "selected_bg": "#eff5ff", "selected_bd": "#dbe8ff",
    "accent": "#3b82f6", "accent_strong": "#2563eb", "accent_soft_bg": "#eff5ff",
    "accent_soft_bd": "#dbe8ff", "upload": "#10b981", "warning": "#f59e0b",
    "warning_2": "#fbbf24", "danger": "#ef4444", "on_accent": "#ffffff",
    "total_grad_a": "#eff5ff", "total_grad_b": "#e7f0ff", "total_grad_bd": "#d7e6ff",
    "shadow_rgba": "rgba(15,23,42,0.32)",
}

DARK = {
    "is_dark": True,
    "app_bg": "#0b0f17", "window_bg": "#0b0f17", "titlebar_bg": "#0b0f17",
    "card_bg": "#111826", "chart_bg": "#111826", "input_bg": "#111826",
    "segment_bg": "#111826", "row_hover_bg": "#111826",
    "border": "#1c2740", "hairline": "#1c2740", "input_border": "#1c2740",
    "grid_line": "#1c2740", "track": "#0b0f17",
    "text": "#eaf1fb", "text_strong": "#eaf1fb", "text_muted": "#93a6c1",
    "text_faint": "#93a6c1", "text_secondary": "#c3d0e2",
    "accent": "#458bf8", "accent_strong": "#458bf8", "accent_soft_bg": "#13233f",
    "accent_soft_bd": "#2a4a85", "down": "#5aa9ff", "upload": "#34d5a3",
    "warning": "#f5b942", "warning_2": "#f5b942", "danger": "#ef4444",
    "on_accent": "#06101f", "selected_bg": "#13233f", "selected_bd": "#2a4a85",
    "total_grad_a": "#13233f", "total_grad_b": "#13233f", "total_grad_bd": "#2a4a85",
    "shadow_rgba": "rgba(2,6,23,0.6)",
}

APP_ICONS = {
    "Google Chrome": {"bg": "#fef0e6", "fg": "#ea7c3c", "letter": "C"},
    "Steam": {"bg": "#e7f0ff", "fg": "#2563eb", "letter": "S"},
    "Spotify": {"bg": "#e6f7ee", "fg": "#10b981", "letter": "♪"},
    "Windows Update": {"bg": "#eef1f5", "fg": "#64748b", "letter": "⊞"},
    "Discord": {"bg": "#ecebfe", "fg": "#6366f1", "letter": "D"},
}

# Sin "Segoe UI": en macOS Qt avisa del alias; en Windows sans-serif lo resuelve.
FONT_FAMILY = '"Plus Jakarta Sans", "Helvetica Neue", sans-serif'
MONO_FAMILY = '"JetBrains Mono", "Menlo", "Consolas", monospace'

RADIUS = {"window": 18, "card": 14, "input": 10, "button": 10,
          "segment": 11, "chip": 8, "app_icon": 9, "bar": 6}

SPACE = {"window_pad": 20, "card_pad": 16, "gap_cards": 14, "gap_section": 18}


def app_qss(t: dict) -> str:
    return f"""
    QWidget {{
        color: {t['text']};
        font-family: {FONT_FAMILY};
        font-size: 13px;
    }}
    #Root {{
        background: {t['window_bg']};
        border: 1px solid {t['border']};
        border-radius: {RADIUS['window']}px;
    }}
    #TitleBar {{
        background: {t['titlebar_bg']};
        border-bottom: 1px solid {t['hairline']};
        border-top-left-radius: {RADIUS['window']}px;
        border-top-right-radius: {RADIUS['window']}px;
    }}
    #Body {{ background: {t['window_bg']};
             border-bottom-left-radius: {RADIUS['window']}px;
             border-bottom-right-radius: {RADIUS['window']}px; }}
    #Logo {{ border-radius: 8px; }}
    #BrandName {{ font-size: 14px; font-weight: 700; color: {t['text_strong']}; }}
    #BrandSub  {{ font-size: 12px; color: {t['text_faint']}; }}
    #SpeedDown {{ font-size: 12px; font-weight: 700; color: {t['accent']}; }}
    #SpeedUp   {{ font-size: 12px; font-weight: 700; color: {t['upload']}; }}

    QPushButton#WinBtn {{
        background: transparent; border: none; color: {t['text_faint']};
        font-size: 14px; padding: 2px 8px; border-radius: 6px;
    }}
    QPushButton#WinBtn:hover {{ background: {t['segment_bg']}; color: {t['text']}; }}
    QPushButton#CloseBtn:hover {{ background: {t['danger']}; color: #fff; }}

    /* Segmented (período) */
    #Segment {{ background: {t['segment_bg']}; border-radius: {RADIUS['segment']}px; }}
    QPushButton#SegChip {{
        background: transparent; border: none; color: {t['text_muted']};
        font-size: 12px; font-weight: 600; padding: 7px 15px; border-radius: 8px;
    }}
    QPushButton#SegChip:checked {{
        background: {t['window_bg']}; color: {t['text_strong']}; font-weight: 700;
    }}

    /* Combo genérico (ej. idioma en Ajustes) */
    QComboBox {{
        background: {t['input_bg']}; border: 1.5px solid {t['input_border']};
        border-radius: {RADIUS['input']}px; padding: 8px 11px;
        color: {t['text']}; font-weight: 600; min-width: 90px;
    }}
    QComboBox:focus, QComboBox:hover {{ border: 1.5px solid {t['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}

    QComboBox#UnitBox {{
        background: {t['segment_bg']}; border: none; border-radius: 9px;
        padding: 6px 12px; color: {t['text']}; font-weight: 600; min-width: 64px;
    }}
    QComboBox#UnitBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {t['window_bg']}; color: {t['text']};
        selection-background-color: {t['accent']}; selection-color: #fff;
        border: 1px solid {t['hairline']}; border-radius: 8px;
        padding: 4px; outline: none;
    }}
    QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 2px 8px; }}

    QPushButton#QuotaBtn {{
        background: {t['accent_soft_bg']}; border: 1px solid {t['accent_soft_bd']};
        color: {t['accent_strong']}; border-radius: {RADIUS['button']}px;
        padding: 7px 14px; font-weight: 700;
    }}

    /* Tabs */
    QTabWidget::pane {{ border: none; }}
    QTabBar {{ background: transparent; }}
    QTabBar::tab {{
        background: transparent; color: {t['text_faint']};
        font-size: 13px; font-weight: 600; padding: 9px 14px 11px;
        border-bottom: 2px solid transparent; margin-right: 6px;
    }}
    QTabBar::tab:selected {{ color: {t['accent']}; font-weight: 700;
                             border-bottom: 2px solid {t['accent']}; }}

    #Card {{ background: {t['card_bg']}; border: 1px solid {t['hairline']};
             border-radius: {RADIUS['card']}px; }}
    #ChartCard {{ background: {t['chart_bg']}; border: 1px solid {t['hairline']};
                  border-radius: {RADIUS['card']}px; }}
    #TotalCard {{
        border: 1px solid {t['total_grad_bd']}; border-radius: {RADIUS['card']}px;
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {t['total_grad_a']}, stop:1 {t['total_grad_b']});
    }}

    #MetricName  {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    #MetricHero  {{ font-size: 27px; font-weight: 800; color: {t['text']}; }}
    #MetricUnit  {{ font-size: 15px; font-weight: 700; color: {t['text_faint']}; }}
    #MetricSub   {{ font-size: 12px; font-weight: 600; color: {t['text_faint']}; }}
    #TotalName   {{ font-size: 12px; font-weight: 700; color: {t['accent']}; }}
    #TotalSub    {{ font-size: 12px; font-weight: 700; color: {t['accent']}; }}

    #SectionTitle {{ font-size: 13px; font-weight: 700; color: {t['text_strong']}; }}
    #Chip {{ background: {t['segment_bg']}; color: {t['text_muted']};
             border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 600; }}
    #LegendText {{ font-size: 11px; font-weight: 600; color: {t['text_muted']}; }}
    #QuotaLabel {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    #QuotaValue {{ font-size: 12px; font-weight: 700; color: {t['text']}; }}

    /* Vista Por aplicación: el viewport del scroll es blanco por defecto;
       hay que pintarlo con el fondo de la ventana o el texto claro se pierde. */
    QScrollArea {{ background: {t['window_bg']}; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: {t['window_bg']}; }}
    #AppsContainer {{ background: {t['window_bg']}; }}

    /* Scrollbar fina y temática (la default rompía el diseño en oscuro). */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px 2px 2px 0; }}
    QScrollBar::handle:vertical {{ background: {t['input_border']};
        border-radius: 5px; min-height: 36px; }}
    QScrollBar::handle:vertical:hover {{ background: {t['text_faint']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{ height: 0; background: transparent; }}

    /* Filas de app */
    #AppRow {{ background: transparent; border: 1px solid transparent;
               border-radius: 12px; }}
    #AppRow:hover {{ background: {t['card_bg']}; border: 1px solid {t['hairline']}; }}
    #AppRowActive {{ border-radius: 12px;
        border: 1px solid {t['accent_soft_bd']};
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {t['accent_soft_bg']}, stop:1 {t['card_bg']}); }}
    #AppName {{ font-size: 13.5px; font-weight: 700; color: {t['text_strong']}; }}
    #AppTotal {{ font-size: 14px; font-weight: 800; color: {t['text']}; }}
    #AppSplit {{ font-size: 11px; font-weight: 600; color: {t['text_muted']}; }}

    /* Diálogo */
    QDialog {{ background: {t['window_bg']}; }}
    #DlgTitle {{ font-size: 14px; font-weight: 700; color: {t['text_strong']}; }}
    #FieldLabel {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background: {t['input_bg']}; border: 1.5px solid {t['input_border']};
        border-radius: {RADIUS['input']}px; padding: 9px 11px;
        color: {t['text']}; font-weight: 600;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1.5px solid {t['accent']};
    }}
    QPushButton#GhostBtn {{
        background: transparent; border: 1.5px solid {t['input_border']};
        color: {t['text_muted']}; border-radius: {RADIUS['button']}px;
        padding: 10px 18px; font-weight: 700;
    }}
    QPushButton#PrimaryBtn {{
        border: none; border-radius: {RADIUS['button']}px; padding: 11px 20px;
        color: {t['on_accent']}; font-weight: 700;
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {t['accent']}, stop:1 {t['accent_strong']});
    }}
    QPushButton#PrimaryBtn:hover {{ background: {t['accent_strong']}; }}
    """


def load_app_fonts() -> None:
    """Registra las fuentes bundleadas (Plus Jakarta Sans, JetBrains Mono) en runtime para no
    depender de que el SO las tenga instaladas (en macOS no vienen de fábrica).

    Best-effort: si el directorio de fuentes no está, no rompe el arranque.
    Llamar UNA vez después de crear la QApplication y antes de aplicar el QSS.
    Resuelve la ruta tanto en dev (repo) como empaquetado (PyInstaller _MEIPASS).
    """
    import sys
    from pathlib import Path

    base = getattr(sys, "_MEIPASS", None)
    fonts_dir = (
        Path(base) / "assets" / "fonts" if base
        else Path(__file__).resolve().parents[3] / "assets" / "fonts"
    )
    if not fonts_dir.is_dir():
        return
    from PySide6.QtGui import QFontDatabase
    for pattern in ("PlusJakartaSans-*.ttf", "JetBrainsMono-*.ttf"):
        for ttf in sorted(fonts_dir.glob(pattern)):
            QFontDatabase.addApplicationFont(str(ttf))
