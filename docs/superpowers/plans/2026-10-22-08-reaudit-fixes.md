# Re-audit fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir los hallazgos de la re-auditoría de la rama `fix/release-audit` (3 revisores de contexto fresco, 2026-10-22) antes de publicar.

**Architecture:** Fix pass único, en 3 tandas secuenciales (A núcleo/arranque, B captura, C UI/docs). Cada fix: test que reproduce el hallazgo → FAIL → fix mínimo → PASS → suite completa verde → commit.

**Tech Stack:** Python 3.14, PySide6, sqlite3, ctypes (Win32), pytest.

**Spec:** docs/superpowers/specs/2026-10-21-release-audit-fixes-design.md

## Global Constraints

- Conventional commits en español, uno por hallazgo (o por grupo pequeño del mismo archivo). Sin `Co-Authored-By` ni atribución de IA.
- Nunca builds ni lanzar la GUI. `python -m pytest` (pytest.ini ya trae `-q`). Baseline: 293 passed, 1 skipped.
- Cada fix con test que falle primero (salvo cambios de docs: verificación con un `python -c` que asserte el texto).
- No tocar datos reales en `%LOCALAPPDATA%`.

## Review Focus

- Migración/arranque en disco lleno o DB bloqueada: la app debe loguear y avisar, no morir muda.
- Dos instancias simultáneas (tarea ONLOGON + doble clic) durante la migración.
- VirusTotal con key inválida / 429 / sin red: no gastar cuota.
- ETW detenido externamente (`logman stop`) con la app corriendo: debe degradar a psutil.
- Usuario que apaga GeoIP con cola llena: no debe salir ni una IP más.

---

## Tanda A — núcleo, persistencia y arranque

### A1 (Important) `save_batch` sin rollback duplica bytes
`src/infrastructure/persistence/sqlite_repository.py` `save_batch` (y `purge_older_than`): si el insert falla a mitad del batch, la transacción queda abierta; el retry de `_flush` + próximo `commit()` persiste filas parciales + el batch completo (repro: app 'a' 200 bytes en vez de 100).
- [ ] Test: conexión que falla en la 2da fila (wrapper/mock de `executemany` o trigger SQLite `RAISE(ABORT)` condicional) → tras reintento exitoso, totales exactos.
- [ ] Fix: `try: ...; commit() except BaseException: self._conn.rollback(); raise` en `save_batch` y `purge_older_than`.

### A2 (Important) `update_settings` re-dispara alertas de cuota
`src/application/monitor_service.py` `update_settings` limpia siempre `_alerts_fired`/`_daily_alerts_fired`; `MainWindow.hideEvent → _save_geometry → update_settings` → toasts 80/100 % se repiten cada vez que se oculta la ventana.
- [ ] Test: alertas disparadas; `update_settings` cambiando solo geometría/unidad → tick → no hay alertas nuevas; cambiando la cuota mensual → sí se rearman.
- [ ] Fix: limpiar sólo si cambió `monthly_quota_gb`, `daily_quota_gb`, `billing_day` o `alert_thresholds` (usar los nombres reales de `Settings`).

### A3 (Important) Excepción en el arranque no se loguea
`main.py`: un `OperationalError` al abrir el repo (DB bloqueada, disco lleno en la migración/VACUUM) mata el exe windowed sin dejar rastro.
- [ ] Test (`tests/test_main.py`): `main()` con factory de repo que lanza → se registra con `log.exception` (caplog) y devuelve código ≠ 0 sin propagar.
- [ ] Fix: tras `_setup_logging`, envolver el resto de `main()` en `try/except Exception: log.exception(...)`; mostrar un `QMessageBox.critical` mínimo sólo si ya existe QApplication o crearla para el mensaje (best-effort, en try). Instalar además `sys.excepthook` que loguee.

### A4 (Important) Repo/migración se abre antes del single-instance
`main.py` construye el repositorio (migración + VACUUM) antes del chequeo de instancia única en `run()` → segunda instancia durante una migración larga choca con el lock y crashea.
- [ ] Test: el chequeo `already_running()` se evalúa antes de construir el repositorio (inyectar fakes y registrar orden de llamadas).
- [ ] Fix: mover el chequeo de instancia única (sólo `already_running()` + envío de "show") antes de construir el repo; si hay otra instancia, salir 0 sin tocar la DB.

### A5 (Important) Retry de `listen()` fallido debe re-chequear la otra instancia
`src/presentation/qt/app.py` (~L181) y `single_instance.py` (~L62): Ruling previo del orquestador era "seguir sin instancia única". Refinado: si `listen()` falla, volver a llamar `already_running()`; si alguien responde → salir 0; sólo si nadie responde → seguir sin guard y loguear warning. En macOS no llamar `removeServer` si `already_running()` responde (borraría el socket vivo).
- [ ] Tests con guard fake: listen False + already_running True → exit 0; listen False + already_running False → continúa + warning; removeServer no se llama si hay instancia viva.

