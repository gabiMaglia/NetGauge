# STATE — NetGauge · actualizado: 2026-06-23

**Marca final:** NetGauge (dos renames: trafficMe → NetLeak → NetGauge; NetLeak nunca se publicó).
**Sprint:** 1 — Marketing (landing) + rename de marca
**Rama activa:** feature/T-019-rename-netgauge
**Stack de ramas:** main → T-015 (landing v1) → T-016 (rename→NetLeak) → T-017 (migración) → T-018 (landing pixel-perfect) → T-019 (rename→NetGauge)
**Hecho, pendiente de QA (Strong):**
- **T-016/T-019** rename total a NetGauge — pytest+build verdes, 0 leftovers.
- **T-017** migración de historial trafficMe → NetGauge al actualizar — 4 tests verdes (56 total).
- **T-018** landing pixel-perfect del diseño (`design_handoff_netLeak_panel/NetLeak Landing.dc.html`) — markup byte a byte, runtime portado, build+lint verdes.
**Bloqueos:** ninguno
**Próximo paso sugerido:** validación visual de la landing (npm run dev); decidir hosting (recomendado Vercel + dominio, ej. netgauge.app); QA Strong; el PO renombra el repo en GitHub a `NetGauge`; luego PRs encadenados T-015→T-019.
**Caveats abiertos:** ramas T-016/T-018 conservan "netleak" en su nombre git (solo el texto del engram dice netgauge); identidad de app cambió con el rename (app_id/bundle_id) → SO la trata como app nueva; validar v1.8.4 en máquina T-013; DT-002 (endpoint VT con key real).
**Preguntas abiertas al PO:** 0
