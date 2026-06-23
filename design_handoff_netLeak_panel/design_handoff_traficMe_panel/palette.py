"""
traficMe · Panel — paleta y tokens de diseño
Dirección 01 (Panel). Tema claro + oscuro.

Uso sugerido en PyQt/PySide:
    from palette import LIGHT, DARK, FONT, RADIUS, app_qss
    qss = app_qss(LIGHT)          # o DARK
    app.setStyleSheet(qss)

Todos los colores son hex de 6 dígitos. Las medidas están en px.
"""

# ----------------------------------------------------------------------
# COLORES POR TEMA
# ----------------------------------------------------------------------
LIGHT = {
    # superficies
    "app_bg":        "#e4e8ee",   # fondo del escritorio / detrás de la ventana
    "window_bg":     "#ffffff",   # fondo de la ventana
    "titlebar_bg":   "#fbfcfe",   # barra de título y cabeceras
    "card_bg":       "#f8fafc",   # tarjetas de métrica
    "chart_bg":      "#fbfcfe",   # contenedor del gráfico
    "input_bg":      "#ffffff",
    "segment_bg":    "#f1f4f8",   # fondo del control de período / select
    "row_hover_bg":  "#f8fafc",   # fila de app resaltada
    # bordes y líneas
    "border":        "#e7ebf0",   # borde de ventana
    "hairline":      "#eef1f5",   # separadores, bordes de tarjeta
    "input_border":  "#e3e8ef",
    "grid_line":     "#eef1f5",   # líneas de la grilla del gráfico
    "track":         "#eef1f5",   # fondo de barras de progreso
    # texto
    "text":          "#0f172a",   # primario
    "text_strong":   "#1e293b",
    "text_muted":    "#64748b",   # secundario
    "text_faint":    "#94a3b8",   # terciario / hint
    # marca y acentos
    "accent":        "#3b82f6",   # azul primario (marca, bajada, activo)
    "accent_strong": "#2563eb",   # azul fuerte (botón, hover)
    "accent_soft_bg":"#eff5ff",   # fondo de botón "Cuota" / total
    "accent_soft_bd":"#dbe8ff",
    "upload":        "#10b981",   # verde (subida)
    "warning":       "#f59e0b",   # ámbar (barra mensual)
    "warning_2":     "#fbbf24",
    "on_accent":     "#ffffff",
}

DARK = {
    "app_bg":        "#0b1220",
    "window_bg":     "#0d1117",
    "titlebar_bg":   "#10161f",
    "card_bg":       "#141a22",
    "chart_bg":      "#10151c",
    "input_bg":      "#0d1117",
    "segment_bg":    "#161b22",
    "row_hover_bg":  "#141a22",
    "border":        "#1e2530",
    "hairline":      "#1b222d",
    "input_border":  "#1e2530",
    "grid_line":     "#1a212b",
    "track":         "#1a212b",
    "text":          "#e6edf6",
    "text_strong":   "#e6edf6",
    "text_muted":    "#93a4b8",
    "text_faint":    "#5b6b80",
    "accent":        "#60a5fa",   # azul aclarado para fondo oscuro
    "accent_strong": "#3b82f6",
    "accent_soft_bg":"#16263f",
    "accent_soft_bd":"#244468",
    "upload":        "#34d399",
    "warning":       "#f59e0b",
    "warning_2":     "#fbbf24",
    "on_accent":     "#ffffff",
}

# Colores de íconos de app (mismos en ambos temas; ajustar fondo si hace falta)
APP_ICONS = {
    "Google Chrome":  {"bg": "#fef0e6", "fg": "#ea7c3c", "letter": "C"},
    "Steam":          {"bg": "#e7f0ff", "fg": "#2563eb", "letter": "S"},
    "Spotify":        {"bg": "#e6f7ee", "fg": "#10b981", "letter": "♪"},
    "Windows Update": {"bg": "#eef1f5", "fg": "#64748b", "letter": "⊞"},
    "Discord":        {"bg": "#ecebfe", "fg": "#6366f1", "letter": "D"},
}

# ----------------------------------------------------------------------
# TIPOGRAFÍA  (Plus Jakarta Sans; fallback al sans del sistema)
# ----------------------------------------------------------------------
FONT = {
    "family":        "Plus Jakarta Sans",
    "hero_metric":   {"size": 27, "weight": 800, "spacing": -0.5},  # 104.4 GB
    "section_title": {"size": 13, "weight": 700},                   # "Ancho de banda en vivo"
    "tab":           {"size": 14, "weight": 700},
    "body":          {"size": 13, "weight": 600},
    "label":         {"size": 13, "weight": 600},   # labels del form
    "caption":       {"size": 12, "weight": 600},   # "73% del total"
    "micro":         {"size": 11, "weight": 600},   # leyendas, ↓42.6 ↑5.6
    "button":        {"size": 14, "weight": 700},
}

