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
    "text": "#0f172a", "text_strong": "#1e293b", "text_muted": "#5b6b82",
    "text_faint": "#94a3b8", "text_secondary": "#475569",
    "down": "#2563eb", "selected_bg": "#eff5ff", "selected_bd": "#dbe8ff",
    "accent": "#2563eb", "accent_strong": "#1d4ed8", "accent_soft_bg": "#eff5ff",
    "accent_soft_bd": "#dbe8ff", "upload": "#047857", "warning": "#b45309",
    "warning_2": "#fbbf24", "danger": "#ef4444", "on_accent": "#ffffff", "on_danger": "#ffffff",
    "total_grad_a": "#eff5ff", "total_grad_b": "#e7f0ff", "total_grad_bd": "#d7e6ff",
    "shadow_rgba": "rgba(15,23,42,0.32)",
    "dashed_bd": "#cbd5e1", "accent_text": "#2563eb",
    "total_fg": "#1d4ed8", "total_fg2": "#2563eb",
    "table_head_bg": "#f1f4f8", "row_line": "#eef1f5",
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
    "on_accent": "#06101f", "on_danger": "#ffffff", "selected_bg": "#13233f", "selected_bd": "#2a4a85",
    "total_grad_a": "#13233f", "total_grad_b": "#13233f", "total_grad_bd": "#2a4a85",
    "shadow_rgba": "rgba(2,6,23,0.6)",
    "dashed_bd": "#2a3a58", "accent_text": "#8cbcff",
    "total_fg": "#9cc4ff", "total_fg2": "#c7dcff",
    "table_head_bg": "#0e1420", "row_line": "#172036",
}

# Sin "Segoe UI": en macOS Qt avisa del alias; en Windows sans-serif lo resuelve.
FONT_FAMILY = '"Plus Jakarta Sans", "Helvetica Neue", sans-serif'
MONO_FAMILY = '"JetBrains Mono", "Menlo", "Consolas", monospace'

RADIUS = {"window": 18, "card": 14, "input": 10, "button": 10,
          "segment": 11, "chip": 8, "app_icon": 9, "bar": 6}

SPACE = {"window_pad": 20, "card_pad": 16, "gap_cards": 14, "gap_section": 18}


_CHECK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" '
              'viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="3.2" '
              'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7"/></svg>')
_check_dir: str | None = None


