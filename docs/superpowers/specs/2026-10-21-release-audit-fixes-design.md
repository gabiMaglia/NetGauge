# Release audit fixes — design

Fecha: 2026-10-21 · Rama: `fix/release-audit` · Base: v2.0.1

## Objetivo

Dejar NetGauge publicable: sin crashes conocidos, sin pérdida silenciosa de datos,
sin degradación con el uso prolongado, con pipeline de release confiable y
documentación honesta (privacidad, licencias, instalación).

Criterio de éxito: `python -m pytest -q` pasa en Windows de forma estable
(5 corridas seguidas), todos los BLOCKER/HIGH del audit resueltos o
documentados como decisión pendiente del PO.

## Origen

Auditoría read-only de 3 frentes (núcleo/captura, UI/persistencia, release/repo).
Hallazgos verificados en código: crash ctypes en `trust.py`, crecimiento sin
agregación en `sqlite_repository.save_batch`.

## Descomposición en sub-proyectos

Cada uno tiene su plan en `docs/superpowers/plans/`. Orden de ejecución = orden
de la tabla (los primeros desbloquean testear los siguientes).

| # | Plan | Hallazgos | Severidad |
|---|------|-----------|-----------|
| 1 | `01-windows-crash-safety` | ctypes sin restype/argtypes en `_signer_name` y `_verify_catalog` (+ leak de cert context); `import pty` a nivel de módulo rompe la colección de tests en Windows; `startswith` sin separador en rutas de confianza | BLOCKER |
| 2 | `02-persistence-hardening` | agregación real por (app, minuto) con UPSERT + migración v2 que consolida filas existentes; WAL + recuperación de DB corrupta; `settings.json` atómico y `load()` robusto; purge con vacuum incremental | BLOCKER/HIGH |
| 3 | `03-service-resilience` | `_tick`/`_rate_tick` se reprograman siempre; `_flush` no pierde el batch si falla; carrera stop/tick; hilos de captura (ETW, nettop, psutil) no mueren en silencio; `_on_exit` con try/finally | HIGH |
| 4 | `04-ui-thread-offload` | trust/exe_paths/connections/cuotas fuera del hilo GUI (worker + cache); cache de PID con invalidación por `create_time`; `exe_paths` con clave por ruta, no por FileDescription | HIGH/MEDIUM |
| 5 | `05-release-pipeline` | versión única desde `src/version.py` (version_info.txt, spec macOS, iss, dmg); ci.yml con runner macOS vigente + ubuntu; release.yml con gate de tests, SHA256SUMS, permisos mínimos; requirements: pyinstaller a dev | BLOCKER/HIGH |
| 6 | `06-docs-legal` | README reescrito (descarga, requisitos, admin, aviso de firma, privacidad); `THIRD_PARTY_LICENSES.md`; `SECURITY.md`; `.gitignore` (`.env*`, `*.pfx`, `*.p12`) | BLOCKER/HIGH |
| 7 | `07-polish-v2.0.2` | single-instance por usuario + chequeo de `listen`; workers VT/GeoIP sin carrera; VT no cachea errores transitorios y `set_api_key` limpia; `test_api_key` sin key en URL; CSV `utf-8-sig` + escape de fórmulas; QLabel PlainText; geometría fuera de pantalla; update check cada 24 h + toast clicable; rotación de reportes | MEDIUM/LOW |

## Decisiones tomadas (autónomas)

- **Agregación**: tabla `usage` con `minute TEXT` (ISO truncado a minuto) y
  `UNIQUE(app_name, minute)`; `save_batch` hace `INSERT ... ON CONFLICT DO UPDATE
  SET bytes += excluded`. Migración v2 recrea la tabla consolidando con
  `GROUP BY app_name, substr(recorded_at,1,16)`. `recorded_at` se mantiene como
  nombre de columna para no romper queries/reportes. Alternativa descartada:
  buffer de 60 s en memoria (pierde hasta 1 min ante crash y no arregla DBs ya infladas).
- **Resiliencia**: patrón `try/except Exception → log → finally reprogramar`.
  Logging vía `logging` estándar a archivo en `data_dir/netgauge.log` con rotación.
- **UI offload**: un único worker de fondo en la capa de aplicación que refresca
  un snapshot (trust por app, conexiones, estado de cuota); la UI sólo lee el
  snapshot. Alternativa descartada: `QThreadPool` en presentación (mete lógica
  de negocio en Qt).
- **Versión única**: `src/version.py` es la fuente; los specs de PyInstaller la
  importan y un script `build/gen_version_info.py` genera `version_info.txt`.
- **Commits**: conventional commits, uno por work unit, sin atribución de IA.

## Decisiones pendientes del PO (NO se ejecutan)

1. **Material interno en el historial** (`engram/`, `design_handoff_*`, `.claude/`
   con ruta local). Opciones: reescribir historial (`git filter-repo`) o publicar
   un repo nuevo limpio. Irreversible y afecta remotos → decide el PO.
2. **Firma de código** (SignPath.io OSS gratis / Azure Trusted Signing / cert OV;
   notarización Apple requiere cuenta de pago).
3. **Proveedor GeoIP**: ip-api free es HTTP y no comercial. Opciones: mantener
   con aviso explícito en Settings (lo que se implementa ahora), pagar ip-api Pro
   (HTTPS), o base offline (MaxMind GeoLite2, requiere licencia/registro).
4. **`package_store.ps1`**: borrar o reescribir para MSIX (incompatible con
   `requireAdministrator` sin rediseño).
5. **API key de VirusTotal en texto plano**: migrar a `keyring` agrega dependencia;
   por ahora se documenta.
6. **Nombres legacy** (`network_monitor*.spec`, AUMID `...NetworkMonitor`):
   cambiar el AUMID rompe pines de la barra de tareas existentes.
7. **Landing**: screenshots, OG image PNG, links a assets directos.

## Testing

Strict TDD: cada fix con test rojo primero. Los tests de ctypes en Windows se
marcan `skipif(sys.platform != "win32")`. Prueba de estabilidad: 5 corridas
seguidas de la suite completa sin crash.