### A6 (Important) VACUUM post-migración no se reintenta
`sqlite_repository.py` (~L127): si `VACUUM` falla tras commitear v2, nunca se vuelve a correr → `auto_vacuum` queda en 0 para siempre.
- [ ] Test: tras abrir, si `PRAGMA auto_vacuum != 2` se intenta VACUUM (best-effort); un VACUUM que falla se loguea y no impide abrir.
- [ ] Fix: VACUUM en try/log; en cada `_open`, si `auto_vacuum != 2`, setear `auto_vacuum=INCREMENTAL` + VACUUM best-effort.

### A7 (Important) Código de error extendido de SQLite
`sqlite_repository.py` (~L69): `sqlite_errorcode` es extendido; comparar `code & 0xFF in (11, 26)` para que `SQLITE_CORRUPT_INDEX` (779) etc. se pongan en cuarentena.
- [ ] Test: excepción fake con `sqlite_errorcode = 779` → se trata como corrupta.

### A8 (Important) `settings.json` pisado tras error transitorio de lectura
`src/infrastructure/persistence/settings_store.py`: un `OSError` de lectura (AV/OneDrive) hace que `load()` devuelva defaults y el próximo `save()` pise la config real.
- [ ] Test: `read_text` lanza `PermissionError` → `load()` devuelve defaults y un `save()` posterior NO sobrescribe el archivo (o lo hace sólo tras una lectura OK). JSON inválido sigue yendo a `.bak` + defaults.
- [ ] Fix: distinguir corrupción (JSON/Type/Value/AttributeError) de `OSError`; en `OSError` reintentar 3 veces con 100 ms y si sigue fallando marcar `_read_failed=True` que hace `save()` no-op (log warning).

### A9 (Minor, barato) Purge fallido silencioso
`monitor_service._purge_if_due`: `except: pass` y `_last_purge` antes de intentar. → `log.exception` y setear `_last_purge` sólo si tuvo éxito. Test con repo que lanza en purge.

### A10 (Minor, barato) Wake-up perdido en SnapshotRefresher + doble worker
`src/application/snapshot_refresher.py`: hacer `clear()` antes de `_refresh()` al tope del loop; en `stop()` conservar `_thread` si sigue vivo tras el join y que `start()` sea no-op en ese caso. Tests directos.

### A11 (Minor, barato) Listener del snapshot no se desengancha al salir
`app.py` `quit_app` y tras `app.exec()`: `monitor.set_snapshot_listener(None)` antes de `monitor.stop()`. Test: `set_snapshot_listener(None)` hace que `refresh_snapshot` no llame al listener anterior.

## Tanda B — captura

### B1 (Important) Backoff de VirusTotal anulado
`monitor_service._enrich_with_vt` llama `set_api_key` cada ciclo y `set_api_key` limpia backoff/errores → reintentos cada 16 s, quema la cuota de 500/día.
- [ ] Test: repetir `set_api_key` con la MISMA key no limpia `_retry_at`/`_fails`/errores; con key distinta sí.
- [ ] Fix: en `reputation_virustotal.set_api_key`: `if key == self._api_key: return` (bajo lock).

### B2 (Important) ETW muerto en runtime no se detecta
`src/infrastructure/capture/etw_capture.py`: pywintrace `ETW.start()` no bloquea; su consumer thread muere en silencio. El fake de los tests bloquea (contrato falso).
- [ ] Cambiar `_FakeSession.start()` en `tests/test_etw_capture.py` para que retorne de inmediato y exponga un hilo consumidor fake.
- [ ] Test: el consumidor fake termina → en ≤ 2 intervalos de watchdog se llama `on_failure` y `failed=True`.
- [ ] Fix: watchdog (hilo daemon o loop en `_run`) que cada 2 s chequea `session.consumer.process_thread.is_alive()` (verificar los atributos reales en el paquete `etw` instalado: `python -c "import etw, inspect; print(inspect.getsourcefile(etw))"`) y, si el hilo murió sin `stop()`, dispara `on_failure`. Fallback si no existe el atributo: no hacer nada (log debug).

