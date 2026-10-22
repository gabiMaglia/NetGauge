# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Network Monitor (Windows x64).
# Build:  pyinstaller build/network_monitor.spec --noconfirm
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Version unica: build/gen_version_info.py parsea src/version.py. Se regenera
# version_info.txt en cada build para que nunca quede desactualizado.
sys.path.insert(0, SPECPATH)  # noqa: F821  (SPECPATH lo inyecta PyInstaller)
from gen_version_info import write_version_info  # noqa: E402

write_version_info(os.path.join(SPECPATH, "version_info.txt"))  # noqa: F821

block_cipher = None

hiddenimports = (
    collect_submodules("PySide6")
    + collect_submodules("etw")   # pywintrace: bundlear TODO el paquete o no hay ETW
    + collect_submodules("reportlab")  # export PDF
    + collect_submodules("openpyxl")   # export Excel (tiene imports dinámicos)
    + ["psutil"]
    + ["keyring.backends.Windows"]  # API key de VirusTotal en Credential Manager
)

# reportlab trae fuentes/recursos que hay que bundlear o falla el export PDF.
datas = collect_data_files("reportlab")
# Fuente de marca bundleada (Plus Jakarta Sans) -> assets/fonts en el bundle;
# la carga load_app_fonts() en runtime para no depender del SO.
datas += [("..\\assets\\fonts", "assets/fonts")]
# Avisos legales (LGPL de PySide6, etc.) dentro del bundle.
datas += [("..\\THIRD_PARTY_LICENSES.md", ".")]

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
