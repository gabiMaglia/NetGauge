"""Genera build/version_info.txt (recurso de version de Windows) desde src/version.py.

src/version.py es la unica fuente de verdad. Este modulo NO importa el paquete
`src` (arrastraria Qt): parsea el texto con regex.

Uso:
    python build/gen_version_info.py                  # escribe build/version_info.txt
    python build/gen_version_info.py --print-version  # imprime la version (p.ej. 2.0.1)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_APP_VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"([^"]*)"\s*$', re.MULTILINE)
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

_TEMPLATE = """\
# Recurso de version embebido en NetGauge.exe (metadata del editor).
# GENERADO por build/gen_version_info.py desde src/version.py. NO editar a mano.
# Lo consume PyInstaller (EXE(version=...)) y lo lee Windows/Explorer y el
# indice de confianza de la app.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=@TUPLE@,
    prodvers=@TUPLE@,
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Gabriel Maglia'),
        StringStruct('FileDescription', 'NetGauge - Monitor de consumo de red'),
        StringStruct('FileVersion', '@DOTTED@'),
        StringStruct('InternalName', 'NetGauge'),
        StringStruct('LegalCopyright', '(c) 2026 Gabriel Maglia. Licencia MIT.'),
        StringStruct('OriginalFilename', 'NetGauge.exe'),
        StringStruct('ProductName', 'NetGauge'),
        StringStruct('ProductVersion', '@DOTTED@')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """'2.0.1' -> (2, 0, 1, 0). Solo X.Y.Z estricto (VS_FIXEDFILEINFO es 4 enteros)."""
    m = _SEMVER_RE.match(version)
    if not m:
        raise ValueError(f"version invalida {version!r}: se espera X.Y.Z (sin sufijos)")
    major, minor, patch = (int(g) for g in m.groups())
    return (major, minor, patch, 0)


def read_app_version(root: Path = ROOT) -> str:
    text = (Path(root) / "src" / "version.py").read_text(encoding="utf-8")
    m = _APP_VERSION_RE.search(text)
    if not m:
        raise ValueError("no se encontro APP_VERSION en src/version.py")
    version = m.group(1)
    version_tuple(version)  # valida el formato
    return version


def render(version: str) -> str:
    tup = version_tuple(version)
    dotted = ".".join(str(n) for n in tup)
    return _TEMPLATE.replace("@TUPLE@", repr(tup)).replace("@DOTTED@", dotted)


def write_version_info(path: Path | None = None, root: Path = ROOT) -> Path:
    target = Path(path) if path is not None else ROOT / "build" / "version_info.txt"
    target.write_text(render(read_app_version(root)), encoding="utf-8", newline="\n")
    return target


def main(argv: list[str]) -> int:
    if argv[1:] == ["--print-version"]:
        print(read_app_version())
        return 0
    if len(argv) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    print(f"[gen_version_info] escrito {write_version_info()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
