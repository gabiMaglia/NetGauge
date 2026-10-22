# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Network Monitor (macOS, app bundle .app).
#
# Build (en un Mac, arquitectura nativa del runner -- PyInstaller NO
# cross-compila x86_64<->arm64, cada arch se buildea en su propio runner;
# eso lo cubre T-004 con macos-15-intel (Intel) y macos-14 (Apple Silicon)):
#   pyinstaller build/network_monitor_macos.spec --noconfirm
#
# Para forzar explícitamente la arquitectura del bundle resultante (debe
# coincidir con el Python/runner que está corriendo pyinstaller):
#   TARGET_ARCH=x86_64 pyinstaller build/network_monitor_macos.spec --noconfirm
#   TARGET_ARCH=arm64  pyinstaller build/network_monitor_macos.spec --noconfirm
# Sin la env var, se autodetecta con platform.machine() (build nativo).
#
# Firma opcional (Developer ID): si está definida la env var
# NETGAUGE_CODESIGN_IDENTITY (p.ej. "Developer ID Application: Nombre (TEAMID)"),
# PyInstaller firma el bundle con esa identidad, hardened runtime y
# build/entitlements.plist. Sin la env var, comportamiento de siempre: firma
# ad-hoc de PyInstaller, .app sin firma de desarrollador (Gatekeeper avisa).
# La firma definitiva (inside-out + verificación) y la notarización las hace
# build/make_dmg.sh; ver build/README_macos.md, "Firma y notarización".
import os
import platform
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Version unica: se parsea src/version.py (sin importar el paquete src/Qt).
sys.path.insert(0, SPECPATH)  # noqa: F821  (SPECPATH lo inyecta PyInstaller)
from gen_version_info import read_app_version  # noqa: E402

APP_VERSION = read_app_version()

block_cipher = None

# Firma Developer ID opcional (opt-in). None = sin firma de desarrollador.
_codesign_identity = os.environ.get("NETGAUGE_CODESIGN_IDENTITY") or None
_entitlements_file = (
    os.path.join(SPECPATH, "entitlements.plist")  # noqa: F821
    if _codesign_identity
    else None
)

hiddenimports = (
    collect_submodules("PySide6")
    + collect_submodules("reportlab")  # export PDF
    + collect_submodules("openpyxl")   # export Excel (tiene imports dinámicos)
    + ["psutil"]
    + ["keyring.backends.macOS"]  # API key de VirusTotal en el Keychain
    # nettop se invoca como subproceso (src/infrastructure/capture/*nettop*);
    # no es un paquete Python, no requiere hiddenimport. pywintrace/etw son
    # Windows-only: no se listan en hiddenimports para macOS (ETW no importa
    # en darwin, ver capture/factory.py).
)

datas = collect_data_files("reportlab")
# Fuente de marca bundleada (Plus Jakarta Sans) -> assets/fonts en el bundle;
# la carga load_app_fonts() en runtime para no depender del SO.
datas += [("../assets/fonts", "assets/fonts")]
# Avisos legales (LGPL de PySide6, etc.) dentro del bundle.
datas += [("../THIRD_PARTY_LICENSES.md", "."), ("../PRIVACY.md", ".")]

# Arquitectura objetivo del bundle. PyInstaller no cross-compila: esto solo
# documenta/valida qué se está generando, no cambia el intérprete usado.
_target_arch = os.environ.get("TARGET_ARCH") or platform.machine()
if _target_arch not in ("x86_64", "arm64"):
    raise SystemExit(
        f"TARGET_ARCH inválido: {_target_arch!r} (esperado x86_64 o arm64)"
    )

a = Analysis(
    ["../main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NetGauge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # app de bandeja: sin terminal
    target_arch=_target_arch,
    codesign_identity=_codesign_identity,
    entitlements_file=_entitlements_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="NetGauge",
)

app = BUNDLE(
    coll,
    name="NetGauge.app",
    icon="../assets/icon.icns",
    bundle_identifier="com.gabrielmaglia.netgauge",
    info_plist={
        "CFBundleName": "NetGauge",
        "CFBundleDisplayName": "NetGauge",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "NSHighResolutionCapable": True,
        # App de bandeja: no queremos icono+ventana en el Dock al arrancar
        # (igual criterio que la presentación Windows/T-002, sin forzar
        # accessory mode acá -- la UI/Qt decide su propio comportamiento de
        # ventana; esto solo evita que Finder/LaunchServices la traten como
        # app de ventana principal por defecto).
        "LSUIElement": False,
        "NSHumanReadableCopyright": "(c) 2026 Gabriel Maglia. Licencia MIT.",
    },
)
