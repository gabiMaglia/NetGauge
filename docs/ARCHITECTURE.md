# Arquitectura

trafficMe sigue **Clean Architecture**: el código se organiza en capas
concéntricas y las dependencias apuntan SIEMPRE hacia el dominio. El dominio no
sabe que existen PyQt6, SQLite ni ETW; son detalles intercambiables.

```
presentation ──▶ application ──▶ domain ◀── infrastructure
```

## Capas

### `domain/` — el núcleo
No importa nada externo. Define el lenguaje del problema.

- `models.py`: entidades inmutables del negocio — `TrafficSample`, `AppUsage`,
  `UsageRecord`, `Settings`, `QuotaStatus`, y el formateador `human_bytes`.
- `ports.py`: interfaces abstractas (puertos) que la infraestructura implementa:
  `CaptureService`, `UsageRepository`, `ReportGenerator`, `Notifier`,
  `SettingsStore`.

### `application/` — los casos de uso
- `monitor_service.py`: orquesta el flujo **capturar → acumular → persistir →
  consultar**. Mantiene la velocidad en vivo, hace flush periódico a disco y
  evalúa las alertas de cuota (diaria y mensual). Depende solo de los puertos.

### `infrastructure/` — los detalles concretos
Implementaciones reales de los puertos.

- `capture/etw_capture.py`: captura **por proceso** vía ETW (provider de kernel
  `Microsoft-Windows-Kernel-Network`). Requiere admin + `pywintrace`.
- `capture/psutil_fallback.py`: captura **global** cuando ETW no está disponible.
- `capture/app_names.py`: resuelve el nombre amigable de la app (FileDescription
  vía `version.dll`), con fallback al nombre del ejecutable.
- `capture/factory.py`: decide ETW vs fallback según admin y disponibilidad de
  `pywintrace`. Devuelve `(servicio, es_por_proceso)`.
- `persistence/sqlite_repository.py`: persistencia en SQLite (thread-safe).
- `persistence/settings_store.py`: settings en JSON.
- `reporting/report_generator.py`: informe CSV.

### `presentation/qt/` — la UI (PyQt6)
- `app.py`: composición de la UI — ventana, `QSystemTrayIcon`, notifier
  thread-safe (señal Qt para marshalear toasts desde el hilo de fondo).
- `main_window.py`: ventana frameless con pestañas **Global** y **Por aplicación**.
- `widgets.py`: gráficos y tarjetas dibujados con `QPainter`.
- `theme.py`: tokens de diseño + generador de QSS (tema claro/oscuro).
- `quota_dialog.py` / `about_dialog.py`: diálogos modales.

## Por qué ETW y no psutil

`psutil` en Windows expone contadores de red **globales**; su
`Process.io_counters()` mide **disco**, no red. Para saber *qué app* consume
*cuántos bytes* hay que escuchar el provider de kernel de red vía ETW, que emite
un evento por operación TCP/UDP con el PID y los bytes. Eso obliga a correr
elevado y a tener el paquete `etw` (pywintrace) presente.

## Por qué esta arquitectura paga

La migración de la UI de **tkinter → PyQt6** tocó **solo** `presentation/`. El
dominio, los casos de uso y la infraestructura ni se enteraron. Esa es la
recompensa de respetar la regla de dependencia.

## Flujo de datos

```
ETW / psutil ──TrafficSample──▶ MonitorService ──UsageRecord──▶ SQLite
                                      │
                                      ├──▶ velocidad en vivo ──▶ UI (gráfico)
                                      ├──▶ QuotaStatus ──▶ alertas (Notifier)
                                      └──▶ consultas por período ──▶ UI (tablas)
```

Datos persistidos en `%LOCALAPPDATA%\NetworkMonitor\`:
`usage.db`, `settings.json`, `monitor.log`, `reports\`.
