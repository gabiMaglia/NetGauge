# STATE — NetGauge · actualizado: 2026-06-23

**Marca final:** NetGauge (dos renames: trafficMe → NetLeak → NetGauge; NetLeak nunca se publicó).
**Sprint:** 1 — Marketing (landing) + rebrand → **RELEASE v2.0.0 PUSHEADO**
**Rama objetivo:** main (en `origin/main`, commit 2467d5c) · repo GitHub renombrado a **gabiMaglia/NetGauge** · remoto local actualizado.
**Release:** tag **v2.0.0** pusheado → workflow `release.yml` corriendo (run 28050985263). Pendiente: confirmar que publique los 3 assets (NetGauge-Setup-x64.exe + 2 .dmg, sin firmar).
**Mergeado a main (ff) y pusheado:** T-015 (landing v1) · T-016/T-019 (rename→NetGauge) · T-017 (migración historial) · T-018 (landing pixel-perfect) · release prep (version 2.0.0 + changelog).
**QA:** Strong NO ejecutada — release por decisión directa del PO. Deuda: auditar T-016..T-019 post-release si se quiere.
**Bloqueos:** ninguno
**Próximo paso sugerido:** confirmar assets del Release v2.0.0; decidir hosting de la landing (recomendado Vercel + dominio netgauge.app); validar v2.0.0 instalado (incl. migración de historial) en una máquina real.
**Caveats abiertos:** ramas feature T-016/T-018 conservan "netleak" en su nombre git (cosmético); identidad de app cambió (app_id/bundle_id) → SO la trata como app nueva; DT-002 (endpoint VT con key real); validar T-013 en la máquina afectada.
**Preguntas abiertas al PO:** 0
