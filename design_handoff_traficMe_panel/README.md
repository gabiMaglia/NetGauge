# Handoff: traficMe · Panel (Dirección 01)

Rediseño de **Monitor de Consumo de Red → traficMe**: un monitor de tráfico de red de
escritorio. Esta entrega cubre la **Dirección 01 "Panel"**: un dashboard suave, con tarjetas
de métrica, gráfico de ancho de banda en vivo y barras de cuota. Pensado para usuarios caseros,
gamers y perfiles IT. Acento azul. Soporta tema **claro y oscuro**.

## Sobre los archivos de diseño

Los archivos de este paquete son **referencias de diseño hechas en HTML/CSS** — prototipos que
muestran el aspecto y la estructura deseados, **no código para copiar tal cual**. La tarea es
**recrear este diseño en la app existente de Python** (PyQt6 / PySide6, según ya esté el proyecto),
usando widgets nativos de Qt y QSS. No incrustes el HTML en la app.

- `panel_reference.html` — abrir en un navegador. Muestra, en claro y oscuro: la **pantalla
  principal**, el diálogo **Configurar cuota** y la vista **Por aplicación**.
- `palette.py` — todos los tokens (colores por tema, tipografía, radios, espaciado, sombras) y
  una función `app_qss(theme)` con QSS base lista para `app.setStyleSheet(...)`. Importable directo.

## Fidelidad

**Alta fidelidad (hifi).** Colores, tipografía, espaciado y radios son finales. Reprodúcelos con
precisión. Las únicas piezas "vivas" son el gráfico y los números, que vienen del muestreo real
de red de la app.

---

## Stack y estructura sugerida

- **Framework:** PyQt6 o PySide6 (lo que ya use el proyecto). El QSS de `palette.py` sirve para ambos.
- **Ventana sin marco** (`Qt.FramelessWindowHint`) con barra de título propia para lograr el look
  moderno (esquinas redondeadas + sombra). Implementa el arrastre de ventana y los botones
  minimizar / maximizar / cerrar a la derecha.
- **Esquinas redondeadas:** widget raíz con `border-radius: 18px` en QSS + `setAttribute(Qt.WA_TranslucentBackground)`
  en la ventana. La sombra exterior con `QGraphicsDropShadowEffect` (ver `SHADOW` en `palette.py`).
- **Fuente:** "Plus Jakarta Sans". Cargarla con `QFontDatabase.addApplicationFont(...)` (descargar de
  Google Fonts, pesos 400/500/600/700/800) y como fallback la sans del sistema.
- **Gráfico:** dibujar con `QPainter` (paths antialias) o `pyqtgraph`/`QtCharts`. Dos series de área
  con relleno en gradiente + línea de 2.2–2.4px: **bajada** azul, **subida** verde. NO uses imágenes.
- **Tema:** mantén dos diccionarios (`LIGHT`/`DARK` de `palette.py`) y reaplica el QSS al togglear.

---

## Pantallas

### 1) Ventana principal — "Consumo de Red"
Ventana ~786px de ancho (alto según contenido). Estructura vertical:

**a. Barra de título** (alto ~52px, padding 13/18, fondo `titlebar_bg`, borde inferior `hairline`)
- Izquierda: logo (cuadro 26px, radio 8, gradiente `#3b82f6→#2563eb`, ícono de línea ascendente
  en blanco) + "traficMe" (14px/700, "Me" en color acento) + "· Mes actual" (12.5px, `text_faint`).
- Derecha: velocidades en vivo `↓ 8.42 MB/s` (acento) `↑ 1.18 MB/s` (verde), ambos 12.5px/700;
  luego los controles de ventana — minimizar `—`, maximizar (cuadrito), cerrar `✕` (`text_faint`).

**b. Barra de herramientas** (margin-bottom 18)
- **Selector de período** = segmented control. Contenedor `segment_bg`, radio 11, padding 3.
  Chips: "Sesión · Día · Semana · Mes". El activo ("Mes") es una pastilla blanca con sombra suave
  (`0 1px 3px rgba(15,23,42,.12)`), texto `text_strong`/700; inactivos `text_muted`/600. → `QButtonGroup` con botones checkables.
- A la derecha (empujado con stretch): **selector de unidad** pastilla "Auto ▾" (`segment_bg`, radio 9) → `QComboBox`.
- **Botón "Cuota"**: pastilla acento suave (`accent_soft_bg`, borde `accent_soft_bd`, texto
  `accent_strong`/700, ícono de engranaje). Abre el diálogo (pantalla 2).

**c. Pestañas** "Global" / "Por aplicación" (borde inferior `hairline`)
- Activa: acento, 13.5px/700, subrayado de 2px en acento. Inactiva: `text_faint`/600. Cada una con ícono 15px.

**d. Tarjetas de métrica** — grid de 3 columnas, gap 14.
- **Bajada**: card `card_bg`, borde `hairline`, radio 14, padding 15/16. Punto azul 9px + "Bajada"
  (12.5px/600 `text_muted`); número `104.4` (27px/800, letter-spacing -0.5) + "GB" (15px/700 `text_faint`);
  sub "73% del total" (12px/600 `text_faint`).
- **Subida**: igual con punto verde, `38.2 GB`, "27% del total".
- **Σ Total**: card con fondo en gradiente azul claro (`#eff5ff→#e7f0ff`, borde `#d7e6ff`).
  "Σ Total" (12.5px/700 acento); `142.6 GB` (27px/800, "GB" en `#60a5fa`); sub "↑ 12% vs ciclo previo"
  (12px/700 acento). En oscuro: gradiente `#15233a→#142036`, borde `#244468`.

