# Backlog — NetGauge

> Estados: Backlog → To Do → En progreso → En revisión QA → Done | Bloqueado
> Solo nerv-qa escribe "Done". Mapear SIEMPRE el ID externo si existe.
> Niv (P-11, nivel de revisión QA): A=Advisory (default) · S=Strong · X=Adversarial.

## Sprint 0 — Intake + investigación de bug reportado
| ID | Ext (ADO/Jira) | Tarea | Asignado | Estado | Niv | Criterios de aceptación | Rama |
|----|----------------|-------|----------|--------|-----|--------------------------|------|
| T-013 | — | Ventana sin controles de header (mover/resize/cerrar/minimizar) en Windows 11 de otra PC; funciona OK en la PC del PO | nerv-desktop | Done | A | El header permite mover/resize/cerrar/minimizar la ventana en ambas máquinas Windows 11; identificar causa raíz (flags de ventana, frameless custom, DPI/escala, instalador) | main (commit 764b188, sin PR) |
| T-014 | — | Feedback visual de VirusTotal insuficiente: el estado del check (settings_dialog.py:53) solo se ve completo con hover; no hay indicio de si una app fue analizada por VT ni si la conexión/API key funciona | nerv-desktop | Done | A | (1) Badge junto al indicador de confianza por proceso que se coloree cuando esa app fue analizada por VT (usar vt_malicious/vt_total ya presentes en TrustInfo); (2) LED/indicador de estado de conexión con VirusTotal en Settings (válido/inválido/sin probar — requiere alguna forma de testear la key sin esperar a la próxima evaluación de proceso); (3) link clickeable en Settings a la página de registro de VirusTotal (https://www.virustotal.com/gui/join-us) para que el usuario consiga su propia API key | fix/T-014-vt-feedback |

## Sprint 1 — Marketing / Landing page
| ID | Ext (ADO/Jira) | Tarea | Asignado | Estado | Niv | Criterios de aceptación | Rama |
|----|----------------|-------|----------|--------|-----|--------------------------|------|
| T-015 | — | Landing page one-page (responsive, mobile-first) para NetGauge; objetivo #1 descargar, #2 confianza (privacidad + open source) | nerv-web | En progreso | S | Ver detalle completo en §T-015 (abajo) | feature/T-015-landing-page |
| T-016 | — | Rename completo de la app trafficMe → NetGauge (código, instaladores, nombres de archivo, workflows, URLs, engram) | nerv-orquestador | En progreso | S | Ver detalle en §T-016 (abajo) | feature/T-016-rename-netgauge (stack sobre T-015) |
| T-017 | — | Migración de historial trafficMe → NetGauge al actualizar (resuelve el caveat de pérdida de datos del rename) | nerv-orquestador | En revisión QA | S | Al primer arranque, si el dir NetGauge está limpio y existe el dir trafficMe con datos, copiar usage.db/settings.json/monitor.log/reports/. Idempotente, copia (no mueve), nunca rompe el arranque. Tests. | feature/T-017-data-migration (stack sobre T-016) |
| T-018 | — | Landing pixel-perfect contra `design_handoff_netLeak_panel/NetGauge Landing.dc.html` (reemplaza la interpretación previa de T-015) | nerv-orquestador (port directo) | En revisión QA | S | Reproducir el diseño 1:1 (acento #22d3ee, Plus Jakarta Sans + JetBrains Mono, mock de ventana, sparklines, reveal/contador/detección SO). URLs → NetGauge. Build limpio. | feature/T-018-landing-pixel-perfect (stack sobre T-017) |
| T-019 | — | Segundo rename: NetLeak → **NetGauge** (toda la app), por cambio de marca del PO | nerv-orquestador | En revisión QA | S | 0 ocurrencias exactas de NetLeak/netleak en trackeados (se preserva `design_handoff_netLeak_panel`, carpeta real); legacy de migración sigue siendo trafficMe (NetLeak nunca se publicó); pytest+build verdes; URLs → gabiMaglia/NetGauge | feature/T-019-rename-netgauge (stack sobre T-018) |

## Sprint 2 — Landing: i18n + ícono
| ID | Ext (ADO/Jira) | Tarea | Asignado | Estado | Niv | Criterios de aceptación | Rama |
|----|----------------|-------|----------|--------|-----|--------------------------|------|
| T-020 | — | i18n de la landing: traducir a inglés y portugués (base español) con switcher de idioma | nerv-web | En revisión QA | S | Ver §T-020 | feature/T-020-landing-i18n (sobre main) |
| T-021 | — | Unificar el ícono de la landing con el real de la app (3 barras, gradiente azul) en todos lados | nerv-web | En revisión QA | A | Ver §T-021 | feature/T-020-landing-i18n |
| T-022 | — | Cambiar el accent de la landing a azul #458BF8 (alineado al ícono) + armonizar paleta compatible en toda la landing | nerv-orquestador | En revisión QA | A | Accent primario = #458BF8 en toda la landing (reemplaza el cian #22d3ee y sus rgba/tonos derivados); paleta de soporte armonizada a azul y cohesiva; verde (ok/subida) y ámbar/rojo (cuota) se mantienen (semánticos); ícono ya es azul, queda igual; build+lint limpios | feature/T-020-landing-i18n |

## §T-020 · i18n landing (ES/EN/PT)
**Estado:** En progreso · **Tech Lead:** nerv-web · **Rama:** `feature/T-020-landing-i18n` (sobre main) · **Niv QA:** Strong · Pedido PO 2026-06-23.
**Alcance:** la landing hoy está solo en español (`landing/src/landing.html` inyectado como innerHTML + runtime en `App.tsx`). Sumar **inglés y portugués (Brasil)**.
**Criterios de aceptación:**
1. **Todo** el texto visible traducible a ES/EN/PT: header/nav, hero (incl. H1 con el span "comiendo"), micro-line, badges de confianza, problema (antes/después), las 6 features (título+desc), cómo funciona (3 pasos + tray mock label), privacidad (incl. los 3 bullets y "en tu equipo / 0 servidores"), avanzado (3 cards), comparativa (filas + "Otros monitores" + valores), descarga (títulos, botones, link, acordeón honesto + mini-instrucciones Win/Mac), FAQ (6 Q+A), CTA final, footer. También los `data-os-label/data-os-sub` (labels de descarga por SO) y el mock de la ventana (pestañas Global/Por aplicación/Conexiones, Bajada/Subida/Total, "Ancho de banda · 2 min", límites diario/mensual).
2. **Switcher de idioma** visible en el header (estilo coherente con el diseño: dark, acento #22d3ee, JetBrains Mono). Persistir elección en `localStorage`.
3. **Auto-detección** inicial por `navigator.language` (es→ES, pt→PT, resto→EN o ES; definir default ES si es indeterminado), overridable por el switcher.
4. Actualizar `<html lang>` y `document.title` por idioma. SEO: meta description traducida (al menos vía JS al cambiar idioma).
5. **Pixel-perfect intacto:** el layout/estilos no cambian; solo el texto. Enfoque libre (recomendado: anotar nodos con `data-i18n`/`data-i18n-html` + diccionario, o templating de `landing.html`). Si se cambia de innerHTML a componentes, mantener la fidelidad 1:1 verificable.
6. **Reglas de contenido (VERDAD) en los 3 idiomas:** la cuota AVISA, no corta/bloquea; privacidad exacta (historial local; VT/GeoIP opt-in y apagados; solo hash o IP, nunca archivos); "índice de confianza" = SOLO Windows (Authenticode). No inventar números/reseñas.
7. Respetar `prefers-reduced-motion` y accesibilidad (switcher operable por teclado, `lang` correcto). Build + lint limpios.

## §T-021 · Ícono unificado con la app
**Estado:** To Do · **Tech Lead:** nerv-web · **Rama:** `feature/T-020-landing-i18n` · **Niv QA:** Advisory · Pedido PO 2026-06-23.
**Contexto:** la landing usa hoy un mark de "línea/sparkline" (favicon `landing/public/favicon.svg` con polyline cian #22d3c5, y 3 logos inline en `landing.html` con `<path d="M3 15l4-5 4 3 5-7 3 4"/>`). El **ícono real de la app** (build/make_icon.py, make_icon_macos.py, make_app_qicon) es **3 barras verticales ascendentes con gradiente azul** `#3b82f6` (abajo) → `#60a5fa` (arriba) sobre fondo `#1e1e2e`.
**SVG de referencia (geometría exacta, grilla 64):**
```
viewBox 0 0 64 64; <rect 64x64 rx=14 fill=#1e1e2e>; gradiente vertical #60a5fa(top)→#3b82f6(bottom);
barras rx=2 fill=gradiente: (x12 y38 w10 h14) (x27 y24 w10 h28) (x42 y12 w10 h40)
```
**Criterios de aceptación:**
1. `landing/public/favicon.svg` reemplazado por el mark de 3 barras (geometría de arriba).
2. Los **3 logos inline** de `landing.html` (header, titlebar del mock de ventana, footer) usan el mismo mark de la app (no la línea). Mantener tamaños (34/24/30px aprox) y el glow/encuadre del diseño donde aplique.
3. Coherencia visual: el ícono es el mismo en favicon, header, mock y footer (= ícono de la app). Build limpio.

## Sprint 3 — Robustez de captura macOS + nombres
| ID | Ext (ADO/Jira) | Tarea | Asignado | Estado | Niv | Criterios de aceptación | Rama |
|----|----------------|-------|----------|--------|-----|--------------------------|------|
| T-023 | — | Leak de procesos `nettop` huérfanos (se acumulan tras cierres no-limpios) | nerv-desktop | To Do | S | Ver §T-023 | feature/T-023-capture-robustness (sobre main) |
| T-024 | — | Ocultar el helper propio (`nettop`) de la lista "Por aplicación" | nerv-desktop | To Do | A | Ver §T-024 | feature/T-023-capture-robustness |
| T-025 | — | Nombres de apps con caracteres raros / rectángulos vacíos (tofu / U+FFFD) | nerv-desktop | To Do | S | Ver §T-025 | feature/T-023-capture-robustness |

## §T-023 · Leak de `nettop` huérfanos
**Estado:** To Do · **Tech Lead:** nerv-desktop · **Niv QA:** Strong (path de captura + manejo de procesos) · Reportado por PO (vio `nettop` ×4 en la lista de procesos del sistema).
**Diagnóstico (CONFIRMADO empíricamente por orquestador):** `nettop -P -x -L 0` corre indefinido. Con cierre limpio, `stop()` lo termina OK. Con cierre NO-limpio (force-quit/crash/`kill -9`/logout), `stop()`/atexit NO corren y el `nettop` hijo queda **huérfano** (reparentado a launchd, ppid 1) y sigue vivo. Cada arranque spawnea otro → se acumulan. Prueba: tras `kill -9` al python padre, el `nettop` siguió vivo con ppid=1. NO es duplicación intra-sesión (la UI agrupa por nombre, `monitor_service.py:134`).
**Criterios de aceptación:**
1. **Reap al arrancar:** antes de lanzar nettop, terminar cualquier `nettop` previo que matchee NUESTRA firma exacta (`-P -x -L 0 … -J bytes_in,bytes_out`), del usuario actual. SIGTERM y luego SIGKILL si sigue. Acota a 1 instancia y limpia huérfanos acumulados.
2. **Cierre robusto:** manejar `SIGTERM`/`SIGINT` (además del `atexit` actual) para llamar a `stop()`/cleanup. `SIGKILL` no es atrapable → por eso (1) es la red de seguridad.
3. **MULTIPLATAFORMA — no romper Windows:** el reap y la firma de nettop son macOS-only (viven en `NettopCaptureService`/path darwin); el path Windows/ETW queda **idéntico**. Los handlers de señales deben guardar diferencias de plataforma (SIGTERM/SIGINT en Windows tienen semántica distinta; no romper el arranque Windows).
4. Tests: reap mata solo lo que matchea la firma; cleanup en stop sigue OK; idempotencia. Suite verde. Sin cambios de comportamiento en Windows.

## §T-024 · Ocultar el helper propio de la lista
**Estado:** To Do · **Tech Lead:** nerv-desktop · **Niv QA:** Advisory.
**Contexto:** `nettop` es el helper interno de la app (macOS), no una app que el usuario abrió; mostrarlo en "Por aplicación" confunde. (En Windows el helper es ETW in-process, no hay subproceso visible.)
**Criterios:**
1. Excluir de la lista/persistencia el proceso helper propio (al menos `nettop` en macOS; genérico/extensible). No contar su tráfico como "una app".
2. Filtro acotado y documentado; sin afectar el resto de apps ni el path Windows.
3. Test del filtro. Suite verde.

## §T-025 · Nombres con caracteres raros / rectángulos vacíos
**Estado:** To Do · **Tech Lead:** nerv-desktop · **Niv QA:** Strong (correctitud de datos + UI) · Reportado por PO (algunas apps con "caracteres super raros, rectángulos grandes vacíos").
**Hipótesis (a verificar, P-3 — no asumir):** dos causas posibles, pueden coexistir:
- (a) **Decodificación:** `iter_lines_from_fd` decodea con `errors="replace"` → bytes inválidos (nombre multibyte truncado por nettop) producen U+FFFD () que se ve como caja. nettop además trunca nombres a un ancho.
- (b) **Fuente/glyphs:** `theme.py:48 FONT_FAMILY='"Plus Jakarta Sans","Segoe UI",sans-serif'`; Plus Jakarta es solo-latín → nombres con CJK/emoji/acentos no cubiertos caen al fallback y pueden dar "tofu" (□) si la cadena no tiene glyph.
**Criterios de aceptación:**
1. Verificar empíricamente con un caso real cuál(es) causa(s) aplica(n) (capturar el nombre crudo de nettop para una app afectada).
2. Corregir el origen: preferible **resolver el nombre real del proceso por PID** (p. ej. psutil) en vez del nombre truncado/garbleado de nettop, o normalizar/validar la decodificación. Mismo criterio aplicable al path Windows si también muestra nombres raros.
3. Asegurar **fallback de fuente** en la UI que cubra scripts no-latinos comunes (sin romper la identidad visual): que un nombre con caracteres no-latinos se vea legible, no como cajas.
4. **Multiplataforma:** la solución no debe degradar Windows; idealmente mejora ambos. Tests del parseo/normalización de nombres. Suite verde.

## Veredictos QA
| Tarea | Veredicto | Defectos (si rechazo) | Fecha |
|-------|-----------|------------------------|-------|
| T-013 | Aprobado (Advisory) | — | 2026-06-19 |
| T-014 | Aprobado (Advisory) | — | 2026-06-20 |

## Deuda técnica
| ID | Descripción | Origen | Prioridad |
|----|-------------|--------|-----------|
| DT-001 | `_hit_test` asume origen físico=lógico en el monitor primario; en multi-monitor con DPI mixto puede desalinearse | QA review T-013 | Baja |
| DT-002 | Endpoint `GET /api/v3/users/{apikey}` para `test_api_key` no fue confirmado contra la API real de VT (sin red en entorno de dev) — validar con key viva post-merge | QA review T-014 | Media |

## §T-015 · Landing page one-page para NetGauge
**Estado:** En progreso · **Tech Lead:** nerv-web · **Rama:** `feature/T-015-landing-page` · **Niv QA:** Strong (S, >400 líneas) · Pedido por PO 2026-06-22.

**Decisiones PO (definidas en intake):**
- **Stack:** React + Vite.
- **Ubicación:** carpeta `/landing` en este repo (build local; hosting se define después). NO toca `src/` ni los workflows existentes.
- **Descargas:** se muestran SIEMPRE 3 botones (Windows x64 · macOS Apple Silicon · macOS Intel). El auto-SO solo resalta el detectado; nunca oculta los otros (el navegador no distingue Mac Intel de ARM de forma fiable).
- **Links de descarga:** apuntar a `releases/latest` (no a URLs de assets directas, que no están confirmadas). GitHub: https://github.com/gabiMaglia/NetGauge · Releases: https://github.com/gabiMaglia/NetGauge/releases/latest · Ko-fi: https://ko-fi.com/gabrielmaglia

**Idioma/tono:** español rioplatense (vos), claro, sin jerga, frases cortas, verbos de acción. Cercano, confiado, honesto.

**Identidad visual:**
- Dark mode tech / data-viz. Fondo grafito / negro azulado.
- Acento cian/verde-aqua para datos/velocidad/estados "ok". Ámbar y rojo SOLO para estados de cuota (verde/amarillo/rojo).
- Tipografía: Plus Jakarta Sans (vía webfont).
- Motivo recurrente: sparklines / gráfico de ancho de banda animado sutil.
- Placeholders para screenshots (ventana dark: "Global", "Por aplicación", "Conexiones"; ícono de bandeja con mini-gráfico).

**Secciones (en orden):**
1. Header sticky: logo "NetGauge" + links (Funciones, Cómo funciona, Privacidad, FAQ, GitHub) + botón "Descargar gratis".
2. HERO: H1 "Sabé qué app se está comiendo tu internet." Subtítulo: "Monitor de consumo de red por aplicación, en tiempo real. Gratis, de código abierto y privado: tus datos nunca salen de tu equipo. Windows y Mac." CTA primario "Descargar gratis" (auto-SO resalta) + CTA secundario "Ver en GitHub". Micro-line: "Gratis · Open source (MIT) · Sin telemetría · Windows + macOS". Imagen: screenshot de la ventana.
3. Barra de confianza: badges "MIT License", "GitHub", "Windows 10/11", "macOS Intel + Apple Silicon", "100% local".
4. Problema: "El medidor de tu sistema te da un total, no el culpable. NetGauge te muestra el ranking de apps que consumen — ahora y en tu historial."
5. Features (grid de 6 con ícono): Consumo por aplicación; Velocidad en tiempo real (↑/↓ + gráfico 2 min); Cuotas con alertas (avisa al 80% y 100%); Historial completo (sesión/día/semana/mes, local); Privacidad real (sin telemetría, VirusTotal/GeoIP opt-in apagados); Informes en un clic (CSV/Excel/PDF).
6. Cómo funciona (3 pasos): Descargá e instalá → Vive en tu bandeja → Mirá, controlá y exportá.
7. Privacidad (destacada): "Tus datos son tuyos. En serio." Historial local; nada se manda a ningún servidor; las únicas funciones con internet (reputación VirusTotal y geoloc de IPs) son opcionales y vienen APAGADAS, y solo envían un hash o una IP, nunca tus archivos.
8. Avanzado/seguridad (3 puntos): Conexiones activas por app (IP, puerto, país, proveedor — GeoIP opt-in); Índice de confianza (firma Authenticode en Windows — NO presentar como multiplataforma); Alertas de anomalías (pico ≥3× el promedio o app nueva usando la red).
9. Comparativa (tabla simple, sin nombrar competidores negativamente): Precio (Gratis), Código abierto (Sí), Telemetría (No), Windows + Mac (Sí), Desglose por aplicación (Sí).
10. Descarga (ancla "descargar"): auto-SO + 3 botones explícitos ("Windows 10/11 (x64)", "macOS Apple Silicon (M1–M4)", "macOS Intel") + link "Todas las versiones en GitHub Releases". Acordeón honesto: "El instalador todavía no está firmado, así que Windows/Mac pueden mostrar un aviso. Es por la falta de firma, no por riesgo; el código es abierto." + mini-instrucciones (Windows: Más información → Ejecutar de todas formas; Mac: click derecho → Abrir).
11. FAQ (acordeón): ¿Es gratis? · ¿Manda mis datos? · ¿Por qué me avisa el sistema al abrirlo? · ¿Necesito admin? · ¿Anda en Mac con chip M? · ¿Corta el internet al llegar a la cuota? (avisa, NO bloquea).
12. CTA final: "Tomá el control de tu red — gratis." + botones Descargar y Ver en GitHub.
13. Footer: links GitHub, Releases, Licencia MIT, Privacidad, Ko-fi ("☕ Invitar un café"). Crédito "Hecho con software libre (Qt/PySide6)".

**SEO:** title "NetGauge — Monitor de consumo de red por aplicación, gratis y open source"; meta description orientada a "ver cuánto consume cada app en Windows y Mac, gratis y privado".

**Reglas de contenido (VERDAD — no inventar):**
- NO inventar números de usuarios, reseñas ni testimonios.
- NO decir que bloquea el tráfico: la cuota AVISA, no corta.
- Privacidad exacta: historial local; VT/GeoIP opt-in y APAGADOS por defecto; solo hash o IP, nunca archivos.
- "Índice de confianza" = Windows (Authenticode); no presentarlo como multiplataforma.

**Criterios de aceptación (verifica QA):**
1. Las 13 secciones presentes, en orden, con el copy especificado (exacto en HERO, privacidad y reglas de contenido).
2. Responsive mobile-first; buen contraste (WCAG AA); accesible (semántica, foco, alt en imágenes, acordeones operables por teclado, `aria-expanded`).
3. Scroll suave entre anclas; animaciones sutiles (sparkline / contador) que respeten `prefers-reduced-motion`.
4. Auto-SO resalta el botón del SO detectado SIN ocultar los otros 3; todos los botones de descarga apuntan a `releases/latest`.
5. Identidad visual respetada (dark, acento cian/aqua, ámbar/rojo solo para cuota, Plus Jakarta Sans, motivo sparkline).
6. SEO: title + meta description exactos; metadatos OG básicos.
7. Cero cambios fuera de `/landing` (no toca `src/`, workflows, ni instaladores). Build de Vite corre limpio (`npm run build`).
8. CERO afirmaciones falsas: ninguna regla de contenido violada; el aviso de "sin firmar" presente y honesto.

## §T-016 · Rename trafficMe → NetGauge (toda la app)
**Estado:** En progreso · **Hecho por:** nerv-orquestador (rename mecánico dirigido por PO) · **Rama:** `feature/T-016-rename-netgauge` (stack sobre T-015) · **Niv QA:** Strong · Pedido por PO 2026-06-23.

**Decisiones PO:** (1) renombrar también el repo de GitHub → URLs apuntan a `github.com/gabiMaglia/NetGauge`; (2) alcance total: código + instaladores + nombres de archivo/identificadores; (3) rama propia stackeada sobre la landing T-015 (para que el rename la cubra).

**Hecho:** 46 archivos trackeados (130×`trafficMe`→`NetGauge`, 2×`trafficme`→`netgauge`) vía sed en dos pasadas, solo sobre `git ls-files` (se excluyó `.venv/trafficscript.py`, falso positivo). Carpeta skill `run-trafficme`→`run-netgauge`. Cubre: `src/`, `main.py`, `build/` (installer.iss, specs, make_dmg, sign.cmd, version_info), workflows CI/release, landing, engram, docs. Verificado: cero leftovers, landing `npm run build` OK, `compileall` OK, **pytest 52 verde (5 skip)**.

**Caveats para QA/PO:**
- ⚠️ **Migración de datos:** el dir de historial cambió (`%LOCALAPPDATA%\NetGauge`, `Library/Application Support/NetGauge`, `~/.NetGauge`). Usuarios que actualicen desde trafficMe **no verán su historial viejo** (queda en la carpeta vieja) — no se implementó migración. Decisión PO si hace falta.
- ⚠️ **Identidad de app cambió:** `_APP_ID` (Windows AppUserModelID), `bundle_identifier` macOS (`com.gabrielmaglia.netgauge`), single-instance key. El SO lo trata como app nueva (pin/tray se resetean).
- ⚠️ **Acción manual pendiente del PO:** renombrar el repo en GitHub (Settings → Rename a `NetGauge`). GitHub redirige el viejo, pero hasta hacerlo el remoto local sigue siendo `trafficMe.git` (funciona por redirect). El registry NERV se actualiza aparte.

**Criterios de aceptación:**
1. Cero ocurrencias de `trafficme`/`trafficMe` en archivos trackeados (excepto historial legítimo si lo hubiera). 
2. Build de landing, `compileall` y suite pytest verdes tras el rename.
3. Instaladores/specs/workflows producen artefactos `NetGauge*` coherentes entre sí (exe/dmg/app/bundle id).
4. URLs de GitHub/releases apuntan a `gabiMaglia/NetGauge`.
5. Sin cambios de comportamiento más allá del nombre e identidad (mismo flujo de captura/UI/reportes).

## Histórico (sprints cerrados: 3 líneas c/u, máx. 5 sprints; el resto a ~/.nerv/archive/)
