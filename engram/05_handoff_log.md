# Handoff Log — NetLeak

> Entradas nuevas ARRIBA. Máx. 6 líneas por entrada. Al superar 30 entradas,
> el Orquestador mueve las más viejas a ~/.nerv/archive/NetLeak-handoffs-[fecha].md

### 2026-06-23 nerv-orquestador (port directo) T-018
- Hecho: landing rehecha pixel-perfect contra `design_handoff_netLeak_panel/NetLeak Landing.dc.html`. Markup extraído byte a byte (script python, URLs → NetLeak) a `landing/src/landing.html`, inyectado vía `?raw`+dangerouslySetInnerHTML; runtime portado en `App.tsx` (detección SO con WebGL, contadores, reveal con reduced-motion, hover por `style-hover`); CSS base/keyframes del diseño en `index.css`; fuentes en `index.html`. Borrados los componentes de la interpretación previa (T-015).
- Verificado: build (17 módulos) + lint verdes; bundle contiene acento #22d3ee/style-hover/URLs NetLeak; cero `trafficMe`/`rootRef`.
- Pendiente: validación VISUAL (npm run dev) y QA Strong. Caveat: dangerouslySetInnerHTML elegido a propósito por fidelidad 1:1 (documentado).

### 2026-06-23 nerv-orquestador (migración) T-017
- Hecho: `main.py` migra el historial de la instalación previa trafficMe → NetLeak al primer arranque (copia usage.db/settings.json/monitor.log/reports si NetLeak está limpio y trafficMe tiene datos). Idempotente, conservador, nunca rompe el arranque. Test `tests/test_data_migration.py` (4 casos). Resuelve el caveat de T-016.
- Verificado: pytest 56 verde (5 skip).

### 2026-06-23 nerv-orquestador (rename) T-016
- Hecho: rename trafficMe → NetLeak en 46 archivos trackeados (sed 2 pasadas sobre `git ls-files`; excluido `.venv` falso positivo), carpeta skill `run-trafficme`→`run-netleak`. Cubre src/, build, workflows, landing, engram, docs, URLs (→ gabiMaglia/NetLeak). Rama `feature/T-016-rename-netleak` stackeada sobre T-015.
- Verificado: cero leftovers, landing `npm run build` OK, `compileall` OK, **pytest 52 verde (5 skip)**. Detalle/criterios en §T-016.
- Pendiente: commit; QA Strong (T-015 + T-016); PO renombra repo en GitHub; actualizar remoto local y registry; PRs encadenados.
- Caveats: migración dir de datos (historial viejo no migra); cambia identidad de app (app_id/bundle_id/single-instance).

### 2026-06-22 nerv-orquestador→nerv-web T-015
- Entrega: construir la landing one-page de NetLeak (React+Vite, en `/landing`). Brief completo, decisiones PO, identidad visual, 13 secciones, reglas de contenido y criterios de aceptación: §T-015 en `engram/03_backlog.md`. Niv QA: Strong (>400 líneas).
- Verdades verificadas contra el código (usar tal cual, NO inventar): MIT (LICENSE raíz); features reales en `src/` (connections, virustotal opt-in, geoip, trust/Authenticode solo-Windows, quota, anomalía 3×, reportes CSV/Excel/PDF); build sin firmar (ADR-001). Links: ver §T-015.
- Restricciones: solo crear archivos bajo `/landing`; NO tocar `src/`, workflows ni instaladores. Descargas → `releases/latest`. 3 botones siempre visibles. Respetar reglas de contenido (cuota avisa NO bloquea; privacidad exacta; confianza=Windows).
- Pendientes: screenshots reales no existen → usar placeholders. `npm run build` debe correr limpio antes de devolver el control.

### 2026-06-20 nerv-orquestador→nerv-desktop T-014
- Entrega: PO reportó que metió la API key de VT, tildó el checkbox, y "no pasó nada" visible. Causa raíz real: NO es bug funcional (el flujo `_enrich_with_vt` en monitor_service.py:349 funciona), es falta total de feedback visual — el label del checkbox se corta por el ancho fijo del diálogo (420px) y solo se lee completo con hover; no hay indicador de "VT analizó esta app" ni de "la key es válida".
- Se espera: (1) badge por proceso coloreado cuando VT analizó esa app, (2) LED de estado de conexión VT en Settings, (3) link a registro de VT. Ver criterios completos en backlog T-014.
- Pendientes: definir cómo testear la API key sin esperar (endpoint liviano de VT, ej. GET a /api/v3/users/<id> o similar con la key — confirmar cuál usa rate limit mínimo).

### 2026-06-20 nerv-orquestador (CI) T-013
- Hallazgo: tag v1.8.2 quedó colgado en "Waiting for a runner" en el job macOS x86_64 — causa: `macos-13` fue deprecado y removido por GitHub (deprecación 2025-09-22, fin de soporte 2025-12-08); el label ya no asigna runners, por eso cuelga indefinido en vez de fallar rápido.
- Fix: `.github/workflows/release.yml` migrado de `macos-13` a `macos-15-intel` (commit 9b6a07a, pusheado a main). Tag `v1.8.3` creado para reintentar el release.
- Pendiente: cancelar manualmente el run colgado de v1.8.2 en GitHub Actions (no hay `gh` CLI disponible en este entorno).

### 2026-06-19 nerv-desktop→nerv-orquestador T-013
- Entrega: fix en rama `fix/T-013-window-controls` (sobre commit 764b188), archivos `src/presentation/qt/app.py`, `src/presentation/qt/native_window.py`, `tests/test_native_window.py` (nuevo).
- Causa raíz: `_hit_test` (WM_NCHITTEST) mezclaba coordenadas físicas y lógicas sin dividir por `devicePixelRatioF()`; con escalado fraccional de Windows (125/150/175%, común en notebooks) el header quedaba "muerto". Se fijó `HighDpiScaleFactorRoundingPolicy.PassThrough` y se blindó `handle_native_event` contra excepciones silenciosas.
- Riesgos: no reproducido en vivo (sin acceso a la máquina afectada); alta confianza pero falta validación real. Fallo preexistente no relacionado en `test_nettop_capture.py` (falta `termios` en Windows).
- Estado: En revisión QA.

### 2026-06-19 nerv-orquestador→nerv-desktop T-013
- Entrega: bug reportado por PO — instalador desde GitHub Releases, instalado en notebook Windows 11 de su novia; ventana sin controles de header (no mueve, no resize, no cierra/minimiza). En la PC del PO (Windows 11) funciona perfecto. Resto de la app funciona bien en ambas.
- Se espera: reproducir o inspeccionar config de ventana (flags Qt, frameless custom, DPI/escala, diferencias de instalador/build) y proponer causa raíz + fix.
- Pendientes: no hay acceso directo a la notebook con el bug; puede requerir logs/capturas de pantalla del PO o instrumentación remota.
