# STATE — NetGauge · actualizado: 2026-06-23

**Marca final:** NetGauge (dos renames: trafficMe → NetLeak → NetGauge; NetLeak nunca se publicó).
**Sprint:** 2 — Landing polish (i18n + ícono + accent) · (Sprint 1 cerró con RELEASE v2.0.0 pusheado)
**Landing en main (origin/main 65dd8c8):** T-020 i18n ES/EN/PT + switcher · T-021 ícono unificado (3 barras) · T-022 accent azul #458bf8. Pusheado.
**Sprint 3 EN MAIN (origin/main 0264f9d):** T-023 fix leak nettop huérfanos (reap + señales, macOS-only; cleanup SIGTERM validado en vivo) · T-024 ocultar helper nettop · T-025 nombres truncados→completos por PID (psutil). + **fix de marca**: la barra de título y el "Acerca de" decían "trafficMe" por marca partida `traffic<span>Me</span>` (mismo bug que el logo landing; el sed no la alcanzó) → corregido a `Net<span>Gauge</span>`. pytest 68 verde. App reabierta y verificada en la Mac del PO (dice NetGauge, 1 nettop).
**T-026 (en main):** tipografía Plus Jakarta Sans bundleada (4 TTF OFL + loader `theme.load_app_fonts()` + specs) → warning de fuente faltante resuelto, verificado en vivo.
**RELEASE v2.0.1 PUSHEADO** (tag cb236e9, workflow corriendo run 28072116944): junta T-023/24/25 + fix marca + T-026. Pendiente: confirmar los 3 assets (exe + 2 dmg).
**QA Strong pendiente (no bloqueante, decisión PO):** T-016..T-026 fueron al release validados a ojo por el PO, sin auditoría QA formal.
**Rama objetivo:** main (en `origin/main`, commit 2467d5c) · repo GitHub renombrado a **gabiMaglia/NetGauge** · remoto local actualizado.
**Release:** tag **v2.0.0** pusheado → workflow `release.yml` corriendo (run 28050985263). Pendiente: confirmar que publique los 3 assets (NetGauge-Setup-x64.exe + 2 .dmg, sin firmar).
**Mergeado a main (ff) y pusheado:** T-015 (landing v1) · T-016/T-019 (rename→NetGauge) · T-017 (migración historial) · T-018 (landing pixel-perfect) · release prep (version 2.0.0 + changelog).
**QA:** Strong NO ejecutada — release por decisión directa del PO. Deuda: auditar T-016..T-019 post-release si se quiere.
**Bloqueos:** ninguno
**Próximo paso sugerido:** confirmar assets del Release v2.0.0; decidir hosting de la landing (recomendado Vercel + dominio netgauge.app); validar v2.0.0 instalado (incl. migración de historial) en una máquina real.
**Caveats abiertos:** ramas feature T-016/T-018 conservan "netleak" en su nombre git (cosmético); identidad de app cambió (app_id/bundle_id) → SO la trata como app nueva; DT-002 (endpoint VT con key real); validar T-013 en la máquina afectada.
**Preguntas abiertas al PO:** 0
