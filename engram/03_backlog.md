# Backlog — NetLeak

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
| T-015 | — | Landing page one-page (responsive, mobile-first) para NetLeak; objetivo #1 descargar, #2 confianza (privacidad + open source) | nerv-web | En progreso | S | Ver detalle completo en §T-015 (abajo) | feature/T-015-landing-page |
| T-016 | — | Rename completo de la app trafficMe → NetLeak (código, instaladores, nombres de archivo, workflows, URLs, engram) | nerv-orquestador | En progreso | S | Ver detalle en §T-016 (abajo) | feature/T-016-rename-netleak (stack sobre T-015) |
| T-017 | — | Migración de historial trafficMe → NetLeak al actualizar (resuelve el caveat de pérdida de datos del rename) | nerv-orquestador | En progreso | S | Al primer arranque, si el dir NetLeak está limpio y existe el dir trafficMe con datos, copiar usage.db/settings.json/monitor.log/reports/. Idempotente, copia (no mueve), nunca rompe el arranque. Tests. | feature/T-017-data-migration (stack sobre T-016) |
| T-018 | — | Landing pixel-perfect contra `design_handoff_netLeak_panel/NetLeak Landing.dc.html` (reemplaza la interpretación previa de T-015) | nerv-web | To Do | S | Reproducir el diseño 1:1 (acento #22d3ee, Plus Jakarta Sans + JetBrains Mono, mock de ventana, sparklines, reveal/contador/detección SO). URLs → NetLeak. Build limpio. | feature/T-018-landing-pixel-perfect (stack sobre T-017) |

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

## §T-015 · Landing page one-page para NetLeak
**Estado:** En progreso · **Tech Lead:** nerv-web · **Rama:** `feature/T-015-landing-page` · **Niv QA:** Strong (S, >400 líneas) · Pedido por PO 2026-06-22.

**Decisiones PO (definidas en intake):**
- **Stack:** React + Vite.
- **Ubicación:** carpeta `/landing` en este repo (build local; hosting se define después). NO toca `src/` ni los workflows existentes.
- **Descargas:** se muestran SIEMPRE 3 botones (Windows x64 · macOS Apple Silicon · macOS Intel). El auto-SO solo resalta el detectado; nunca oculta los otros (el navegador no distingue Mac Intel de ARM de forma fiable).
- **Links de descarga:** apuntar a `releases/latest` (no a URLs de assets directas, que no están confirmadas). GitHub: https://github.com/gabiMaglia/NetLeak · Releases: https://github.com/gabiMaglia/NetLeak/releases/latest · Ko-fi: https://ko-fi.com/gabrielmaglia

**Idioma/tono:** español rioplatense (vos), claro, sin jerga, frases cortas, verbos de acción. Cercano, confiado, honesto.

**Identidad visual:**
- Dark mode tech / data-viz. Fondo grafito / negro azulado.
- Acento cian/verde-aqua para datos/velocidad/estados "ok". Ámbar y rojo SOLO para estados de cuota (verde/amarillo/rojo).
- Tipografía: Plus Jakarta Sans (vía webfont).
- Motivo recurrente: sparklines / gráfico de ancho de banda animado sutil.
- Placeholders para screenshots (ventana dark: "Global", "Por aplicación", "Conexiones"; ícono de bandeja con mini-gráfico).

**Secciones (en orden):**
1. Header sticky: logo "NetLeak" + links (Funciones, Cómo funciona, Privacidad, FAQ, GitHub) + botón "Descargar gratis".
2. HERO: H1 "Sabé qué app se está comiendo tu internet." Subtítulo: "Monitor de consumo de red por aplicación, en tiempo real. Gratis, de código abierto y privado: tus datos nunca salen de tu equipo. Windows y Mac." CTA primario "Descargar gratis" (auto-SO resalta) + CTA secundario "Ver en GitHub". Micro-line: "Gratis · Open source (MIT) · Sin telemetría · Windows + macOS". Imagen: screenshot de la ventana.
3. Barra de confianza: badges "MIT License", "GitHub", "Windows 10/11", "macOS Intel + Apple Silicon", "100% local".
4. Problema: "El medidor de tu sistema te da un total, no el culpable. NetLeak te muestra el ranking de apps que consumen — ahora y en tu historial."
5. Features (grid de 6 con ícono): Consumo por aplicación; Velocidad en tiempo real (↑/↓ + gráfico 2 min); Cuotas con alertas (avisa al 80% y 100%); Historial completo (sesión/día/semana/mes, local); Privacidad real (sin telemetría, VirusTotal/GeoIP opt-in apagados); Informes en un clic (CSV/Excel/PDF).
6. Cómo funciona (3 pasos): Descargá e instalá → Vive en tu bandeja → Mirá, controlá y exportá.
7. Privacidad (destacada): "Tus datos son tuyos. En serio." Historial local; nada se manda a ningún servidor; las únicas funciones con internet (reputación VirusTotal y geoloc de IPs) son opcionales y vienen APAGADAS, y solo envían un hash o una IP, nunca tus archivos.
8. Avanzado/seguridad (3 puntos): Conexiones activas por app (IP, puerto, país, proveedor — GeoIP opt-in); Índice de confianza (firma Authenticode en Windows — NO presentar como multiplataforma); Alertas de anomalías (pico ≥3× el promedio o app nueva usando la red).
9. Comparativa (tabla simple, sin nombrar competidores negativamente): Precio (Gratis), Código abierto (Sí), Telemetría (No), Windows + Mac (Sí), Desglose por aplicación (Sí).
10. Descarga (ancla "descargar"): auto-SO + 3 botones explícitos ("Windows 10/11 (x64)", "macOS Apple Silicon (M1–M4)", "macOS Intel") + link "Todas las versiones en GitHub Releases". Acordeón honesto: "El instalador todavía no está firmado, así que Windows/Mac pueden mostrar un aviso. Es por la falta de firma, no por riesgo; el código es abierto." + mini-instrucciones (Windows: Más información → Ejecutar de todas formas; Mac: click derecho → Abrir).
11. FAQ (acordeón): ¿Es gratis? · ¿Manda mis datos? · ¿Por qué me avisa el sistema al abrirlo? · ¿Necesito admin? · ¿Anda en Mac con chip M? · ¿Corta el internet al llegar a la cuota? (avisa, NO bloquea).
12. CTA final: "Tomá el control de tu red — gratis." + botones Descargar y Ver en GitHub.
13. Footer: links GitHub, Releases, Licencia MIT, Privacidad, Ko-fi ("☕ Invitar un café"). Crédito "Hecho con software libre (Qt/PySide6)".

**SEO:** title "NetLeak — Monitor de consumo de red por aplicación, gratis y open source"; meta description orientada a "ver cuánto consume cada app en Windows y Mac, gratis y privado".

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

## §T-016 · Rename trafficMe → NetLeak (toda la app)
**Estado:** En progreso · **Hecho por:** nerv-orquestador (rename mecánico dirigido por PO) · **Rama:** `feature/T-016-rename-netleak` (stack sobre T-015) · **Niv QA:** Strong · Pedido por PO 2026-06-23.

**Decisiones PO:** (1) renombrar también el repo de GitHub → URLs apuntan a `github.com/gabiMaglia/NetLeak`; (2) alcance total: código + instaladores + nombres de archivo/identificadores; (3) rama propia stackeada sobre la landing T-015 (para que el rename la cubra).

**Hecho:** 46 archivos trackeados (130×`trafficMe`→`NetLeak`, 2×`trafficme`→`netleak`) vía sed en dos pasadas, solo sobre `git ls-files` (se excluyó `.venv/trafficscript.py`, falso positivo). Carpeta skill `run-trafficme`→`run-netleak`. Cubre: `src/`, `main.py`, `build/` (installer.iss, specs, make_dmg, sign.cmd, version_info), workflows CI/release, landing, engram, docs. Verificado: cero leftovers, landing `npm run build` OK, `compileall` OK, **pytest 52 verde (5 skip)**.

**Caveats para QA/PO:**
- ⚠️ **Migración de datos:** el dir de historial cambió (`%LOCALAPPDATA%\NetLeak`, `Library/Application Support/NetLeak`, `~/.NetLeak`). Usuarios que actualicen desde trafficMe **no verán su historial viejo** (queda en la carpeta vieja) — no se implementó migración. Decisión PO si hace falta.
- ⚠️ **Identidad de app cambió:** `_APP_ID` (Windows AppUserModelID), `bundle_identifier` macOS (`com.gabrielmaglia.netleak`), single-instance key. El SO lo trata como app nueva (pin/tray se resetean).
- ⚠️ **Acción manual pendiente del PO:** renombrar el repo en GitHub (Settings → Rename a `NetLeak`). GitHub redirige el viejo, pero hasta hacerlo el remoto local sigue siendo `trafficMe.git` (funciona por redirect). El registry NERV se actualiza aparte.

**Criterios de aceptación:**
1. Cero ocurrencias de `trafficme`/`trafficMe` en archivos trackeados (excepto historial legítimo si lo hubiera). 
2. Build de landing, `compileall` y suite pytest verdes tras el rename.
3. Instaladores/specs/workflows producen artefactos `NetLeak*` coherentes entre sí (exe/dmg/app/bundle id).
4. URLs de GitHub/releases apuntan a `gabiMaglia/NetLeak`.
5. Sin cambios de comportamiento más allá del nombre e identidad (mismo flujo de captura/UI/reportes).

## Histórico (sprints cerrados: 3 líneas c/u, máx. 5 sprints; el resto a ~/.nerv/archive/)
