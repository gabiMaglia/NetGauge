# Empaquetado macOS (T-003)

Genera `NetGauge.app` (PyInstaller) y `NetGauge-<version>-<arch>.dmg`
(`hdiutil`). Por defecto sin firmar; la firma *Developer ID* y la
notarización son opcionales (ver [Firma y notarización](#firma-y-notarización-opcional)). No afecta el pipeline Windows
(`network_monitor.spec`, `installer.iss`, `sign.cmd` quedan intactos).

## Requisitos
- macOS (Intel o Apple Silicon).
- `pip install -r requirements.txt` (incluye `pyinstaller` y `Pillow`).

## Pasos (build local, arch nativa del Mac)

```bash
# 1. Icono .icns (una vez, o si cambia el diseño en make_icon.py)
python3 build/make_icon_macos.py

# 2. App bundle .app
pyinstaller build/network_monitor_macos.spec --noconfirm
# -> dist/NetGauge.app

# 3. .dmg (arrastrar a Applications); sin credenciales sale sin firmar
build/make_dmg.sh
# -> dist/NetGauge-1.7.1-<arch>.dmg   (arch = uname -m, o pasala como arg)
```

Para forzar el sufijo de arquitectura del `.dmg` (debe coincidir con la
arch real del `.app` compilado, PyInstaller no cross-compila):

```bash
build/make_dmg.sh arm64
build/make_dmg.sh x86_64
```

## Intel vs ARM
PyInstaller no cross-compila: un Mac Intel solo puede generar el `.app`
x86_64; un Mac Apple Silicon solo arm64 (salvo Python universal2, no usado
aquí). Los dos builds separados se resuelven con dos runners en CI
(`macos-13` x86_64 y `macos-14` arm64) — eso es alcance de **T-004**, no de
este ticket.

## Firma y notarización (opcional)

Sin credenciales el `.dmg` queda **sin firmar** (`codesign`) ni notarizado
(`notarytool`), como en v1 (ADR-001): Gatekeeper muestra "app no verificada" y
el usuario debe permitirla a mano (clic derecho → Abrir, System Settings →
Privacy & Security, o `xattr -dr com.apple.quarantine`).

Con credenciales, `build/make_dmg.sh` firma el `.app` *inside-out* (cada
`.dylib`/`.so`/ejecutable anidado, los `.framework` y por último el `.app`) con
**hardened runtime**, timestamp y [`entitlements.plist`](entitlements.plist),
lo verifica con `codesign --verify --deep --strict`, firma el `.dmg`, lo
notariza (`xcrun notarytool submit --wait`, falla si el estado no es
`Accepted` e imprime el log de Apple), engrapa el ticket (`xcrun stapler
staple`) y lo valida con `spctl`. Un `.dmg` así abre sin advertencias y sin
`xattr`.

> **Requiere el Apple Developer Program pago** (USD 99/año): sin él no se puede
> emitir un certificado *Developer ID Application* ni notarizar.

| Variable | Para qué |
|---|---|
| `NETGAUGE_CODESIGN_IDENTITY` | Identidad de firma, p.ej. `Developer ID Application: Gabriel Maglia (TEAMID)`. Activa la firma (en el spec de PyInstaller y en `make_dmg.sh`). |
| `NETGAUGE_NOTARY_PROFILE` | Perfil del Keychain creado con `xcrun notarytool store-credentials`. Activa la notarización. |
| `APPLE_ID` + `APPLE_TEAM_ID` + `APPLE_APP_PASSWORD` | Alternativa al perfil (la usa CI): Apple ID, Team ID y contraseña de app específica. |

La notarización requiere la firma: si hay credenciales de notarización pero
falta `NETGAUGE_CODESIGN_IDENTITY`, el script falla.

### Build local firmado y notarizado (en el Mac)

1. Instalá el certificado **Developer ID Application** en el llavero *login*
   (developer.apple.com → Certificates → `+` → *Developer ID Application*,
   o desde Xcode → Settings → Accounts → Manage Certificates). Comprobá que
   aparece y copiá el nombre exacto entre comillas:

   ```bash
   security find-identity -v -p codesigning
   #  1) ABCDEF... "Developer ID Application: Gabriel Maglia (TEAMID)"
   ```

2. Generá una **contraseña de app específica** en <https://account.apple.com>
   (Inicio de sesión y seguridad → Contraseñas de apps) y guardá las
   credenciales de notarización en el Keychain (una sola vez):

   ```bash
   xcrun notarytool store-credentials netgauge-notary \
       --apple-id "tu-apple-id@ejemplo.com" \
       --team-id "TEAMID" \
       --password "xxxx-xxxx-xxxx-xxxx"
   ```

3. Buildeá, firmá y notarizá:

   ```bash
   export NETGAUGE_CODESIGN_IDENTITY="Developer ID Application: Gabriel Maglia (TEAMID)"
   export NETGAUGE_NOTARY_PROFILE=netgauge-notary
   python3 build/make_icon_macos.py
   pyinstaller build/network_monitor_macos.spec --noconfirm
   ./build/make_dmg.sh
   ```

   (Si el `.app` ya está compilado alcanza con
   `NETGAUGE_CODESIGN_IDENTITY="Developer ID Application: ... (TEAMID)" NETGAUGE_NOTARY_PROFILE=netgauge-notary ./build/make_dmg.sh`.)

4. Verificá el resultado:

   ```bash
   xcrun stapler validate dist/NetGauge-*.dmg
   spctl -a -t open --context context:primary-signature -v dist/NetGauge-*.dmg
   # -> accepted / source=Notarized Developer ID
   codesign --verify --deep --strict --verbose=2 /Volumes/NetGauge/NetGauge.app   # con el .dmg montado
   spctl -a -t exec -vv /Volumes/NetGauge/NetGauge.app
   ```

### Firma en CI (GitHub Actions)

El job `macos` de `.github/workflows/release.yml` firma y notariza solo si
existen estos secrets (Settings → Secrets and variables → Actions → *New
repository secret*); sin ellos el release sale sin firmar, como siempre:

| Secret | Valor |
|---|---|
| `APPLE_CERTIFICATE_P12_BASE64` | El `.p12` del certificado Developer ID (con su clave privada) en base64. |
| `APPLE_CERTIFICATE_PASSWORD` | La contraseña con la que exportaste el `.p12`. |
| `APPLE_CODESIGN_IDENTITY` | Opcional: `Developer ID Application: Gabriel Maglia (TEAMID)` (si falta, se toma del `.p12`). |
| `APPLE_ID` | Apple ID de la cuenta de desarrollador. |
| `APPLE_TEAM_ID` | Team ID (10 caracteres). |
| `APPLE_APP_PASSWORD` | Contraseña de app específica (no la del Apple ID). |

Para obtener el `.p12`: Acceso a Llaveros → *Mis certificados* → clic
derecho sobre *Developer ID Application: …* → **Exportar** → formato `.p12`
con contraseña. Después copialo en base64 al portapapeles y pegalo en el secret:

```bash
base64 -i cert.p12 | pbcopy
rm cert.p12   # no lo dejes suelto (el .gitignore ya ignora *.p12)
```

El workflow importa el certificado en un keychain temporal, exporta
`NETGAUGE_CODESIGN_IDENTITY` para los pasos siguientes (PyInstaller y
`make_dmg.sh`) y borra el keychain al final aunque el job falle.
