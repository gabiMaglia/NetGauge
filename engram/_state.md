# STATE — NetLeak · actualizado: 2026-06-23

**Sprint:** 1 — Marketing (landing) + rename de marca
**Rama activa:** feature/T-016-rename-netleak (stack: main → T-015 landing → T-016 rename)
**En curso:**
- **T-015** landing one-page (React+Vite, en `/landing`) — construida por nerv-web, build+lint verdes, commiteada en su rama. **Falta QA formal (Strong).**
- **T-016** rename trafficMe → **NetLeak** (toda la app: código, instaladores, workflows, URLs, engram) — hecho, pytest 52 verde, landing build OK. **Falta QA + commit.**
**Bloqueos:** ninguno
**Próximo paso sugerido:** commitear T-016; QA (nerv-qa, Strong) sobre T-015 y T-016; el PO renombra el repo en GitHub a `NetLeak`; luego PRs encadenados T-015→T-016.
**Caveats abiertos:** migración de dir de datos al renombrar (usuarios pierden historial viejo); identidad de app cambió (app_id/bundle_id); validar v1.8.4 en máquina T-013; DT-002 (endpoint VT con key real).
**Preguntas abiertas al PO:** 0
