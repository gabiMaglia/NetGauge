# trafficMe

[![CI](https://github.com/gabiMaglia/trafficMe/actions/workflows/ci.yml/badge.svg)](https://github.com/gabiMaglia/trafficMe/actions/workflows/ci.yml)

Monitor de consumo de red para Windows x64. Vive en la bandeja del sistema,
trackea subida/bajada **por aplicación**, persiste el historial en SQLite y
genera un informe CSV al cerrar.

Repo: **https://github.com/gabiMaglia/trafficMe** · UI en **PySide6** (LGPL).

## ⚠️ El punto técnico que tenés que entender

`psutil` **no mide tráfico por proceso** en Windows. Sus contadores de red son
globales y `Process.io_counters()` es de **disco**, no de red.

El desglose real por aplicación se obtiene con **ETW** (Event Tracing for
Windows), provider de kernel `Microsoft-Windows-Kernel-Network`, que emite un
evento por cada operación TCP/UDP con el **PID** y los **bytes**. Eso exige:

1. Ejecutar como **Administrador**.
2. Tener instalado **`pywintrace`** (módulo `etw`).

Si falta cualquiera de los dos, la app cae automáticamente a un **modo global**
(psutil): funciona, pero sin desglose por app. La UI te avisa cuál modo está activo.

## Arquitectura (Clean Architecture)

```
trafficMe/
├─ main.py                      # Composition Root: arma dependencias
├─ requirements.txt             # runtime (PySide6, psutil, pywintrace)
├─ requirements-dev.txt         # + pytest
├─ pytest.ini
├─ build/
│  ├─ network_monitor.spec      # PyInstaller (one-file, uac_admin)
│  ├─ installer.iss             # Inno Setup (instalador x64)
│  ├─ make_icon.py              # genera assets/icon.ico
│  └─ sign.cmd                  # pipeline de firma de código (signtool)
├─ tests/                       # pytest (dominio + aplicación + infra)
└─ src/
   ├─ version.py                # versión + coordenadas del repo (auto-update)
   ├─ domain/                   # Núcleo: NO depende de nada externo
   │  ├─ models.py              # TrafficSample, AppUsage, UsageRecord, Settings,
   │  │                         #   QuotaStatus, TrustInfo, Connection, human_bytes
   │  └─ ports.py               # interfaces: Capture/Repository/Reporter/Notifier/
   │                            #   SettingsStore/TrustEvaluator/ConnectionProvider/
   │                            #   ReputationService/GeoIpService
   ├─ application/
   │  └─ monitor_service.py     # caso de uso: captura→acumula→persiste→consulta,
   │                            #   cuotas, anomalías, retención, confianza, conexiones
   ├─ infrastructure/           # Detalles concretos (implementan ports)
   │  ├─ capture/
   │  │  ├─ etw_capture.py       # ETW por proceso
   │  │  ├─ psutil_fallback.py   # fallback global
   │  │  ├─ factory.py           # elige ETW o fallback según admin/pywintrace
   │  │  ├─ app_names.py         # nombre amigable de la app (version.dll)
   │  │  ├─ trust.py             # índice de confianza (firma Authenticode/ruta)
   │  │  ├─ connections.py       # conexiones activas por proceso (psutil)
   │  │  ├─ geoip_ipapi.py       # país/proveedor de IPs remotas (ip-api, opt-in)
   │  │  └─ reputation_virustotal.py  # reputación por hash (VirusTotal, opt-in)
   │  ├─ persistence/            # sqlite_repository.py (+ versión de esquema),
   │  │                          #   settings_store.py (JSON)
   │  ├─ reporting/report_generator.py   # CSV
   │  └─ update/github_updater.py        # chequeo de versión vs GitHub Releases
   └─ presentation/
      └─ qt/                    # UI PySide6 (frameless, tema claro/oscuro)
         ├─ app.py              # arranque: ventana + tray + notifier + update + sparkline
         ├─ main_window.py      # ventana: tabs Global / Por aplicación / Conexiones
         ├─ native_window.py    # chrome nativo (resize esquinas + Aero Snap)
         ├─ single_instance.py  # instancia única (QLocalServer)
         ├─ widgets.py          # gráficos, tarjetas, badges, logo (QPainter)
         ├─ theme.py            # tokens de diseño + QSS (claro/oscuro)
         ├─ i18n.py             # es/en/pt + formato de números por locale
         ├─ quota_dialog.py · settings_dialog.py · about_dialog.py
```

**Regla de dependencia:** `presentation → application → domain ← infrastructure`.
El dominio no importa nada de afuera; la infraestructura implementa los puertos.

Datos en `%LOCALAPPDATA%\trafficMe\`: `usage.db`, `monitor.log`, `reports\`.

## Ejecutar en desarrollo

```powershell
cd "network Monitor"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Para desglose por app, abrí PowerShell COMO ADMINISTRADOR:
python main.py
```

### Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

## Generar el .exe (PyInstaller)

```powershell
cd "network Monitor"
.\.venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller build\network_monitor.spec --noconfirm
# Resultado: dist\trafficMe.exe  (one-file, pide elevación al abrir)
```

## Generar el instalador (Inno Setup)

1. Instalá Inno Setup 6+ (https://jrsoftware.org/isdl.php).
2. Asegurate de tener `dist\trafficMe.exe` ya compilado.
3. Compilá el instalador:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\installer.iss
# Resultado: build\Output\trafficMe-Setup-<versión>-x64.exe
```

> Detalle completo de firma de código y troubleshooting en [`docs/BUILD.md`](docs/BUILD.md).

El instalador pide privilegios de admin, ofrece autoarranque con Windows y crea
accesos directos.

## Funcionalidades (MVP comercial)

Basadas en lo que ofrecen GlassWire, NetWorx y DU Meter:

- **Consumo por aplicación** (ETW) o global (fallback psutil).
- **Velocidad en vivo** ↑/↓: en la cabecera de la ventana y en el tooltip del tray.
- **Gráfico de ancho de banda en vivo** (últimos ~2 min, subida y bajada).
- **Cuotas diaria y mensual con alertas**: configurás límites en GB y el día de
  corte del ciclo; la app te notifica al 80% y 100% (umbrales configurables).
  Barra de progreso con color (verde / amarillo / rojo). *La feature clave para
  conexiones medidas.* La cuota diaria avisa, no corta el tráfico.
- **Historial Sesión / Día / Semana / Mes** (SQLite).
- **Selector de unidad** Auto / KB / MB / GB.
- **Dashboard en dos vistas**: Global y Por aplicación.
- **Tema claro/oscuro** y ventana sin marco con barra de título propia.
- **Informe CSV / Excel / PDF**: al "Salir", al cierre del sistema (`atexit`) o
  on-demand desde el menú del tray.
- **Settings persistentes** en `settings.json`.
- **Acerca de** con botón de donación (Ko-fi), en la barra de título (ⓘ) y el tray.
- **Multi-idioma**: español, inglés y portugués (cambia en vivo desde Ajustes ⚙).
- **Índice de confianza local** por app: verifica la **firma Authenticode** (embebida
  y por catálogo, vía `WinVerifyTrust`), la **ubicación** del ejecutable y la
  **metadata**. Badge ✓/!/⚠ con el desglose en el tooltip. NO inventa un "%": es un
  veredicto a partir de señales reales y verificables. Se puede apagar en Ajustes.
- **Reputación VirusTotal** (opt-in): con tu API key, consulta el **ratio de
  detección** por SHA-256 (ej. "3/72 motores lo marcan"). Solo se envía el hash,
  nunca el archivo. No bloqueante (worker en segundo plano con throttle del free
  tier). Apagado por defecto.
- **Conexiones activas por aplicación** (IP remota · puerto · estado) vía psutil,
  con **GeoIP/ASN** opt-in (país y proveedor de cada IP remota, vía ip-api.com) y
  toggle para **ocultar conexiones a localhost**.
- **Mini-gráfico (sparkline) en el ícono del tray** + tooltip con velocidad y app top.
- **Alertas de anomalías**: pico de tráfico inusual (≥3× el promedio reciente) y
  apps que empiezan a usar la red por primera vez. Configurable en Ajustes.
- **Indicador de modo de captura** (ETW · por app / Global) en la barra de título,
  para saber si estás viendo desglose real o el fallback global.
- **Maximizar / restaurar** (botón + doble clic en la barra) y **persistencia** de
  posición y tamaño de la ventana entre sesiones.
- **Aviso de actualizaciones** vía GitHub Releases (chequeo en segundo plano; no
  descarga nada, solo te avisa y deja el link).
- **Formato de números por idioma** (es/pt: `1.234,5` · en: `1,234.5`).
- **Disclosure de privacidad** en Ajustes: explica exactamente qué envían VT y GeoIP.
- **Retención del histórico** configurable: purga automática de datos viejos para
  que `usage.db` no crezca sin techo.

Archivos en `%LOCALAPPDATA%\trafficMe\`: `usage.db`, `settings.json`,
`monitor.log`, `reports\`.

## Apoyar el proyecto ☕

trafficMe es software libre y gratuito. Si te resulta útil, podés invitar un café:

**[ko-fi.com/gabrielmaglia](https://ko-fi.com/gabrielmaglia)**

El botón también está dentro de la app, en **Acerca de** (ícono ⓘ de la barra de
título, o el menú del ícono de bandeja).

## Licencia

Distribuido bajo licencia **MIT** — software libre. Podés usar, modificar y
redistribuir, conservando el aviso de copyright. Ver [LICENSE](LICENSE).

### Licencias de terceros (importante para distribución)

- **PySide6** — LGPLv3. Elegido a propósito sobre PyQt6 (GPL/comercial) porque
  **permite distribución gratuita y comercial / closed-source**. La app se enlaza
  dinámicamente con Qt; se puede reemplazar la librería Qt del bundle.
- **psutil** — BSD-3. **pywintrace** — BSD.
- **VirusTotal (API pública)** e **ip-api.com (free)**: ambos prohíben el uso
  **comercial** en su free tier. Si en el futuro se vende la app, esas dos
  funciones (opt-in) requieren plan de pago o quedar deshabilitadas en la build
  comercial. El resto de la app no tiene esa restricción.

Más documentación en [`docs/`](docs/): arquitectura y guía de build.