# ----------------------------------------------------------------------
# FORMA / ESPACIADO
# ----------------------------------------------------------------------
RADIUS = {
    "window":  18,
    "card":    14,
    "input":   10,
    "button":  10,
    "segment": 11,   # contenedor; chips internos 8
    "chip":    8,
    "app_icon":9,
    "bar":     6,    # barras de progreso / track
}

SPACE = {
    "window_pad":   20,   # padding del cuerpo de la ventana
    "card_pad":     16,
    "gap_cards":    14,
    "gap_section":  18,
    "titlebar_pad": (13, 18),  # (vertical, horizontal)
}

# Sombra de ventana (para QGraphicsDropShadowEffect):
#   blur=70, dx=0, dy=30, color=rgba(15,23,42,0.32) en claro  /  rgba(2,6,23,0.6) en oscuro
SHADOW = {
    "light": {"blur": 70, "dx": 0, "dy": 30, "rgba": (15, 23, 42, 82)},
    "dark":  {"blur": 70, "dx": 0, "dy": 30, "rgba": (2, 6, 23, 153)},
}

# ----------------------------------------------------------------------
# Datos de ejemplo (los mismos del mockup)
# ----------------------------------------------------------------------
SAMPLE = {
    "period": "Mes",
    "download_gb": 104.4,
    "upload_gb": 38.2,
    "total_gb": 142.6,
    "speed_down": "8.42 MB/s",
    "speed_up": "1.18 MB/s",
    "peak": "11.7 MB/s",
    "daily_limit_gb": 10.0,
    "daily_used_gb": 6.8,
    "monthly_limit_gb": 200.0,
    "monthly_used_gb": 142.6,
    "cycle_day": 1,
    "apps": [
        {"name": "Google Chrome",  "total_gb": 48.2, "down": 42.6, "up": 5.6, "pct": 88},
        {"name": "Steam",          "total_gb": 31.5, "down": 30.9, "up": 0.6, "pct": 58},
        {"name": "Spotify",        "total_gb": 12.1, "down": 12.0, "up": 0.1, "pct": 24},
        {"name": "Windows Update", "total_gb": 9.7,  "down": 9.7,  "up": 0.0, "pct": 18},
        {"name": "Discord",        "total_gb": 6.3,  "down": 4.1,  "up": 2.2, "pct": 11},
    ],
}


def app_qss(t: dict) -> str:
    """Devuelve una hoja QSS base para el tema `t` (LIGHT o DARK).
    Es un punto de partida — los widgets de métrica/gráfico se estilizan aparte.
    """
    return f"""
    QWidget {{
        background: {t['window_bg']};
        color: {t['text']};
        font-family: "{FONT['family']}";
        font-size: 13px;
    }}
    QFrame#Card {{
        background: {t['card_bg']};
        border: 1px solid {t['hairline']};
        border-radius: {RADIUS['card']}px;
    }}
    QFrame#TitleBar {{
        background: {t['titlebar_bg']};
        border-bottom: 1px solid {t['hairline']};
    }}
    /* Botón Cuota (acento suave) */
    QPushButton#QuotaBtn {{
        background: {t['accent_soft_bg']};
        border: 1px solid {t['accent_soft_bd']};
        color: {t['accent_strong']};
        border-radius: {RADIUS['button']}px;
        padding: 7px 13px;
        font-weight: 700;
    }}
    /* Botón primario (Guardar) */
    QPushButton#PrimaryBtn {{
        background: {t['accent_strong']};
        color: {t['on_accent']};
        border: none;
        border-radius: {RADIUS['button']}px;
        padding: 11px 18px;
        font-weight: 700;
    }}
    QPushButton#PrimaryBtn:hover {{ background: {t['accent']}; }}
    /* Inputs */
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background: {t['input_bg']};
        border: 1.5px solid {t['input_border']};
        border-radius: {RADIUS['input']}px;
        padding: 10px 12px;
        color: {t['text']};
        font-weight: 600;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1.5px solid {t['accent']};
    }}
    /* Barras de progreso */
    QProgressBar {{
        background: {t['track']};
        border: none;
        border-radius: {RADIUS['bar']}px;
        max-height: 9px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {t['accent']};
        border-radius: {RADIUS['bar']}px;
    }}
    """
