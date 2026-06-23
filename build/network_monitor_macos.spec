# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Network Monitor (macOS, app bundle .app).
#
# Build (en un Mac, arquitectura nativa del runner -- PyInstaller NO
# cross-compila x86_64<->arm64, cada arch se buildea en su propio runner;
# eso lo cubre T-004 con macos-13 (Intel) y macos-14 (Apple Silicon)):
#   pyinstaller build/network_monitor_macos.spec --noconfirm
#
# Para forzar explícitamente la arquitectura del bundle resultante (debe
# coincidir con el Python/runner que está corriendo pyinstaller):
#   TARGET_ARCH=x86_64 pyinstaller build/network_monitor_macos.spec --noconfirm
#   TARGET_ARCH=arm64  pyinstaller build/network_monitor_macos.spec --noconfirm
# Sin la env var, se autodetecta con platform.machine() (build nativo).
#
# Importante: NO firma ni notariza (ver ADR-001, T-005 diferido a v2). El
# .app/.dmg resultante están sin firmar; Gatekeeper mostrará advertencia.
import os
import platform

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hiddenimports = (
    collect_submodules("PySide6")
    + collect_submodules("reportlab")  # export PDF
    + collect_submodules("openpyxl")   # export Excel (tiene imports dinámicos)
    + ["psutil"]
    # nettop se invoca como subproceso (src/infrastructure/capture/*nettop*);
    # no es un paquete Python, no requiere hiddenimport. pywintrace/etw son
    # Windows-only: no se listan en hiddenimports para macOS (ETW no importa
    # en darwin, ver capture/factory.py).
)

datas = collect_data_files("reportlab")

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
        "CFBundleShortVersionString": "1.7.1",
        "CFBundleVersion": "1.7.1",
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
