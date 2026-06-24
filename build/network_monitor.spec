# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Network Monitor (Windows x64).
# Build:  pyinstaller build/network_monitor.spec --noconfirm
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

hiddenimports = (
    collect_submodules("PySide6")
    + collect_submodules("etw")   # pywintrace: bundlear TODO el paquete o no hay ETW
    + collect_submodules("reportlab")  # export PDF
    + collect_submodules("openpyxl")   # export Excel (tiene imports dinámicos)
    + ["psutil"]
)

# reportlab trae fuentes/recursos que hay que bundlear o falla el export PDF.
datas = collect_data_files("reportlab")
# Fuente de marca bundleada (Plus Jakarta Sans) -> assets/fonts en el bundle;
# la carga load_app_fonts() en runtime para no depender del SO.
datas += [("..\\assets\\fonts", "assets/fonts")]

a = Analysis(
    ["..\\main.py"],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NetGauge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # app de bandeja: sin consola
    target_arch="x86_64",   # Windows x64
    uac_admin=True,         # solicita elevación (necesario para ETW)
    icon="..\\assets\\icon.ico",
    version="version_info.txt",  # metadata del editor (CompanyName/FileDescription)
)
