#!/bin/bash
# Genera NetGauge-<version>-<arch>.dmg (estilo "arrastrar a Applications")
# a partir del dist/NetGauge.app ya construido por PyInstaller.
#
# Firma y notarización OPCIONALES (opt-in por env vars; sin ellas el .dmg sale
# sin firmar, igual que siempre, y Gatekeeper avisa al usuario final):
#   NETGAUGE_CODESIGN_IDENTITY  "Developer ID Application: Nombre (TEAMID)".
#                               Firma el .app inside-out con hardened runtime +
#                               build/entitlements.plist, lo verifica y firma el .dmg.
#   NETGAUGE_NOTARY_PROFILE     perfil de Keychain de `xcrun notarytool
#                               store-credentials`, o bien el trío
#   APPLE_ID + APPLE_TEAM_ID + APPLE_APP_PASSWORD (contraseña de app específica).
#                               Notariza el .dmg, lo engrapa (stapler) y lo valida.
# La notarización requiere la firma (NETGAUGE_CODESIGN_IDENTITY).
# Detalle en build/README_macos.md, "Firma y notarización (opcional)".
#
# Uso (desde la raíz del repo, en un Mac, tras compilar el spec):
#   pyinstaller build/network_monitor_macos.spec --noconfirm
#   build/make_dmg.sh                 # autodetecta arch nativa (uname -m)
#   build/make_dmg.sh arm64           # fuerza el sufijo de arch del .dmg
#   build/make_dmg.sh x86_64
#
# La versión del nombre del .dmg sale de DMG_VERSION si está definida (CI la
# inyecta con la versión del git tag); sin esa env var (build local) se lee
# de src/version.py (fuente única) vía build/gen_version_info.py.
#
# Requiere macOS (usa hdiutil, no portable a Linux/Windows).
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[make_dmg] Este script requiere macOS (usa hdiutil)." >&2
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="NetGauge"
VERSION="${DMG_VERSION:-$(cd "$ROOT_DIR" && python3 build/gen_version_info.py --print-version)}"
if [[ -z "$VERSION" ]]; then
    echo "[make_dmg] No se pudo determinar la versión (src/version.py)." >&2
    exit 1
fi
ARCH="${1:-$(uname -m)}"

if [[ "$ARCH" != "x86_64" && "$ARCH" != "arm64" ]]; then
    echo "[make_dmg] Arch inválida: '$ARCH' (esperado x86_64 o arm64)" >&2
    exit 1
fi

APP_BUNDLE="$ROOT_DIR/dist/${APP_NAME}.app"
OUT_DIR="$ROOT_DIR/dist"
DMG_NAME="${APP_NAME}-${VERSION}-${ARCH}.dmg"
DMG_PATH="$OUT_DIR/$DMG_NAME"
STAGING_DIR="$(mktemp -d)"

if [[ ! -d "$APP_BUNDLE" ]]; then
    echo "[make_dmg] No se encontró $APP_BUNDLE." >&2
    echo "[make_dmg] Corré primero: pyinstaller build/network_monitor_macos.spec --noconfirm" >&2
    exit 1
fi

cleanup() { rm -rf "$STAGING_DIR"; }
trap cleanup EXIT

IDENTITY="${NETGAUGE_CODESIGN_IDENTITY:-}"
ENTITLEMENTS="$ROOT_DIR/build/entitlements.plist"

# NOTARIZE como flag aparte: con `set -u`, expandir un array vacío falla en el
# bash 3.2 que trae macOS.
NOTARIZE=0
if [[ -n "${NETGAUGE_NOTARY_PROFILE:-}" ]]; then
    NOTARIZE=1
    NOTARY_AUTH=(--keychain-profile "$NETGAUGE_NOTARY_PROFILE")
