# STATE — NetGauge · actualizado: 2026-06-23

**Sprint:** 1 — Marketing (landing) + rename de marca
**Rama activa:** feature/T-018-landing-pixel-perfect
**Stack de ramas:** main → T-015 (landing v1) → T-016 (rename) → T-017 (migración) → T-018 (landing pixel-perfect)
**En curso / pendiente de QA:**
- **T-015** landing v1 (React+Vite) — superada por T-018 (se borraron sus componentes). Mantener el commit por historia.
- **T-016** rename trafficMe → NetGauge (toda la app) — hecho, pytest verde, build OK.
- **T-017** migración de historial al actualizar — hecho, 4 tests nuevos verdes (56 total).
- **T-018** landing pixel-perfect del diseño `NetGauge Landing.dc.html` — markup extraído byte a byte, runtime portado (detección SO/contadores/reveal/hover), build+lint verdes.
**Bloqueos:** ninguno
**Próximo paso sugerido:** validación visual de la landing (npm run dev); QA Strong (T-016/T-017/T-018); el PO renombra el repo en GitHub a `NetGauge`; luego PRs encadenados T-015→T-018.
**Caveats abiertos:** identidad de app cambió con el rename (app_id/bundle_id) → el SO la trata como app nueva; design_handoff_* sin commitear (churn de carpetas que dejó el PO); validar v1.8.4 en máquina T-013; DT-002 (endpoint VT con key real).
**Preguntas abiertas al PO:** 0
