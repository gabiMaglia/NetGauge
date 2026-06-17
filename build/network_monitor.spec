# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Network Monitor (Windows x64).
# Build:  pyinstaller build/network_monitor.spec --noconfirm
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = (
    collect_submodules("PySide6")
    + collect_submodules("etw")   # pywintrace: bundlear TODO el paquete o no hay ETW
    + ["psutil"]
)

a = Analysis(
    ["..\\main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="trafficMe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # app de bandeja: sin consola
    target_arch="x86_64",   # Windows x64
    uac_admin=True,         # solicita elevación (necesario para ETW)
    icon="..\\assets\\icon.ico",
)
