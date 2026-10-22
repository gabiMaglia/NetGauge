# Política de privacidad / Privacy policy

*Español primero, [English below](#english).*

## Español

**NetGauge** es software libre (MIT) mantenido por Gabriel Maglia
([@gabiMaglia](https://github.com/gabiMaglia)). No tiene telemetría ni
analítica, no crea cuentas y no sube tu historial de uso. Todo el historial
queda en tu equipo.

> Este programa no transferirá ninguna información a otros sistemas en red a
> menos que el usuario, o quien lo instala u opera, lo solicite de forma
> específica.

### Qué sale por la red (lista completa)

| Qué | A quién | Cuándo | Qué se envía | ¿Se puede desactivar? |
|---|---|---|---|---|
| Búsqueda de actualizaciones | `api.github.com` (HTTPS) | Automático (**activado por defecto**): al iniciar la app y luego cada 24 h | Un `GET` a `/repos/gabiMaglia/NetGauge/releases/latest`. GitHub ve, como en cualquier request, tu IP y el `User-Agent: NetGauge-updater`. No se envía ningún dato de uso. No descarga ni instala nada: solo avisa si hay una versión más nueva. | Sí: desactivá *Buscar actualizaciones automáticamente* en Ajustes. |
| **GeoIP** | `ip-api.com` por **HTTP sin cifrar** | Solo si activás *GeoIP* en Ajustes (**apagado por defecto**), por cada IP remota nueva de la pestaña Conexiones | La **IP remota** consultada. Al ser HTTP, cualquiera en tu red puede ver esas consultas. El plan gratuito de ip-api.com es solo para uso no comercial. | Sí: desactivá *GeoIP* en Ajustes. |
| **Reputación VirusTotal** | `www.virustotal.com` (HTTPS) | Solo si activás VirusTotal y cargás tu propia API key (**apagado por defecto**) | El **hash SHA-256** del ejecutable de cada app (nunca el archivo) y tu API key en el header `x-apikey`. Al usar "Probar key" se consulta además el hash público de EICAR. La API pública gratuita es solo para uso no comercial. | Sí: desactivá VirusTotal en Ajustes. |

**Nota sobre la búsqueda de actualizaciones:** viene activada por defecto y es
una única consulta HTTPS de solo lectura a GitHub. Podés desactivarla en
Ajustes (*Buscar actualizaciones automáticamente*); el cambio se aplica al
instante, sin reiniciar, y si la volvés a activar se consulta de inmediato.

El índice de confianza (firma/ruta del ejecutable) se calcula **localmente** y
no envía nada.

### Qué se guarda en tu equipo

| Sistema | Carpeta de datos |
|---|---|
| Windows | `%LOCALAPPDATA%\NetGauge\` |
| macOS | `~/Library/Application Support/NetGauge/` |

- `usage.db`: historial de consumo por aplicación (SQLite). Retención
  configurable, 180 días por defecto.
- `settings.json`: tus preferencias.
- `netgauge.log`: registro de diagnóstico local.
- `reports\`: informes que exportes (CSV, Excel, PDF).
- **API key de VirusTotal:** se guarda en el almacén de credenciales del
  sistema (Administrador de credenciales de Windows / Llavero de macOS), bajo el
  servicio `NetGauge`, no en `settings.json`. Solo si ese almacén no está
  disponible se guarda en texto plano en `settings.json` (con un aviso en el
  log); en ese caso cualquier proceso o usuario con acceso a tu carpeta de datos
  puede leerla.

Borrar la carpeta de datos elimina todo lo que NetGauge guardó (la credencial
de VirusTotal se borra desde el almacén de credenciales del sistema).

### Contacto

Dudas de privacidad: abrí un issue en
<https://github.com/gabiMaglia/NetGauge/issues>. Vulnerabilidades: ver
[`SECURITY.md`](SECURITY.md).

---

## English

**NetGauge** is free software (MIT) maintained by Gabriel Maglia
([@gabiMaglia](https://github.com/gabiMaglia)). It has no telemetry or
analytics, creates no accounts and never uploads your usage history. All
history stays on your machine.

> This program will not transfer any information to other networked systems
> unless specifically requested by the user or the person installing or
> operating it.

### What goes over the network (complete list)

| What | To whom | When | What is sent | Can it be disabled? |
|---|---|---|---|---|
| Update check | `api.github.com` (HTTPS) | Automatic (**on by default**): at app start, then every 24 h | A `GET` to `/repos/gabiMaglia/NetGauge/releases/latest`. GitHub sees, as with any request, your IP and the `User-Agent: NetGauge-updater`. No usage data is sent. It downloads and installs nothing: it only notifies you of a newer version. | Yes: turn off *Check for updates automatically* in Settings. |
| **GeoIP** | `ip-api.com` over **unencrypted HTTP** | Only if you enable *GeoIP* in Settings (**off by default**), for each new remote IP in the Connections tab | The queried **remote IP**. Being HTTP, anyone on your network can see those lookups. ip-api.com's free plan is for non-commercial use only. | Yes: turn *GeoIP* off in Settings. |
| **VirusTotal reputation** | `www.virustotal.com` (HTTPS) | Only if you enable VirusTotal and enter your own API key (**off by default**) | The **SHA-256 hash** of each app's executable (never the file) and your API key in the `x-apikey` header. "Test key" also queries the public EICAR hash. The free public API is for non-commercial use only. | Yes: turn VirusTotal off in Settings. |

**Note on the update check:** it is on by default and is a single read-only
HTTPS request to GitHub. You can turn it off in Settings (*Check for updates
automatically*); the change applies immediately, without a restart, and
turning it back on checks right away.

The trust index (executable signature/path) is computed **locally** and sends
nothing.

### What is stored on your machine

| System | Data folder |
|---|---|
| Windows | `%LOCALAPPDATA%\NetGauge\` |
| macOS | `~/Library/Application Support/NetGauge/` |

- `usage.db`: per-application usage history (SQLite). Retention is
  configurable, 180 days by default.
- `settings.json`: your preferences.
- `netgauge.log`: local diagnostic log.
- `reports\`: reports you export (CSV, Excel, PDF).
- **VirusTotal API key:** stored in the operating system credential store
  (Windows Credential Manager / macOS Keychain) under the service `NetGauge`,
  not in `settings.json`. Only if that store is unavailable is it saved as plain
  text in `settings.json` (with a log warning); in that case any process or user
  with access to your data folder can read it.

Deleting the data folder removes everything NetGauge stored (remove the
VirusTotal credential from the OS credential store separately).

### Contact

Privacy questions: open an issue at
<https://github.com/gabiMaglia/NetGauge/issues>. Vulnerabilities: see
[`SECURITY.md`](SECURITY.md).
