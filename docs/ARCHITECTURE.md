# Arquitectura

NetLeak sigue **Clean Architecture**: el código se organiza en capas
concéntricas y las dependencias apuntan SIEMPRE hacia el dominio. El dominio no
sabe que existen PySide6, SQLite ni ETW; son detalles intercambiables.

```
presentation ──▶ application ──▶ domain ◀── infrastructure
```

## Capas

### `domain/` — el núcleo
No importa nada externo. Define el lenguaje del problema.

- `models.py`: entidades del negocio — `TrafficSample`, `AppUsage`,
  `UsageRecord`, `Settings`, `QuotaStatus`, `TrustInfo`, `Connection`, los niveles
  de confianza (`TRUST_*`) y el formateador `human_bytes`.
- `ports.py`: interfaces abstractas (puertos) que la infraestructura implementa:
  `CaptureService`, `UsageRepository`, `ReportGenerator`, `Notifier`,
  `SettingsStore`, `TrustEvaluator`, `ConnectionProvider`, `ReputationService`,
  `GeoIpService`.

### `application/` — los casos de uso
- `monitor_service.py`: orquesta el flujo **capturar → acumular → persistir →
  consultar**. Velocidad en vivo, flush periódico, alertas de cuota (diaria/
  mensual), detección de anomalías (picos y apps nuevas), purga por retención,
  índice de confianza por app (enriquecido con VirusTotal) y conexiones activas.
  Recibe un traductor (`set_translator`) para que los avisos respeten el idioma.
  Depende solo de los puertos.

### `infrastructure/` — los detalles concretos
Implementaciones reales de los puertos.

- `capture/etw_capture.py`: captura **por proceso** vía ETW (provider de kernel
  `Microsoft-Windows-Kernel-Network`). Requiere admin + `pywintrace`.
- `capture/psutil_fallback.py`: captura **global** cuando ETW no está disponible.
- `capture/app_names.py`: resuelve el nombre amigable de la app (FileDescription
  vía `version.dll`), con fallback al nombre del ejecutable.
- `capture/factory.py`: decide ETW vs fallback según admin y disponibilidad de
  `pywintrace`. Devuelve `(servicio, es_por_proceso)`.
- `capture/trust.py`: índice de confianza local (firma Authenticode embebida y
  por catálogo vía `WinVerifyTrust`, ubicación del exe, metadata).
- `capture/connections.py`: conexiones activas por proceso (psutil).
- `capture/geoip_ipapi.py`: país/proveedor de IPs remotas (ip-api, opt-in, worker).
- `capture/reputation_virustotal.py`: reputación por hash SHA-256 (VirusTotal, opt-in).
- `persistence/sqlite_repository.py`: SQLite thread-safe, con versión de esquema
  (`PRAGMA user_version`) y framework de migraciones.
- `persistence/settings_store.py`: settings en JSON.
- `reporting/report_generator.py`: informe CSV.
- `update/github_updater.py`: chequeo de versión contra GitHub Releases.

### `presentation/qt/` — la UI (PySide6)
- `app.py`: composición — ventana, `QSystemTrayIcon` (con sparkline), notifier
  thread-safe (señal Qt), instancia única y chequeo de actualización.
- `main_window.py`: ventana frameless con pestañas **Global / Por aplicación /
  Conexiones**, badge de modo (ETW/Global), maximizar y persistencia de geometría.
- `native_window.py`: chrome nativo de Windows (resize desde esquinas + Aero Snap).
- `single_instance.py`: instancia única vía `QLocalServer`/`QLocalSocket`.
- `widgets.py`: gráficos, tarjetas, badges y logo dibujados con `QPainter`.
- `theme.py`: tokens de diseño + generador de QSS (tema claro/oscuro).
- `i18n.py`: traducciones es/en/pt y formato de números por locale.
- `quota_dialog.py` / `settings_dialog.py` / `about_dialog.py`: diálogos modales.

## Por qué ETW y no psutil

`psutil` en Windows expone contadores de red **globales**; su
`Process.io_counters()` mide **disco**, no red. Para saber *qué app* consume
*cuántos bytes* hay que escuchar el provider de kernel de red vía ETW, que emite
un evento por operación TCP/UDP con el PID y los bytes. Eso obliga a correr
elevado y a tener el paquete `etw` (pywintrace) presente.

## Por qué esta arquitectura paga

Las migraciones de UI **tkinter → PyQt6 → PySide6** tocaron **solo**
`presentation/`. El dominio, los casos de uso y la infraestructura ni se
enteraron. (La segunda migración, a PySide6/LGPL, fue por licencia: PyQt6 es
GPL/comercial.) Esa es la recompensa de respetar la regla de dependencia.

## Flujo de datos

```
ETW / psutil ──TrafficSample──▶ MonitorService ──UsageRecord──▶ SQLite
                                      │
                                      ├──▶ velocidad en vivo ──▶ UI (gráfico)
                                      ├──▶ QuotaStatus ──▶ alertas (Notifier)
                                      └──▶ consultas por período ──▶ UI (tablas)
```

Datos persistidos en `%LOCALAPPDATA%\NetLeak\`:
`usage.db`, `settings.json`, `monitor.log`, `reports\`.
