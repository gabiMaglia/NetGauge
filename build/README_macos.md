# Empaquetado macOS (T-003)

Genera `trafficMe.app` (PyInstaller) y `trafficMe-<version>-<arch>.dmg`
(`hdiutil`, sin firmar). No afecta el pipeline Windows
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
# -> dist/trafficMe.app

# 3. .dmg sin firmar (arrastrar a Applications)
build/make_dmg.sh
# -> dist/trafficMe-1.7.1-<arch>.dmg   (arch = uname -m, o pasala como arg)
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

## Sin firma / notarización
El `.dmg` queda sin firmar (`codesign`) ni notarizado (`notarytool`) por
decisión de ADR-001 (sin cuenta Apple Developer en v1). Gatekeeper
mostrará "app no verificada" al abrir; el usuario debe permitir manualmente
(clic derecho → Abrir, o System Settings → Privacy & Security). Firma y
notarización quedan diferidas a **T-005 (v2)**.