**e. Tarjeta de gráfico** "Ancho de banda en vivo" (`chart_bg`, borde `hairline`, radio 14)
- Cabecera: título (13px/700 `text_strong`) + a la derecha chip "pico 11.7 MB/s" (`segment_bg`, radio 6)
  y leyenda: línea azul 10×3 "Bajada", línea verde "Subida".
- Área del gráfico: 3 líneas de grilla horizontales (`grid_line`). Dos series área+línea (ver "Gráfico" arriba).
  Bajada azul `#3b82f6` (oscuro `#60a5fa`), subida verde `#10b981` (oscuro `#34d399`), relleno en gradiente
  vertical que cae a opacidad 0.

**f. Barras de cuota** (gap 14)
- "Límite diario · hoy" — izq `text_muted`, der "6.8 / 10 GB" (`text`/700). Track `track` alto 9px radio 6,
  relleno **68%** gradiente azul `#3b82f6→#60a5fa`.
- "Límite mensual · este ciclo" — der "142.6 / 200 GB". Relleno **71%** gradiente ámbar `#f59e0b→#fbbf24`
  (señala cercanía al límite). → `QProgressBar` con `::chunk` o widget propio con `QPainter`.

### 2) Diálogo "Configurar cuota"
Modal ~420px. Barra de título: ícono engranaje + "Configurar cuota" (14.5px/700) + `✕`.
Cuerpo padding 20, gap 17, tres campos (cada uno label 12.5px/600 `text_muted` + input):
- "Límite diario (GB · 0 = sin límite)" → input "10.0", sufijo "GB / día". → `QDoubleSpinBox`.
- "Límite mensual (GB · 0 = sin límite)" → input "200.0" en **estado foco**: borde acento +
  halo `0 0 0 3px rgba(59,130,246,.12)`. → `QDoubleSpinBox`.
- "Día de corte del ciclo (1–28)" → input "1". → `QSpinBox` (min 1, max 28).
- Pie: botón "Cancelar" (contorno `input_border`, texto `text_muted`/700) + "Guardar" (primario,
  gradiente `#3b82f6→#2563eb`, texto blanco/700, sombra `0 8px 18px -6px rgba(37,99,235,.6)`).

### 3) Vista "Por aplicación"
Misma ventana con la pestaña "Por aplicación" activa. Lista de filas (gap 6); la primera fila va
resaltada con fondo `row_hover_bg` y radio 12. Cada fila:
- Ícono de app: cuadro 34px radio 9, fondo + letra del mapa `APP_ICONS` en `palette.py`.
- Centro (flex 1): nombre (13.5px/700 `text_strong`) + mini-barra de proporción (alto 5px radio 3,
  track `hairline`, relleno gradiente azul al `pct`).
- Derecha: total "48.2 GB" (14px/800) + split "↓42.6 ↑5.6" (11px/600 `text_faint`).
- Datos de ejemplo en `SAMPLE["apps"]` (Chrome, Steam, Spotify, Windows Update, Discord).

> Nota: en el mockup los nombres de app salen "amigables" (Google Chrome, Steam…). Tú ya tienes la
> lógica para resolver el nombre real desde el PID/ruta del proceso — conéctala aquí.

---

## Interacciones y estados

- **Período / Unidad / Pestañas:** cambian el conjunto de datos mostrado (sesión/día/semana/mes;
  unidad Auto/KB/MB/GB; global vs por app). El activo se marca como en los mocks.
- **Botón Cuota:** abre el diálogo modal (pantalla 2). Guardar persiste límites y día de corte.
- **Gráfico en vivo:** se actualiza periódicamente (p. ej. `QTimer` cada 1 s) desplazando la serie.
- **Hover de fila de app:** fondo `row_hover_bg`, radio 12 (cursor pointer).
- **Barras de cuota:** el color de relleno puede pasar a ámbar/rojo al acercarse/superar el límite
  (mensual ya va ámbar en el mock; >100% sugiero rojo `#ef4444`).
- **Toggle de tema:** reaplica el QSS con el otro diccionario y repinta el gráfico con sus colores.

## Estado necesario
- Período activo, unidad activa, pestaña activa, tema (claro/oscuro).
- Totales subida/bajada/total por período; serie temporal del ancho de banda; pico.
- Config de cuota: `daily_limit_gb`, `monthly_limit_gb`, `cycle_day` (persistir en disco).
- Lista de apps con total + split + nombre resuelto.

## Tokens de diseño
Todos en **`palette.py`** (`LIGHT`, `DARK`, `FONT`, `RADIUS`, `SPACE`, `SHADOW`, `APP_ICONS`,
`SAMPLE`, `app_qss()`). Resumen rápido:
- **Acento:** `#3b82f6` (claro) / `#60a5fa` (oscuro); fuerte `#2563eb`. **Subida:** `#10b981`/`#34d399`.
  **Ámbar cuota:** `#f59e0b→#fbbf24`.
- **Radios:** ventana 18 · card 14 · input/botón 10 · segment 11 · chip/icon 8–9 · barra 6.
- **Tipografía:** Plus Jakarta Sans. Métrica hero 27/800 · títulos 13/700 · cuerpo 13/600 · micro 11/600.

## Assets
- Sin imágenes. Íconos = SVG de trazo sencillo (logo línea ascendente, engranaje, globo, grilla,
  flechas ↓↑). Reimplementar como `QIcon`/SVG o dibujados; o usar un set como Lucide/Feather.
- Íconos de app = cuadro de color + letra (mapa `APP_ICONS`). Si quieres, sustituir por el ícono
  real del ejecutable más adelante.
- Fuente: descargar "Plus Jakarta Sans" de Google Fonts y empaquetarla con la app.

## Archivos de este paquete
- `panel_reference.html` — referencia visual (claro + oscuro, las 3 pantallas).
- `palette.py` — tokens + QSS base, listos para importar en la app PyQt/PySide.