### B3 (Important) `_signer_name` devuelve la CA, no el firmante
`trust.py` (~L306): toma el primer cert del store PKCS7. Repro: explorer.exe → "Microsoft Windows Production PCA ...".
- [ ] Test (win32): `_signer_name(explorer.exe)` empieza con "Microsoft Windows" y NO contiene "PCA"; un exe firmado de terceros que exista (`python.exe` de `sys.executable` si está firmado) no contiene "PCA"/"Timestamp".
- [ ] Fix: usar el buffer `CMSG_SIGNER_INFO` ya obtenido: castear a struct `CMSG_SIGNER_INFO` (dwVersion, Issuer CERT_NAME_BLOB, SerialNumber CRYPT_INTEGER_BLOB, ...), armar `CERT_INFO` con Issuer+SerialNumber y `CertFindCertificateInStore(h_store, X509|PKCS7, 0, CERT_FIND_SUBJECT_CERT=0x000B0000, byref(cert_info), None)` con prototipos correctos (`c_void_p` retorno), liberar con `CertFreeCertificateContext`.

### B4 (Important) Errores de IO de WinVerifyTrust → SUSPICIOUS cacheado para siempre
`trust.py` (~L260-275, cache ~L355): `CRYPT_E_FILE_ERROR` (0x80092003) y similares se tratan como firma inválida.
- [ ] Tests: ruta inexistente → nivel UNKNOWN (no suspicious) y no se cachea; cache se invalida si cambia (mtime, size).
- [ ] Fix: sólo `TRUST_E_BAD_DIGEST` (0x80096010), `TRUST_E_EXPLICIT_DISTRUST` (0x800B0111), `CERT_E_*` (0x800B01xx), `TRUST_E_CERT_SIGNATURE` (0x80096004) → firmado inválido; `TRUST_E_NOSIGNATURE` → sin firma; cualquier otro error → `None` (indeterminado) → UNKNOWN sin cachear. Clave de cache `(path, mtime_ns, size)` con `os.stat` (si falla stat → UNKNOWN sin cachear).

### B5 (Important) Apagar GeoIP no corta la cola
`geoip_ipapi.py` worker sigue drenando la cola tras desactivar GeoIP (README promete lo contrario).
- [ ] Test: encolar N IPs, `set_enabled(False)` (o `cancel_pending()`) → el worker no hace ninguna request más; `_queued` vacío.
- [ ] Fix: método `cancel_pending()` en `IpApiGeoIp` (bajo el lock: vaciar `_q` y `_queued`) + flag `_enabled` chequeado antes de cada `_query`; `MonitorService.update_settings` lo llama cuando `geoip_enabled` pasa a False (agregar `cancel_pending` al puerto `GeoIpService` en `src/domain/ports.py` con implementación no-op en fakes).

### B6 (Minor, barato) `_is_public` deja pasar CGNAT/rangos especiales
`geoip_ipapi.py` (~L26): usar `addr.is_global`. Test con `100.64.0.1` → no público.

## Tanda C — UI y docs

### C1 (Minor) Cambio de período muestra frame vacío
`main_window.py` (~L498) + `monitor_service.usage_for_period`: si el período aún no está en el snapshot (devuelve `None`/sentinel), no reconstruir filas; esperar al snapshot. Ajustar `usage_for_period` para distinguir "no calculado" (None) de "vacío" ([]). Test en `tests/test_ui_snapshot.py`.

### C2 (Minor) Tooltip de confianza interpreta HTML
`main_window.py` (~L440): `html.escape` del signer/razones en el tooltip. Test de la función que arma el texto si es extraíble; si no, factorizarla.

### C3 (docs) Exactitud
- README: gráfico "~1 minuto" (60 puntos × 1 s); `SHA256SUMS.txt` (README y SECURITY.md); "Desactivar GeoIP detiene de inmediato" queda verdadero tras B5.
- CHANGELOG: "acciones de terceros pineadas por SHA"; agregar bullets de esta tanda (A1–A8, B1–B5).
- THIRD_PARTY_LICENSES.md: separar Windows (one-file: Qt no reemplazable in situ; relinkear construyendo desde fuente) de macOS (onedir: frameworks Qt reemplazables en `NetGauge.app/Contents/Frameworks`).
- Verificación: `python -c` que asserte cada string.

## Diferidos (no entran en este pase)

- Badge "modo degradado" en la UI cuando `FallbackCaptureService.degraded` (requiere i18n + diseño).
- GeoIP cachea errores transitorios para siempre.
- nettop: contador de give-up se resetea con bloques sólo-header.
- `FallbackCaptureService` no re-arrancable / fallback que falla al arrancar.
- `stop()` de nettop/psutil puede volver con el hilo vivo.
- SUM de cuota cada 2 s (performance con meses largos).
- release.yml corre tests sólo en Windows antes de publicar dmgs.
- Pestaña Conexiones sin hook `currentChanged` (pre-existente).
- Prefijo `'` visible en celdas XLSX escapadas.
- Requisito "macOS 12" no verificado contra los wheels de PySide6.
