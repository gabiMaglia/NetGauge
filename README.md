# NetGauge

[![CI](https://github.com/gabiMaglia/NetGauge/actions/workflows/ci.yml/badge.svg)](https://github.com/gabiMaglia/NetGauge/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)

**Monitor de consumo de red para Windows y macOS.** Vive en la bandeja del
sistema, mide subida y bajada **por aplicación**, guarda el historial en SQLite
y exporta informes en CSV, Excel y PDF.

> **English (short):** NetGauge is a free, open-source (MIT) per-application
> network usage monitor for Windows 10/11 x64 and macOS. System-tray app with
> live bandwidth chart, daily/monthly quotas, history, connection list and
> CSV/XLSX/PDF reports. UI in Spanish, English and Portuguese. Per-app
> breakdown on Windows needs administrator rights (ETW); otherwise it falls
> back to global totals. No telemetry. Optional features that contact third
> parties (GeoIP, VirusTotal) are **off by default** — see
> [Privacidad](#privacidad).

## Descargar

Bajá la última versión desde
**[GitHub Releases](https://github.com/gabiMaglia/NetGauge/releases/latest)**:

| Sistema | Archivo |
|---|---|
| Windows 10/11 x64 | `NetGauge-Setup-<versión>-x64.exe` (instalador) |
| macOS Apple Silicon (M1+) | `NetGauge-<versión>-arm64.dmg` |
| macOS Intel | `NetGauge-<versión>-x86_64.dmg` |

Cada release incluye un archivo `SHA256SUMS.txt` para verificar la descarga.
Sobre la firma de los binarios, ver la [Code signing policy](#code-signing-policy).

### Desinstalar

- **Windows:** *Configuración → Aplicaciones → NetGauge → Desinstalar*, o el
  acceso **Desinstalar NetGauge** del menú Inicio (el instalador lo crea y
  también elimina la tarea de inicio automático). Los datos de usuario
  (`%LOCALAPPDATA%\NetGauge\`) no se borran; podés eliminarlos a mano.
- **macOS:** arrastrá `NetGauge.app` a la Papelera. Opcionalmente borrá
  `~/Library/Application Support/NetGauge` para eliminar el historial y los
  ajustes.

### Aviso de firma (importante)

Los binarios **todavía no están firmados** con certificado de código. Es normal
que el sistema muestre una advertencia la primera vez:

- **Windows (SmartScreen):** "Windows protegió su PC" → **Más información** →
  **Ejecutar de todas formas**.
- **macOS (Gatekeeper):** arrastrá `NetGauge.app` a *Aplicaciones*. Si macOS
  dice que no se puede verificar, hacé clic derecho → **Abrir**, o quitá la
  cuarentena desde Terminal:

  ```bash
  xattr -dr com.apple.quarantine /Applications/NetGauge.app
  ```

  El pipeline de build ya soporta firma *Developer ID* + notarización de Apple
  (opcional, ver [`build/README_macos.md`](build/README_macos.md)). Un `.dmg`
  **firmado y notarizado** abre sin advertencia y **no** necesita el paso de
  `xattr`; los pasos de arriba aplican solo a builds sin firmar. Podés
  comprobarlo con `spctl -a -t open --context context:primary-signature -v NetGauge-*.dmg`
  (debe decir `accepted` y `source=Notarized Developer ID`).

Si preferís no confiar en un binario sin firma, podés compilarlo vos mismo desde
el código fuente: ver [`docs/BUILD.md`](docs/BUILD.md).

## Requisitos

- **Windows:** 10 u 11, x64. Para el desglose **por aplicación** hay que
  ejecutar como **Administrador** (el instalador y el `.exe` piden elevación);
  usa ETW (Event Tracing for Windows). Sin admin la app funciona igual pero en
  **modo global** (totales de la máquina, sin desglose por app) y la ventana
  lo indica.
- **macOS:** 12 (Monterey) o superior, Intel o Apple Silicon. Usa `nettop`
  (incluido en el sistema) para medir por aplicación.
- Para correr desde fuente: Python 3.10+ y las dependencias de
  `requirements.txt`.

## Funciones

- Consumo **por aplicación** (ETW en Windows, `nettop` en macOS) o global (fallback).
- Velocidad en vivo ↑/↓ en la cabecera, gráfico de ancho de banda de los últimos
  ~1 minuto (60 puntos, uno por segundo) y mini-gráfico (sparkline) en el ícono de la bandeja.
- **Cuotas** diaria y mensual con día de corte configurable y alertas al 80 % y
  100 % (umbrales configurables). Avisa, **no corta** el tráfico.
- **Historial** por sesión, día, semana y mes, con retención configurable
  (por defecto 180 días).
- Pestañas **Global**, **Por aplicación** y **Conexiones** (IP remota, puerto,
  estado, por proceso; opción de ocultar localhost).
- **Índice de confianza local** por app (firma Authenticode en Windows,
  ubicación del ejecutable y metadata). Es un veredicto basado en señales
  verificables, no un porcentaje inventado.
- **Alertas de anomalías**: picos inusuales (≥ 3× el promedio reciente) y apps
  que usan la red por primera vez.
- **Informes** CSV, Excel (.xlsx) y PDF: al salir o a pedido desde el menú de la
  bandeja.
- Tema claro/oscuro, selector de unidad (Auto/KB/MB/GB), formato numérico por
  idioma e interfaz en **español, inglés y portugués**.
- Aviso de nuevas versiones (solo avisa; no descarga ni instala nada).
- Opcional (apagado por defecto): **GeoIP** de IPs remotas y **reputación de
  VirusTotal** por hash. Ver [Privacidad](#privacidad).

## Privacidad

> La política completa (fuente de verdad) está en [`PRIVACY.md`](PRIVACY.md); el
> instalador de Windows la muestra durante la instalación. Resumen:

NetGauge **no tiene telemetría ni analítica**, no crea cuentas y no sube tu
historial de uso. Todo el historial queda en tu equipo. Esto es *exactamente*
lo que puede salir por la red:

| Qué | A quién | Cuándo | Qué se envía |
|---|---|---|---|
| Búsqueda de actualizaciones | `api.github.com` (HTTPS) | En segundo plano al iniciar y periódicamente (activado por defecto; se desactiva en Ajustes) | Una consulta `GET` a la última release del repo. GitHub ve, como en cualquier request, tu IP y el `User-Agent`. No se envía ningún dato de uso. |
| **GeoIP** (opcional) | `ip-api.com` por **HTTP sin cifrar** | Solo si activás *GeoIP* en Ajustes (**apagado por defecto**), por cada IP remota nueva de la pestaña Conexiones | La **IP remota** consultada. Al ser HTTP, cualquiera en tu red puede ver esas consultas. El plan gratuito de ip-api.com es **solo para uso no comercial**. |
| **VirusTotal** (opcional) | `www.virustotal.com` (HTTPS) | Solo si activás VirusTotal y cargás tu propia API key (**apagado por defecto**) | Únicamente el **hash SHA-256** del ejecutable; nunca el archivo. La API pública gratuita es solo para uso no comercial. |

Notas:

- La **API key de VirusTotal se guarda en el almacén de credenciales del
  sistema** (Administrador de credenciales de Windows / Llavero de macOS), no
  en `settings.json`. Solo si ese almacén no está disponible se guarda en
  texto plano en `settings.json` (con un aviso en el log); en ese caso
  cualquier proceso o usuario con acceso a tu carpeta de datos puede leerla.
  Usá una key de cuenta gratuita y no la reutilices. Si venías de una versión
  anterior, la key se migra sola al almacén en el primer arranque.
- Desactivar GeoIP o VirusTotal en Ajustes detiene esas consultas. En GeoIP, las
  IPs que estaban en cola se descartan y, a lo sumo, puede completarse la única
  consulta que ya estaba en vuelo.
- El índice de confianza se calcula **localmente**; no envía nada.

## Code signing policy

Política de firma de código / Code signing policy.

| Plataforma / Platform | Estado / Status |
|---|---|
| macOS (`.dmg`) | Firmado con Apple Developer ID y notarizado por Apple (desde v2.0.3). / Signed with an Apple Developer ID and notarized by Apple (since v2.0.3). |
| Windows (`.exe`) | **Sin firmar por ahora.** SmartScreen puede mostrar un aviso: *Más información* → *Ejecutar de todas formas*. / **Not signed yet.** SmartScreen may show a warning: *More info* → *Run anyway*. |

Podés verificar la integridad de cada descarga con `SHA256SUMS.txt`, incluido en
cada release. El código es abierto y se puede auditar y compilar desde el
fuente. / You can verify each download with the `SHA256SUMS.txt` published with
every release. The code is open source and can be audited and built from source.

**Privacy policy / Política de privacidad:** This program will not transfer any
information to other networked systems unless specifically requested by the user
or the person installing or operating it. Concretely, NetGauge only connects to:

- `api.github.com` (HTTPS) — automatic update check at start and every 24 h; sends
  no usage data; on by default, can be turned off in Settings. / búsqueda
  automática de actualizaciones al iniciar y cada 24 h; activada por defecto,
  se desactiva en Ajustes.
- `ip-api.com` (HTTP) — only if you enable *GeoIP* in Settings (off by default);
  sends the remote IP. / solo si activás *GeoIP* (apagado por defecto).
- `www.virustotal.com` (HTTPS) — only if you enable VirusTotal and enter your own
  API key (off by default); sends the executable's SHA-256 hash. / solo si
  activás VirusTotal con tu API key (apagado por defecto).

Details: [`PRIVACY.md`](PRIVACY.md).

> Los binarios publicados en una release pueden estar firmados o no, según la
> versión; los de releases anteriores a la adopción de esta política no lo están
> (ver *Aviso de firma* arriba). / Binaries of releases published before this
> policy was adopted are unsigned (see the signing notice above).

## Datos locales

| Sistema | Carpeta |
|---|---|
| Windows | `%LOCALAPPDATA%\NetGauge\` |
| macOS | `~/Library/Application Support/NetGauge/` |

Contiene `usage.db` (historial), `settings.json` (preferencias; la API key de
VirusTotal queda en el almacén de credenciales del SO), el log (`netgauge.log`) y
`reports\` (informes exportados). Borrar esa carpeta elimina todo lo que
NetGauge guardó.

## Desarrollo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py                          # en Windows, PowerShell como Administrador para ver el desglose por app
```

Tests:

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

La arquitectura (Clean Architecture: `presentation → application → domain ←
infrastructure`) está en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Cómo
generar el `.exe`, el instalador y firmar el código:
[`docs/BUILD.md`](docs/BUILD.md); el `.app`/`.dmg` de macOS:
[`build/README_macos.md`](build/README_macos.md). Historial de cambios:
[`CHANGELOG.md`](CHANGELOG.md).

## Apoyar el proyecto

NetGauge es software libre y gratuito. Si te resulta útil, podés invitar un café:
**[ko-fi.com/gabrielmaglia](https://ko-fi.com/gabrielmaglia)** (también dentro de
la app, en *Acerca de*).

## Seguridad

Para reportar una vulnerabilidad de forma privada, ver [`SECURITY.md`](SECURITY.md).

## Licencia

NetGauge se distribuye bajo licencia **MIT**: ver [LICENSE](LICENSE).

Incluye componentes de terceros (PySide6/Qt bajo **LGPL v3**, psutil, pywintrace,
reportlab, openpyxl, fuentes Plus Jakarta Sans bajo SIL OFL) con sus propias
licencias, y cómo obtener su código fuente / usar tu propia versión de Qt:
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

Los servicios opcionales **ip-api.com** (plan gratuito) y **VirusTotal** (API
pública) restringen su uso a fines **no comerciales**; si redistribuís NetGauge
comercialmente, esas dos funciones requieren plan de pago o deben quedar
deshabilitadas.