elif [[ -n "${APPLE_ID:-}" && -n "${APPLE_TEAM_ID:-}" && -n "${APPLE_APP_PASSWORD:-}" ]]; then
    NOTARIZE=1
    NOTARY_AUTH=(--apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_PASSWORD")
fi

if [[ "$NOTARIZE" == 1 && -z "$IDENTITY" ]]; then
    echo "[make_dmg] Hay credenciales de notarización pero falta NETGAUGE_CODESIGN_IDENTITY:" >&2
    echo "[make_dmg] Apple solo notariza binarios firmados con Developer ID." >&2
    exit 1
fi

sign() {
    codesign --force --options runtime --timestamp \
        --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" "$1"
}

# Firma inside-out (Apple desaconseja `codesign --deep` para firmar): primero
# cada Mach-O anidado (.dylib/.so/ejecutables), del más profundo al menos
# profundo, después los .framework, y al final el .app.
sign_app_inside_out() {
    local app="$1" f
    while IFS= read -r f; do
        if file -b "$f" | grep -q "Mach-O"; then
            sign "$f"
        fi
    done < <(find "$app/Contents" -type f \
                \( -name "*.dylib" -o -name "*.so" -o -perm -u+x \) \
                ! -path "$app/Contents/MacOS/$APP_NAME" \
             | awk -F/ '{ print NF "\t" $0 }' | sort -rn | cut -f2-)
    while IFS= read -r f; do
        sign "$f"
    done < <(find "$app/Contents" -type d -name "*.framework" \
             | awk -F/ '{ print NF "\t" $0 }' | sort -rn | cut -f2-)
    sign "$app"
}

echo "[make_dmg] Preparando staging para $DMG_NAME ..."
cp -R "$APP_BUNDLE" "$STAGING_DIR/${APP_NAME}.app"
ln -s /Applications "$STAGING_DIR/Applications"

if [[ -n "$IDENTITY" ]]; then
    if [[ ! -f "$ENTITLEMENTS" ]]; then
        echo "[make_dmg] No se encontró $ENTITLEMENTS." >&2
        exit 1
    fi
    echo "[make_dmg] Firmando ${APP_NAME}.app (Developer ID, hardened runtime) ..."
    sign_app_inside_out "$STAGING_DIR/${APP_NAME}.app"
    codesign --verify --deep --strict --verbose=2 "$STAGING_DIR/${APP_NAME}.app"
fi

rm -f "$DMG_PATH"
mkdir -p "$OUT_DIR"

echo "[make_dmg] Generando $DMG_PATH ..."
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

if [[ -z "$IDENTITY" ]]; then
    echo "[make_dmg] OK -> $DMG_PATH"
    echo "[make_dmg] Nota: .dmg sin firmar/notarizar (definí NETGAUGE_CODESIGN_IDENTITY para firmar)."
    echo "[make_dmg]       Gatekeeper avisará 'app no verificada' al abrirla."
    exit 0
fi

echo "[make_dmg] Firmando $DMG_NAME ..."
codesign --force --sign "$IDENTITY" --timestamp "$DMG_PATH"
codesign --verify --verbose=2 "$DMG_PATH"

if [[ "$NOTARIZE" != 1 ]]; then
    echo "[make_dmg] OK -> $DMG_PATH (firmado, SIN notarizar: faltan credenciales de notarytool)."
    exit 0
fi

echo "[make_dmg] Enviando $DMG_NAME a notarización (puede tardar varios minutos) ..."
# Se captura la salida aunque notarytool salga con error, para poder leer el
# id y pedir el log; el veredicto lo decide el campo "status".
NOTARY_JSON="$(xcrun notarytool submit "$DMG_PATH" "${NOTARY_AUTH[@]}" --wait --output-format json)" || true
notary_field() {
    printf '%s' "$NOTARY_JSON" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get(sys.argv[1], ""))
except ValueError:
    print("")
' "$1"
}
NOTARY_ID="$(notary_field id)"
NOTARY_STATUS="$(notary_field status)"
echo "[make_dmg] Notarización $NOTARY_ID: $NOTARY_STATUS"
if [[ "$NOTARY_STATUS" != "Accepted" ]]; then
    echo "[make_dmg] La notarización no fue aceptada. Log de Apple:" >&2
    if [[ -n "$NOTARY_ID" ]]; then
        xcrun notarytool log "$NOTARY_ID" "${NOTARY_AUTH[@]}" >&2 || true
    fi
    exit 1
fi

echo "[make_dmg] Engrapando el ticket de notarización ..."
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"
spctl -a -t open --context context:primary-signature -v "$DMG_PATH"

echo "[make_dmg] OK -> $DMG_PATH (firmado y notarizado)"
