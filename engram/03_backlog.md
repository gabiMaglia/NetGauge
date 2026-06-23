# Backlog — trafficMe

> Estados: Backlog → To Do → En progreso → En revisión QA → Done | Bloqueado
> Solo nerv-qa escribe "Done". Mapear SIEMPRE el ID externo si existe.
> Niv (P-11, nivel de revisión QA): A=Advisory (default) · S=Strong · X=Adversarial.

## Sprint 0 — Intake + investigación de bug reportado
| ID | Ext (ADO/Jira) | Tarea | Asignado | Estado | Niv | Criterios de aceptación | Rama |
|----|----------------|-------|----------|--------|-----|--------------------------|------|
| T-013 | — | Ventana sin controles de header (mover/resize/cerrar/minimizar) en Windows 11 de otra PC; funciona OK en la PC del PO | nerv-desktop | Done | A | El header permite mover/resize/cerrar/minimizar la ventana en ambas máquinas Windows 11; identificar causa raíz (flags de ventana, frameless custom, DPI/escala, instalador) | main (commit 764b188, sin PR) |
| T-014 | — | Feedback visual de VirusTotal insuficiente: el estado del check (settings_dialog.py:53) solo se ve completo con hover; no hay indicio de si una app fue analizada por VT ni si la conexión/API key funciona | nerv-desktop | Done | A | (1) Badge junto al indicador de confianza por proceso que se coloree cuando esa app fue analizada por VT (usar vt_malicious/vt_total ya presentes en TrustInfo); (2) LED/indicador de estado de conexión con VirusTotal en Settings (válido/inválido/sin probar — requiere alguna forma de testear la key sin esperar a la próxima evaluación de proceso); (3) link clickeable en Settings a la página de registro de VirusTotal (https://www.virustotal.com/gui/join-us) para que el usuario consiga su propia API key | fix/T-014-vt-feedback |

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

## Histórico (sprints cerrados: 3 líneas c/u, máx. 5 sprints; el resto a ~/.nerv/archive/)
