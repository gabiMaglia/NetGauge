#!/bin/bash
# Genera trafficMe-<version>-<arch>.dmg (estilo "arrastrar a Applications")
# a partir del dist/trafficMe.app ya construido por PyInstaller.
#
# Sin firmar ni notarizado (ver ADR-001 / T-005 diferido a v2): Gatekeeper
# mostrará advertencia al usuario final; aceptado para v1.
#
# Uso (desde la raíz del repo, en un Mac, tras compilar el spec):
#   pyinstaller build/network_monitor_macos.spec --noconfirm
#   build/make_dmg.sh                 # autodetecta arch nativa (uname -m)
#   build/make_dmg.sh arm64           # fuerza el sufijo de arch del .dmg
#   build/make_dmg.sh x86_64
#
# Requiere macOS (usa hdiutil, no portable a Linux/Windows).
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "[make_dmg] Este script requiere macOS (usa hdiutil)." >&2
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="trafficMe"
VERSION="1.7.1"
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

echo "[make_dmg] Preparando staging para $DMG_NAME ..."
cp -R "$APP_BUNDLE" "$STAGING_DIR/${APP_NAME}.app"
ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$DMG_PATH"
mkdir -p "$OUT_DIR"

echo "[make_dmg] Generando $DMG_PATH (sin firmar) ..."
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "[make_dmg] OK -> $DMG_PATH"
echo "[make_dmg] Nota: .dmg sin firmar/notarizar (ADR-001, T-005 diferido v2)."
echo "[make_dmg]       Gatekeeper avisará 'app no verificada' al abrirla."
