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

NetGauge **no tiene telemetría ni analítica**, no crea cuentas y no sube tu
historial de uso. Todo el historial queda en tu equipo. Esto es *exactamente*
lo que puede salir por la red:

| Qué | A quién | Cuándo | Qué se envía |
|---|---|---|---|
| Búsqueda de actualizaciones | `api.github.com` (HTTPS) | En segundo plano al iniciar y periódicamente | Una consulta `GET` a la última release del repo. GitHub ve, como en cualquier request, tu IP y el `User-Agent`. No se envía ningún dato de uso. |
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