def check_icon_url(color: str) -> str:
    """Ruta (para url() del QSS) de la tilde del checkbox en `color`.

    El QSS sólo acepta imágenes de archivo: se escribe un SVG por color en un
    directorio temporal del proceso (se reusa si ya existe)."""
    import atexit
    import shutil
    import tempfile
    from pathlib import Path

    global _check_dir
    if _check_dir is None or not Path(_check_dir).is_dir():
        _check_dir = tempfile.mkdtemp(prefix="netgauge_ui_")
        atexit.register(shutil.rmtree, _check_dir, ignore_errors=True)
    path = Path(_check_dir) / f"check_{color.lstrip('#')}.svg"
    if not path.exists():
        path.write_text(_CHECK_SVG.format(c=color), encoding="utf-8")
    return path.as_posix()


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
    #BrandName {{ font-size: 14px; font-weight: 700; color: {t['text_strong']}; }}
    #SpeedDown {{ font-family: {MONO_FAMILY}; font-size: 20px; font-weight: 700; color: {t['down']}; }}
    #SpeedUp   {{ font-family: {MONO_FAMILY}; font-size: 20px; font-weight: 700; color: {t['upload']}; }}
    #SpeedUnit {{ font-size: 12px; color: {t['text_muted']}; }}
    #TitleSep  {{ background: {t['border']}; }}

    QPushButton#IconBtn, QPushButton#WinBtn {{
        background: transparent; border: none; border-radius: 8px; padding: 0;
    }}
    QPushButton#IconBtn:hover, QPushButton#WinBtn:hover {{ background: {t['segment_bg']}; }}
    QPushButton#WinBtn[class="CloseBtn"]:hover {{ background: {t['danger']}; }}

    /* Fila de navegación */
    #NavRule {{ background: {t['border']}; border: none; }}
    #Segment {{ background: {t['card_bg']}; border: 1px solid {t['border']};
                border-radius: {RADIUS['input']}px; }}
    QPushButton#SegChip {{
        background: transparent; border: none; color: {t['text_muted']};
        font-size: 13px; font-weight: 600; padding: 0 12px; min-height: 30px;
        max-height: 30px; border-radius: 8px;
    }}
    QPushButton#SegChip:checked {{
        background: {t['accent']}; color: {t['on_accent']}; font-weight: 700;
    }}
    #UnitCaption {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}

    /* Combo genérico (ej. idioma en Ajustes) */
    QComboBox {{
        background: {t['input_bg']}; border: 1.5px solid {t['input_border']};
        border-radius: {RADIUS['input']}px; padding: 8px 11px;
        color: {t['text']}; font-weight: 600; min-width: 90px;
    }}
    QComboBox:focus, QComboBox:hover {{ border: 1.5px solid {t['accent']}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}

    QComboBox#UnitBox {{
        background: {t['card_bg']}; border: 1px solid {t['border']};
        border-radius: {RADIUS['input']}px; padding: 0 30px 0 12px;
        min-height: 36px; max-height: 36px;
        color: {t['text']}; font-size: 13px; font-weight: 700; min-width: 56px;
    }}
    QComboBox#UnitBox:focus {{ border: 1px solid {t['accent']}; }}
    QComboBox#UnitBox::drop-down {{ border: none; width: 0; }}
    QComboBox QAbstractItemView {{
        background: {t['window_bg']}; color: {t['text']};
        selection-background-color: {t['accent']}; selection-color: #fff;
        border: 1px solid {t['hairline']}; border-radius: 8px;
        padding: 4px; outline: none;
    }}
    QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 2px 8px; }}

    /* Pestañas */
    QTabBar {{ background: transparent; }}
    QTabBar::tab {{
        background: transparent; color: {t['text_muted']};
        font-size: 14px; font-weight: 600; padding: 0 12px; height: 38px;
        border-bottom: 2px solid transparent; margin-right: 4px;
    }}
    QTabBar::tab:selected {{ color: {t['text_strong']}; font-weight: 700;
                             border-bottom: 2px solid {t['accent']}; }}

    #Card {{ background: {t['card_bg']}; border: 1px solid {t['border']};
             border-radius: {RADIUS['card']}px; }}
    #ChartCard {{ background: {t['chart_bg']}; border: 1px solid {t['border']};
                  border-radius: {RADIUS['card']}px; }}
    #TotalCard {{
        border: 1px solid {t['selected_bd']}; border-radius: {RADIUS['card']}px;
        background: {t['selected_bg']};
    }}
    #Card QLabel, #TotalCard QLabel, #LimitCard QLabel {{ background: transparent; }}

    #MetricName  {{ font-size: 13px; font-weight: 600; color: {t['text_muted']}; }}
    #MetricHero  {{ font-family: {MONO_FAMILY}; font-size: 30px; font-weight: 700;
                    color: {t['text']}; }}
    #MetricUnit  {{ font-size: 13px; font-weight: 600; color: {t['text_muted']}; }}
    #TotalUnit   {{ font-size: 13px; font-weight: 600; color: {t['total_fg']}; }}
    #MetricSub   {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    #TotalName   {{ font-size: 13px; font-weight: 700; color: {t['total_fg']}; }}
    #TotalSub    {{ font-size: 12px; font-weight: 600; color: {t['total_fg2']}; }}
    #MetricTrend {{ font-size: 12px; font-weight: 700; color: {t['text_muted']}; }}
    #MetricTrend[level="up"] {{ color: {t['upload']}; }}
    #MetricTrend[level="down"] {{ color: {t['warning']}; }}
    #TotalCard #MetricTrend[level="flat"] {{ color: {t['total_fg2']}; }}

    #SectionTitle {{ font-size: 14px; font-weight: 700; color: {t['text_strong']}; }}
    #Chip {{ background: {t['track']}; color: {t['text_secondary']};
             border: 1px solid {t['border']}; border-radius: 7px; padding: 3px 8px;
             font-family: {MONO_FAMILY}; font-size: 12px; font-weight: 600; }}
    #LegendText {{ font-size: 12px; font-weight: 600; color: {t['text_secondary']}; }}

    /* Tarjetas de límite */
    #LimitCard {{ background: {t['card_bg']}; border: 1px solid {t['border']};
                  border-radius: {RADIUS['card']}px; }}
    #LimitCard[state="empty"] {{ border: 1px dashed {t['dashed_bd']}; }}
    #LimitTitle {{ font-size: 13px; font-weight: 700; color: {t['text_strong']}; }}
    #LimitValue {{ font-family: {MONO_FAMILY}; font-size: 13px; font-weight: 700;
                   color: {t['accent']}; }}
    #LimitValue[level="warn"] {{ color: {t['warning']}; }}
    #LimitValue[level="danger"] {{ color: {t['danger']}; }}
    #LimitHint {{ font-size: 12px; color: {t['text_muted']}; }}
    QPushButton#LimitDefineBtn {{
        background: transparent; border: 1px solid {t['accent']}; border-radius: 10px;
        color: {t['accent_text']}; font-size: 13px; font-weight: 700; padding: 0 16px;
    }}
    QPushButton#LimitDefineBtn:hover {{ background: {t['selected_bg']}; }}
    QPushButton#LimitEditBtn {{
        background: transparent; border: none; color: {t['accent_text']};
        font-size: 12px; font-weight: 700; padding: 2px 4px;
    }}
    QPushButton#LimitEditBtn:hover {{ text-decoration: underline; }}

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
    #AppRowActive {{ border-radius: 12px; border: 1px solid {t['selected_bd']};
                     background: {t['selected_bg']}; }}
    #AppRowName {{ font-size: 15px; font-weight: 700; color: {t['text_strong']};
                   background: transparent; }}
    #AppConns {{ font-size: 12px; color: {t['text_muted']}; background: transparent; }}
    #AppRate {{ font-family: {MONO_FAMILY}; font-size: 12px; color: {t['text_secondary']};
                background: transparent; }}
    #AppRowTotal {{ font-family: {MONO_FAMILY}; font-size: 15px; font-weight: 700;
                 color: {t['text']}; background: transparent; }}
    #AppRowShare {{ font-size: 12px; font-weight: 600; color: {t['text_muted']};
                    background: transparent; }}

    /* Barra de herramientas de Por aplicación */
    QLineEdit#AppsSearch, QLineEdit#ConnSearch {{
        background: {t['input_bg']}; border: 1px solid {t['input_border']};
        border-radius: {RADIUS['input']}px; padding: 0 12px 0 4px;
        font-size: 13px; font-weight: 500; color: {t['text']};
        placeholder-text-color: {t['text_muted']};
    }}
    QLineEdit#AppsSearch:focus, QLineEdit#ConnSearch:focus {{ border: 1px solid {t['accent']}; }}
    #SortCaption {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    QPushButton#SortChip, QPushButton#StatusChip {{
        background: transparent; border: 1px solid {t['border']}; border-radius: 16px;
        color: {t['text_muted']}; font-size: 12px; font-weight: 600; padding: 0 12px;
    }}
    QPushButton#SortChip:hover, QPushButton#StatusChip:hover {{ border: 1px solid {t['accent_soft_bd']}; }}
    QPushButton#SortChip:focus, QPushButton#StatusChip:focus {{ border: 1px solid {t['accent']}; }}
    QPushButton#SortChip:checked, QPushButton#StatusChip:checked {{
        background: {t['selected_bg']}; border: 1px solid {t['accent']};
        color: {t['accent_text']}; font-weight: 700;
    }}
    #AppsHeader QLabel {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    #AppsEmpty {{ font-size: 13px; color: {t['text_muted']}; }}

    /* Checkbox con indicador propio (el nativo se ve blanco en oscuro) */
    QCheckBox {{ font-size: 13px; font-weight: 600; color: {t['text_secondary']};
                 spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border-radius: 6px;  /* + borde 1px = 20x20 */
        border: 1px solid {t['dashed_bd']}; background: transparent;
    }}
    QCheckBox::indicator:checked {{
        background: {t['accent']}; border: 1px solid {t['accent']};
        image: url("{check_icon_url(t['on_accent'])}");
    }}

    /* Pestaña Conexiones */
    #ConnCard {{ background: {t['card_bg']}; border: 1px solid {t['border']};
                 border-radius: {RADIUS['card']}px; }}
    #ConnHead {{ background: {t['table_head_bg']};
                 border: none; border-bottom: 1px solid {t['border']};
                 border-top-left-radius: {RADIUS['card'] - 1}px;
                 border-top-right-radius: {RADIUS['card'] - 1}px; }}
    #ConnHead QLabel {{ font-size: 12px; font-weight: 700; color: {t['text_muted']};
                        background: transparent; }}
    #ConnScroll, #ConnScroll > QWidget > QWidget, #ConnContainer {{
        background: transparent; }}
    #ConnRow {{ background: transparent; border: none;
                border-bottom: 1px solid {t['row_line']}; }}
    #ConnRow QLabel {{ background: transparent; }}
    #ConnApp {{ font-size: 13px; font-weight: 700; color: {t['text_strong']}; }}
    #ConnEndpoint {{ font-family: {MONO_FAMILY}; font-size: 12px; color: {t['text_secondary']}; }}
    #ConnCountry {{ font-size: 13px; font-weight: 600; color: {t['text']}; }}
    #ConnStatus {{ font-size: 12px; font-weight: 600; color: {t['text_muted']}; }}
    #ConnStatus[kind="established"] {{ color: {t['upload']}; }}
    #ConnStatus[kind="closing"] {{ color: {t['warning']}; }}
    /* '#ConnRow #ConnDot' gana por id sobre '#ConnRow QLabel' (que pone fondo transparente) */
    #ConnRow #ConnDot {{ background: {t['text_muted']}; border-radius: 3px; }}
    #ConnRow #ConnDot[kind="established"] {{ background: {t['upload']}; }}
    #ConnRow #ConnDot[kind="closing"] {{ background: {t['warning']}; }}
    #ConnTraffic {{ font-family: {MONO_FAMILY}; font-size: 12px; font-weight: 700;
                    color: {t['text_muted']}; }}
    #ConnEmpty {{ background: transparent; border: 1px dashed {t['dashed_bd']};
                  border-radius: {RADIUS['card']}px; }}
    #ConnEmpty QLabel {{ background: transparent; }}
    #ConnEmptyTile {{ background: {t['card_bg']}; border: 1px solid {t['border']};
                      border-radius: 12px; }}
    #ConnEmptyTitle {{ font-size: 14px; font-weight: 700; color: {t['text_strong']}; }}
    #ConnEmptyBody {{ font-size: 12px; color: {t['text_muted']}; }}

    /* Barra de estado */
    #StatusBar {{ background: {t['window_bg']}; border-top: 1px solid {t['border']};
                  border-bottom-left-radius: {RADIUS['window'] - 1}px;
                  border-bottom-right-radius: {RADIUS['window'] - 1}px; }}
    #StatusText, #StatusRight {{ font-size: 12px; color: {t['text_muted']};
                                 background: transparent; }}

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
    """Registra las fuentes bundleadas (Plus Jakarta Sans, JetBrains Mono).

    Se hace en runtime para no depender de que el SO las tenga instaladas
    (en macOS no vienen de fábrica).

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
