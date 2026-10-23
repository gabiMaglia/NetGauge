# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/);
versionado [SemVer](https://semver.org/lang/es/).

## [Unreleased]

## [2.0.5] - 2026-10-23
### Changed
- **Rediseño de la UI.** Header con velocidad de bajada/subida en vivo (anchos
  fijos, sin saltos) y botón de cerrar con ícono blanco en hover; una sola fila
  de navegación (pestañas + período + unidad); pestaña *Global* con tarjetas con
  tendencia, gráfico con ejes y tooltip, y tarjetas de límite diario/mensual
  (reemplazan al botón *Cuota*); pestaña *Por aplicación* con íconos, búsqueda,
  orden, velocidad actual y porcentaje del total; pestaña *Conexiones* como tabla
  con filtros y estado vacío; barra de estado; tipografía JetBrains Mono para
  cifras; tema claro con texto de contraste AA; ancho mínimo de ventana 780 px.

## [2.0.4] - 2026-10-22
### Fixed
- **macOS:** `nettop` consumía ~100-120 % de CPU permanente mientras NetGauge
  estaba abierta. Causa: el modo streaming (`-L 0`) mantiene una suscripción
  persistente a NetworkStatistics que procesa cada evento de cada flow del
  kernel. Ahora se hace polling de snapshots one-shot (`nettop -L 1`, cada 2 s,
  ~0.08 s de CPU c/u): ~4-5 % de un core con la misma exactitud (10 MB medidos
  como 10.02 MB). Limitación: flows que nacen y mueren entre dos snapshots no
  se ven. La tasa en vivo se suaviza ahora sobre 4 lecturas (cadencia de 2 s).
- Docs: la sección *Code signing policy* del README atribuía la firma a SignPath
  Foundation, pero nunca se aprobó ni se usó. Ahora refleja el estado real:
  macOS firmado y notarizado (Apple Developer ID), Windows sin firmar.

## [2.0.3] - 2026-10-22
### Added
- **macOS:** firma *Developer ID* (hardened runtime + `build/entitlements.plist`)
  y notarización de Apple **opcionales** en el build: `build/make_dmg.sh` firma
  el `.app` inside-out, firma, notariza y engrapa el `.dmg` cuando hay
  credenciales (`NETGAUGE_CODESIGN_IDENTITY`, `NETGAUGE_NOTARY_PROFILE` o
  `APPLE_ID`/`APPLE_TEAM_ID`/`APPLE_APP_PASSWORD`), y el workflow de release lo
  hace si existen los secrets de Apple. Sin credenciales el `.dmg` sale sin
  firmar, igual que antes. Pasos en `build/README_macos.md`.
### Fixed
- **Windows:** crash potencial en la verificación de firma (llamadas `ctypes`
  sin tipos de retorno/argumentos y fuga de contexto de certificado) y la
  colección de tests ya no falla en Windows por un `import pty` a nivel de módulo.
- Persistencia: el historial ahora se **agrega por (app, minuto)** en vez de
  crecer indefinidamente; migración automática que consolida las filas
  existentes. `settings.json` se escribe de forma atómica y tolera archivos
  corruptos (respaldo en `settings.json.bak`); la base usa WAL, se recupera de
  corrupción y la purga de retención se hace por lotes.
- Resiliencia: los ciclos de captura/cuotas se reprograman aunque falle un tick,
  no se pierde el lote pendiente si falla el guardado, `stop()` espera el tick
  en curso, y los hilos de captura (ETW, nettop, psutil) ya no mueren en
  silencio: se degrada a psutil si la captura nativa falla.
- Conexiones y confianza: la ruta del ejecutable se resuelve por ruta y el
  veredicto de confianza es el **peor** entre ejecutables homónimos; la caché de
  nombres por PID se invalida por `create_time`.
- Rendimiento de la UI: firma/ruta de ejecutables, conexiones, cuotas y
  períodos se calculan fuera del hilo de la interfaz (sin congelamientos con
  muchas apps).
- Release: la versión sale de una única fuente (`src/version.py`) en el
  instalador, el `.exe`, los specs y los `.dmg`.
- Instancia única **por usuario** (antes, con RDP/cambio de usuario, la 2ª sesión no podía abrir la app).
- VirusTotal/GeoIP: un lookup encolado justo cuando el worker se apagaba por inactividad ya no queda trabado.
- VirusTotal: los errores transitorios (429/5xx/401/403/red) se reintentan con espera; cambiar la API key limpia errores previos.
- "Probar key" de VirusTotal nunca se cuelga ante errores de red.
- Informes: CSV con BOM (acentos correctos en Excel) y ya no se escribe en el Escritorio por defecto.
- La ventana ya no reaparece fuera de pantalla si se desconectó el monitor donde estaba.
- Comparación de versiones (`2.0` = `2.0.0`).
- Persistencia: `save_batch` con rollback ya no duplica bytes y los cambios de ajustes no re-disparan alertas de cuota.
- Arranque: los fallos de inicio se registran en `netgauge.log` y se muestran en un cuadro de mensaje (best-effort); el chequeo de instancia única ocurre antes de abrir la base.
- Captura: si el consumer de ETW muere en runtime, un watchdog lo detecta y se degrada a psutil.
- VirusTotal: repetir `set_api_key` con la misma key ya no anula el backoff.
- Confianza: el nombre del firmante resuelve el certificado real (Issuer+Serial) en vez de la CA; los errores de IO de WinVerifyTrust dan *desconocido* (no sospechoso) y no se cachean; la caché de confianza se indexa por (ruta, mtime, tamaño).
- GeoIP: apagarlo descarta la cola pendiente (a lo sumo se completa la única consulta ya en vuelo) y se descartan rangos no globales (CGNAT).
- UI: cambiar de período espera al snapshot en vez de mostrar un frame vacío.
### Security
- La **API key de VirusTotal** ya no se guarda en `settings.json`: se almacena en
  el almacén de credenciales del SO (Credential Manager / Keychain) vía
  `keyring`, con migración automática desde texto plano; si el almacén no está
  disponible se mantiene el texto plano como fallback (con aviso en el log).
- El tooltip de confianza escapa HTML del firmante/razones.
- Comparaciones de rutas de confianza con separador (evita falsos positivos
  tipo `C:\Windows` vs `C:\WindowsEvil`).
- Aviso explícito en Ajustes de que GeoIP envía IPs por **HTTP sin cifrar** a
  ip-api.com.
- Pipeline de release con gate de tests, permisos mínimos, acciones de terceros
  pineadas por SHA y `SHA256SUMS.txt`; CI con `pip-audit` y Dependabot.
- "Probar key" de VirusTotal ya no manda la clave en la URL (solo en el header).
- Informes: escape de fórmulas (`=`, `+`, `-`, `@`) y nombre de archivo sanitizado (sin path traversal).
- Nombres de app y datos GeoIP se muestran como texto plano.
### Changed
- Política de privacidad: nuevo `PRIVACY.md` (fuente de verdad) que el instalador
  de Windows muestra durante la instalación y se empaqueta en los bundles; el
  README suma la sección *Code signing policy* e
  instrucciones de desinstalación, y la landing enlaza la política.
- README reescrito (descarga, requisitos, aviso de firma, privacidad y datos
  locales); nuevos `THIRD_PARTY_LICENSES.md` (incluido en el instalador y los
  bundles) y `SECURITY.md`; `.gitignore` ignora `.env*`, `*.pfx`, `*.p12`.
- El log ahora es `netgauge.log` con rotación.
- `pyinstaller` pasa a dependencias de desarrollo y los majors de las
  dependencias quedan acotados.
- Chequeo de actualizaciones cada 24 h; el aviso es clicable y abre la release.
- La búsqueda automática de actualizaciones (api.github.com) ahora se puede
  desactivar en Ajustes (*Buscar actualizaciones automáticamente*); sigue
  activada por defecto y el cambio aplica sin reiniciar. `PRIVACY.md` y el
  README reflejan la nueva opción.
- Se conservan solo los últimos 20 informes en `reports/`.
- "Acerca de" ya no dice "para Windows" (también macOS).

## [2.0.1] - 2026-06-24
### Fixed
- **macOS:** los procesos `nettop` ya no quedan huérfanos al cerrar la app de
  forma no-limpia (se acumulaban en la lista de procesos). Se limpian al
  arrancar y ante SIGTERM/SIGINT.
- **macOS:** los nombres de apps con caracteres raros o "rectángulos vacíos"
  (nombres que `nettop` truncaba) ahora se muestran completos.
- La barra de título y el "Acerca de" decían "trafficMe" (residuo del rebrand);
  ahora dicen **NetGauge**.
### Changed
- El helper interno (`nettop`) ya no aparece en la lista "Por aplicación".
- Se **bundlea la tipografía Plus Jakarta Sans** con la app, así se ve igual sin
  depender de que el sistema la tenga instalada.

## [2.0.0] - 2026-06-23
### Changed
- **Rebrand completo: la app ahora se llama NetGauge.** Cambian el ejecutable,
  el instalador, la identidad de la app y la carpeta de datos
  (`%LOCALAPPDATA%\NetGauge`, `~/Library/Application Support/NetGauge`).
### Added
- **Migración automática del historial** desde instalaciones previas: al
  actualizar, se copia tu `usage.db`, settings, log y reportes a la carpeta
  nueva (no perdés tu historial).
- Soporte macOS (Intel + Apple Silicon) y release multiplataforma (.exe + .dmg).

## [1.8.0] - 2026-06-17
### Added
- Export de informes en **Excel (.xlsx)** y **PDF**, además de CSV (menú del tray).
- Toggle **"Ocultar localhost"** en la pestaña Conexiones (filtra 127.0.0.1/::1),
  persistente.

## [1.7.1] - 2026-06-17
### Added
- Metadata del editor embebida en el `.exe` (CompanyName/FileDescription).
- CI con GitHub Actions (pytest en windows-latest en cada push/PR).
### Changed
- App renombrada a **NetGauge** de punta a punta (exe, carpeta de instalación,
  tarea programada, carpeta de datos `%LOCALAPPDATA%\NetGauge`).
### Fixed
- Flecha (chevron) de los dropdowns rota.
- El gráfico de ancho de banda no se ocultaba en ventanas de poco alto.

## [1.7.0] - 2026-06-17
### Added
- **Chrome nativo de Windows**: resize desde esquinas + Aero Snap (Win+flechas,
  arrastrar al borde), maximizar nativo.
- Tab Global scrollable; % de cuota visible al pasar el límite.

## [1.5.0] - 2026-06-17
### Added
- Aviso de actualizaciones vía GitHub Releases (chequeo en segundo plano).
- Indicador de modo de captura (ETW / Global) en la barra de título.
- Maximizar/restaurar y persistencia de posición/tamaño de la ventana.
- Pipeline de firma de código (`build/sign.cmd`, listo para certificado).

## [1.4.0] - 2026-06-17
### Changed
- **Migración de PyQt6 (GPL) a PySide6 (LGPL)** para permitir distribución
  gratuita y comercial / closed-source.
### Added
- Suite de tests con pytest (dominio + aplicación + infraestructura).

## [1.3.0] - 2026-06-17
### Added
- GeoIP/ASN (país/proveedor de IPs remotas, opt-in) en Conexiones.
- Mini-gráfico (sparkline) en el ícono del tray.
- Alertas de anomalías (picos de tráfico, apps nuevas en la red).
### Changed
- Conexiones con reconciliación in-place; versión de esquema en la DB;
  disclosure de privacidad; formato de números por idioma.

## [1.2.0] - 2026-06-17
### Added
- Reputación VirusTotal (opt-in, por hash SHA-256).

## [1.1.0] - 2026-06-17
### Added
- Multi-idioma (es/en/pt) con cambio en vivo.
- Índice de confianza local por app (firma Authenticode embebida y por catálogo,
  ubicación, metadata).
- Conexiones activas por aplicación.
- Retención del histórico configurable.

## [1.0.0] - 2026-06-17
### Added
- Versión inicial: consumo por app (ETW) o global (psutil), velocidad en vivo,
  cuotas diaria/mensual con alertas, historial en SQLite, informe CSV, tray,
  tema claro/oscuro, instalador Inno Setup.
