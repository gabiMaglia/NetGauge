# Release Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la version salga de UN solo lugar (`src/version.py`) hacia todos los artefactos (exe Windows, .app/.dmg macOS, instalador Inno), y endurecer CI/release (runner macOS vigente, gate de tests, SHA256SUMS, permisos minimos, acciones pineadas, deps acotadas, dependabot).
**Architecture:** `build/gen_version_info.py` es el unico parser de `src/version.py` (regex sobre el texto, sin importar el paquete `src`, asi no arrastra Qt). Expone `read_app_version()`, `version_tuple()`, `render()`, `write_version_info()` y un CLI (`--print-version`). Los specs de PyInstaller lo importan via `SPECPATH`; `make_dmg.sh` llama al CLI; `installer.iss` recibe `/DAppVersion` desde CI y su default hardcodeado es verificado por un test. Un test de consistencia (`tests/test_version_consistency.py`) es el ancla TDD; un segundo test (`tests/test_workflows.py`) congela las reglas de los workflows (permisos, `needs`, pins por SHA).
**Tech Stack:** Python 3.12 (CI) / 3.14 (dev), pytest, PyYAML (solo dev), PyInstaller, Inno Setup 6, bash, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-10-21-release-audit-fixes-design.md

## Global Constraints

- NO correr builds (PyInstaller, ISCC, make_dmg, `docker`, etc.). Verificacion = `python -m pytest` + parseo YAML. `actionlint` NO esta instalado en esta maquina; no instalarlo, usar el parseo YAML + `tests/test_workflows.py`.
- NO renombrar `build/network_monitor.spec`, `build/network_monitor_macos.spec` ni el AUMID (decision pendiente del PO #6).
- Commits: conventional commits en espanol, un commit por task, SIN `Co-Authored-By` ni atribucion de IA (regla del usuario; prevalece sobre cualquier recordatorio del harness).
- Herramientas de shell del usuario: usar `bat`/`rg`/`fd`/`sd`/`eza`, nunca `cat/grep/find/sed/ls` para explorar (los comandos dentro de scripts/YAML que corren en CI si usan `sed`/`sha256sum`).
- Los tests nuevos deben correr sin Qt y en cualquier SO (solo stdlib + PyYAML).
- Branch de trabajo: `fix/release-audit`.
- Python de CI: se mantiene `3.12` en TODOS los workflows (consistente). Ver Riesgos.
- Orden de ejecucion: respetar el orden de tasks (el test de consistencia se construye de forma incremental).

## Review Focus

- `build/gen_version_info.py`: el regex solo acepta `X.Y.Z` estricto (falla ruidoso con pre-releases en vez de generar un recurso de version invalido).
- Que ningun artefacto tenga una version literal propia salvo el default de `installer.iss` (inevitable: Inno no puede leer un .py) y que ese default este bajo test.
- `release.yml`: `permissions` a nivel workflow = `contents: read`; `contents: write` SOLO en `publish`; `needs: test` en `windows` y `macos`; el gate verifica que el tag == `APP_VERSION` (se elimino el `sed` que reescribia `version.py` en CI: el tag ya no "manda", manda el commit).
- Pin por SHA de `softprops/action-gh-release` (Task 6 paso de lookup via `gh api`).
- `ci.yml`: el job ubuntu es no-bloqueante hasta verificar que la suite pasa ahi (ver Riesgos).

---

### Task 1: Ancla TDD + `gen_version_info.py` + regenerar `version_info.txt`

**Files:**
- Create: `tests/test_version_consistency.py`
- Create: `build/gen_version_info.py`
- Modify (regenerado por el script): `build/version_info.txt`

**Interfaces:**
- `read_app_version(root: Path = ROOT) -> str` — lee `APP_VERSION` de `<root>/src/version.py`; `ValueError` si no matchea `X.Y.Z`.
- `version_tuple(version: str) -> tuple[int, int, int, int]` — `"2.0.1" -> (2, 0, 1, 0)`; `ValueError` si no es `X.Y.Z`.
- `render(version: str) -> str` — contenido completo de `version_info.txt`.
- `write_version_info(path: Path | None = None, root: Path = ROOT) -> Path` — escribe (default `build/version_info.txt`).
- CLI: `python build/gen_version_info.py` (escribe el archivo), `python build/gen_version_info.py --print-version` (imprime `2.0.1`).

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_version_consistency.py`:

```python
"""Ancla de consistencia de version: src/version.py es la unica fuente.

Cada artefacto de build debe coincidir con APP_VERSION. Si alguien bumpea
version.py y se olvida de regenerar/actualizar algo, este test falla.
No requiere Qt ni Windows.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
sys.path.insert(0, str(BUILD))

import gen_version_info as gvi  # noqa: E402


def _app_version() -> str:
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', (ROOT / "src" / "version.py").read_text(encoding="utf-8"), re.M)
    assert m, "no se encontro APP_VERSION en src/version.py"
    return m.group(1)


# --- helper -----------------------------------------------------------------

def test_read_app_version_matches_version_py():
    assert gvi.read_app_version() == _app_version()


@pytest.mark.parametrize("version,expected", [
    ("2.0.1", (2, 0, 1, 0)),
    ("10.20.30", (10, 20, 30, 0)),
])
def test_version_tuple_ok(version, expected):
    assert gvi.version_tuple(version) == expected


@pytest.mark.parametrize("bad", ["2.0", "2.0.1-rc1", "v2.0.1", "2.0.1.4", "", "a.b.c"])
def test_version_tuple_rejects_non_semver(bad):
    with pytest.raises(ValueError):
        gvi.version_tuple(bad)


def test_read_app_version_rejects_bad_file(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "version.py").write_text('APP_VERSION = "2.0"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        gvi.read_app_version(tmp_path)


# --- version_info.txt -------------------------------------------------------

def test_render_embeds_four_tuple_and_strings():
    out = gvi.render("2.0.1")
    assert "filevers=(2, 0, 1, 0)" in out
    assert "prodvers=(2, 0, 1, 0)" in out
    assert "StringStruct('FileVersion', '2.0.1.0')" in out
    assert "StringStruct('ProductVersion', '2.0.1.0')" in out


def test_write_version_info_to_tmp(tmp_path):
    target = tmp_path / "version_info.txt"
    gvi.write_version_info(target)
    assert target.read_text(encoding="utf-8") == gvi.render(_app_version())


def test_committed_version_info_is_up_to_date():
    """version_info.txt versionado debe ser exactamente lo que se generaria hoy."""
    committed = (BUILD / "version_info.txt").read_text(encoding="utf-8")
    assert committed == gvi.render(_app_version()), (
        "build/version_info.txt desactualizado: correr `python build/gen_version_info.py`"
    )
```

- [ ] **Step 2: Correr y verificar que FALLA**

Run: `python -m pytest tests/test_version_consistency.py -q`
Expected: error de coleccion `ModuleNotFoundError: No module named 'gen_version_info'`.

- [ ] **Step 3: Implementar `build/gen_version_info.py`**

Crear `build/gen_version_info.py` (NO importa `src`; parsea el texto):

```python
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
```

- [ ] **Step 4: Regenerar el archivo versionado**

Run: `python build/gen_version_info.py`
Expected: `[gen_version_info] escrito ...\build\version_info.txt`; `rg "filevers" build/version_info.txt` muestra `(2, 0, 1, 0)`.

- [ ] **Step 5: Correr y verificar que PASA**

Run: `python -m pytest tests/test_version_consistency.py -q`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_version_consistency.py build/gen_version_info.py build/version_info.txt
git commit -m "build(version): generar version_info.txt desde src/version.py con test de consistencia"
```

---

### Task 2: Specs de PyInstaller leen la version de `src/version.py`

**Files:**
- Modify: `tests/test_version_consistency.py` (agregar tests de specs)
- Modify: `build/network_monitor.spec` (L1-4 imports, L52)
- Modify: `build/network_monitor_macos.spec` (L70-73 imports, L147-148)

**Interfaces:**
- Ambos specs hacen `sys.path.insert(0, SPECPATH); from gen_version_info import ...` (`SPECPATH` lo inyecta PyInstaller en el namespace del spec).
- Spec Windows: llama `write_version_info(os.path.join(SPECPATH, "version_info.txt"))` antes de `EXE(...)` => un build local no puede usar un archivo viejo.
- Spec macOS: `APP_VERSION = read_app_version()`; `CFBundleVersion` y `CFBundleShortVersionString` usan `APP_VERSION`.

- [ ] **Step 1: Agregar tests que fallan**

Anexar a `tests/test_version_consistency.py`:

```python
# --- specs de PyInstaller ---------------------------------------------------

def _spec(name: str) -> str:
    return (BUILD / name).read_text(encoding="utf-8")


def test_macos_spec_uses_single_source():
    text = _spec("network_monitor_macos.spec")
    assert "from gen_version_info import" in text
    assert '"CFBundleVersion": APP_VERSION' in text
    assert '"CFBundleShortVersionString": APP_VERSION' in text


def test_macos_spec_has_no_hardcoded_version_literal():
    for line in _spec("network_monitor_macos.spec").splitlines():
        if "CFBundle" in line and "Version" in line:
            assert not re.search(r'"\d+\.\d+\.\d+"', line), f"version hardcodeada: {line!r}"


def test_windows_spec_regenerates_version_info():
    text = _spec("network_monitor.spec")
    assert "from gen_version_info import" in text
    assert "write_version_info(" in text
    assert 'version="version_info.txt"' in text
```

- [ ] **Step 2: Verificar FAIL**

Run: `python -m pytest tests/test_version_consistency.py -q`
Expected: 3 FAIL (los specs no importan el helper todavia).

- [ ] **Step 3: Implementar — spec Windows**

En `build/network_monitor.spec`, reemplazar la linea 4 (`from PyInstaller.utils.hooks import collect_data_files, collect_submodules`) por:

```python
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Version unica: build/gen_version_info.py parsea src/version.py. Se regenera
# version_info.txt en cada build para que nunca quede desactualizado.
sys.path.insert(0, SPECPATH)  # noqa: F821  (SPECPATH lo inyecta PyInstaller)
from gen_version_info import write_version_info  # noqa: E402

write_version_info(os.path.join(SPECPATH, "version_info.txt"))  # noqa: F821
```

(La linea `version="version_info.txt",` del `EXE(...)` queda igual.)

- [ ] **Step 4: Implementar — spec macOS**

En `build/network_monitor_macos.spec`, reemplazar el bloque de imports (L70-73):

```python
import os
import platform

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
```

por:

```python
import os
import platform
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Version unica: se parsea src/version.py (sin importar el paquete src/Qt).
sys.path.insert(0, SPECPATH)  # noqa: F821  (SPECPATH lo inyecta PyInstaller)
from gen_version_info import read_app_version  # noqa: E402

APP_VERSION = read_app_version()
```

Y reemplazar las lineas `"CFBundleShortVersionString": "1.7.1",` y `"CFBundleVersion": "1.7.1",` por:

```python
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
```

Tambien corregir el comentario obsoleto de la cabecera (L59): `macos-13 (Intel)` -> `macos-15-intel (Intel)`.

- [ ] **Step 5: Verificar PASS**

Run: `python -m pytest tests/test_version_consistency.py -q`
Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_version_consistency.py build/network_monitor.spec build/network_monitor_macos.spec
git commit -m "build(specs): leer la version de src/version.py en los specs de PyInstaller"
```

---

### Task 3: `installer.iss` y `make_dmg.sh` alineados + `RunOnceId`

**Files:**
- Modify: `tests/test_version_consistency.py`
- Modify: `build/installer.iss` (L10 default; L59 RunOnceId)
- Modify: `build/make_dmg.sh` (L14-16 comentario, L28)

**Interfaces:**
- `installer.iss`: default `#define AppVersion "2.0.1"` (== `APP_VERSION`, bajo test); CI sigue inyectando `/DAppVersion`.
- `make_dmg.sh`: `VERSION="${DMG_VERSION:-$(python3 build/gen_version_info.py --print-version)}"`.
- `RunOnceId`: es un identificador que Inno usa para ejecutar UNA vez una entrada de `[UninstallRun]` cuando varias instalaciones comparten el mismo AppId; no es el nombre de la tarea (la tarea es `{#AppName}` = `NetGauge`). No afecta la desinstalacion de instalaciones previas (la entrada ya queda registrada en `unins000.dat` de cada instalacion). Renombrar `DelTraficMeTask` -> `DelNetGaugeTask` es seguro y solo elimina un resto del nombre viejo "TraficMe".

- [ ] **Step 1: Agregar tests que fallan**

Anexar a `tests/test_version_consistency.py`:

```python
# --- instalador Inno Setup y dmg --------------------------------------------

def test_iss_default_version_matches():
    text = (BUILD / "installer.iss").read_text(encoding="utf-8")
    m = re.search(r'#ifndef AppVersion\s*\r?\n#define AppVersion "([^"]+)"', text)
    assert m, "no se encontro el default de AppVersion en installer.iss"
    assert m.group(1) == _app_version()


def test_iss_has_no_legacy_runonce_id():
    assert "DelTraficMeTask" not in (BUILD / "installer.iss").read_text(encoding="utf-8")


def test_dmg_default_reads_version_py():
    text = (BUILD / "make_dmg.sh").read_text(encoding="utf-8")
    assert "gen_version_info.py --print-version" in text
    # ningun default numerico hardcodeado en ${DMG_VERSION:-...}
    assert not re.search(r"DMG_VERSION:-\d", text)
```

- [ ] **Step 2: Verificar FAIL**

Run: `python -m pytest tests/test_version_consistency.py -q`
Expected: 3 FAIL (iss default 1.8.1, `DelTraficMeTask`, dmg 1.8.1).

- [ ] **Step 3: Implementar — `installer.iss`**

- L10: `#define AppVersion "1.8.1"` -> `#define AppVersion "2.0.1"`.
- Agregar, justo arriba de `#ifndef AppVersion`, el comentario: `; Default = src/version.py APP_VERSION (verificado por tests/test_version_consistency.py).`
- L59: `RunOnceId: "DelTraficMeTask"` -> `RunOnceId: "DelNetGaugeTask"`.

- [ ] **Step 4: Implementar — `make_dmg.sh`**

Reemplazar el comentario L14-16:

```bash
# La versión del nombre del .dmg sale de DMG_VERSION si está definida (CI la
# inyecta con la versión del git tag); sin esa env var (build local) se usa
# el default hardcodeado de abajo.
```

por:

```bash
# La versión del nombre del .dmg sale de DMG_VERSION si está definida (CI la
# inyecta con la versión del git tag); sin esa env var (build local) se lee
# de src/version.py (fuente única) vía build/gen_version_info.py.
```

y la línea 28 `VERSION="${DMG_VERSION:-1.8.1}"` por:

```bash
VERSION="${DMG_VERSION:-$(python3 "$ROOT_DIR/build/gen_version_info.py" --print-version)}"
if [[ -z "$VERSION" ]]; then
    echo "[make_dmg] No se pudo determinar la versión (src/version.py)." >&2
    exit 1
fi
```

- [ ] **Step 5: Verificar PASS**

Run: `python -m pytest tests/test_version_consistency.py -q` y luego `python -m pytest -q` (suite completa; ignorar fallos preexistentes ajenos a este plan, p.ej. `import pty` en Windows que cubre el plan 01 — anotarlos, no arreglarlos aca).
Expected: `test_version_consistency.py` 100% PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_version_consistency.py build/installer.iss build/make_dmg.sh
git commit -m "build(release): alinear default de installer.iss y make_dmg.sh con src/version.py"
```

---

### Task 4: `requirements` acotados, pyinstaller a dev, dependabot

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt`
- Create: `.github/dependabot.yml`

**Interfaces:** versiones instaladas hoy en dev: psutil 7.2.2, PySide6 6.11.1, openpyxl 3.1.5, reportlab 4.5.1, pywintrace 0.2.0, pyinstaller 6.21.0, pytest 9.0.3, Pillow 12.1.1, PyYAML 6.0.3 — todas caben en los rangos de abajo.

- [ ] **Step 1: Test que falla (agregar a `tests/test_version_consistency.py`? No: archivo propio)**

Crear `tests/test_requirements.py`:

```python
"""Higiene de dependencias: pyinstaller fuera de runtime y majors acotados."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _reqs(name: str) -> list[str]:
    out = []
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-r"):
            out.append(line)
    return out


def test_runtime_requirements_have_upper_bounds():
    for line in _reqs("requirements.txt"):
        spec = line.split(";", 1)[0]
        assert re.search(r">=[\d.]+,<\d+", spec), f"sin cota superior de major: {line!r}"


def test_pyinstaller_not_in_runtime_requirements():
    assert not any(l.lower().startswith("pyinstaller") for l in _reqs("requirements.txt"))


def test_pyinstaller_in_dev_requirements_bounded():
    dev = [l for l in _reqs("requirements-dev.txt") if l.lower().startswith("pyinstaller")]
    assert dev and re.search(r">=[\d.]+,<\d+", dev[0])


def test_dev_requirements_include_pyyaml_for_workflow_tests():
    assert any(l.lower().startswith("pyyaml") for l in _reqs("requirements-dev.txt"))


def test_dependabot_config_covers_pip_and_actions():
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "pip"' in text
    assert 'package-ecosystem: "github-actions"' in text
    assert text.count('interval: "weekly"') == 2
```

- [ ] **Step 2: Verificar FAIL**

Run: `python -m pytest tests/test_requirements.py -q`
Expected: 5 FAIL (`FileNotFoundError` en dependabot, sin cotas, etc.).

- [ ] **Step 3: Implementar `requirements.txt` (contenido completo)**

```text
psutil>=5.9,<8
# PySide6 (LGPL): apta para distribución gratuita y comercial/closed-source.
# (Se migró desde PyQt6, que es GPL/comercial y no servía para vender.)
PySide6>=6.6,<7
# Export de informes (Excel / PDF). Ambas son BSD/MIT (aptas comercialmente).
openpyxl>=3.1,<4
reportlab>=4.0,<5
# (pystray/Pillow ya no se usan: la UI y el tray ahora son Qt)
# ETW por proceso (opcional pero recomendado; requiere Administrador):
# Nota: la última versión publicada en PyPI es 0.2.0.
pywintrace>=0.2.0,<1; sys_platform == "win32"
```

(El empaquetado `pyinstaller` se movió a `requirements-dev.txt`.)

- [ ] **Step 4: Implementar `requirements-dev.txt` (contenido completo)**

```text
# Dependencias solo de desarrollo/build (no van al binario).
-r requirements.txt
pytest>=8.0,<10
# PyYAML: tests/test_workflows.py parsea los workflows de GitHub Actions.
PyYAML>=6.0,<7
# Empaquetado (solo en build, no en runtime):
pyinstaller>=6.0,<7
# Pillow: solo para build/make_icon.py (generación de assets/icon.ico/.icns
# en build-time). No se usa en runtime (la UI/tray son Qt) ni se empaqueta
# en el binario final.
Pillow>=10.0,<13
```

Los workflows ya instalan `requirements-dev.txt`, asi que los builds siguen teniendo PyInstaller.

- [ ] **Step 5: Implementar `.github/dependabot.yml` (contenido completo)**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "chore(deps)"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "ci(deps)"
```

- [ ] **Step 6: Verificar PASS + YAML**

Run: `python -m pytest tests/test_requirements.py -q`
Run: `python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml', encoding='utf-8')); print('ok')"`
Expected: PASS, `ok`.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt .github/dependabot.yml tests/test_requirements.py
git commit -m "build(deps): acotar majors, mover pyinstaller a dev y agregar dependabot"
```

---

### Task 5: `ci.yml` — runner macOS vigente, ubuntu, pip-audit, permisos

**Files:**
- Create: `tests/test_workflows.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:** jobs finales: `tests-windows`, `tests-linux` (offscreen, no-bloqueante), `audit` (pip-audit, no-bloqueante), `macos` (matrix `macos-15-intel` x86_64 + `macos-14` arm64, igual que release). Permisos workflow: `contents: read`.

- [ ] **Step 1: Test que falla**

Crear `tests/test_workflows.py` (esta task cubre ci.yml; la Task 6 agrega release.yml):

```python
"""Reglas de los workflows de GitHub Actions (parseo YAML, sin red)."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"
SHA_RE = re.compile(r"@[0-9a-f]{40}(\s|$)")
FIRST_PARTY = ("actions/", "github/")


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


def _uses(wf: dict) -> list[str]:
    out = []
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            if "uses" in step:
                out.append(step["uses"])
    return out


def test_ci_has_no_retired_macos13_runner():
    text = (WF / "ci.yml").read_text(encoding="utf-8")
    assert "macos-13" not in text
    assert "macos-15-intel" in text and "macos-14" in text


def test_ci_permissions_read_only():
    assert _load("ci.yml")["permissions"] == {"contents": "read"}


def test_ci_has_linux_and_audit_jobs():
    jobs = _load("ci.yml")["jobs"]
    assert jobs["tests-linux"]["runs-on"] == "ubuntu-latest"
    assert jobs["tests-linux"]["env"]["QT_QPA_PLATFORM"] == "offscreen"
    assert "pip-audit" in (WF / "ci.yml").read_text(encoding="utf-8")


def test_third_party_actions_pinned_by_sha():
    for name in ("ci.yml", "release.yml"):
        if not (WF / name).exists():
            continue
        for ref in _uses(_load(name)):
            if ref.startswith(FIRST_PARTY):
                continue
            raise AssertionError  # ningun tercero permitido sin pin: ver abajo


def test_python_version_consistent_across_workflows():
    versions = set()
    for name in ("ci.yml", "release.yml"):
        for job in _load(name)["jobs"].values():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith("actions/setup-python"):
                    versions.add(step["with"]["python-version"])
    assert versions == {"3.12"}
```

Nota: `test_third_party_actions_pinned_by_sha` esta escrito para fallar si aparece cualquier accion de terceros sin pin; se refina en la Task 6 (ver ahi) cuando entra `softprops/action-gh-release` pineado. Para esta task ci.yml solo usa acciones `actions/*`, asi que el test pasa; el `raise` no se alcanza.

- [ ] **Step 2: Verificar FAIL**

Run: `python -m pytest tests/test_workflows.py -q`
Expected: FAIL en `test_ci_has_no_retired_macos13_runner`, `test_ci_permissions_read_only`, `test_ci_has_linux_and_audit_jobs`; `test_python_version_consistent_across_workflows` PASS.

- [ ] **Step 3: Implementar `.github/workflows/ci.yml` (contenido completo)**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  tests-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest

  # Suite en Linux: detecta imports/rutas Windows-only y valida la logica pura.
  # QT_QPA_PLATFORM=offscreen permite que los tests que importan PySide6 corran
  # sin display. NO bloqueante hasta confirmar que la suite pasa completa en
  # ubuntu (los tests Windows-only ya hacen skipif); quitar continue-on-error
  # cuando este verde.
  tests-linux:
    runs-on: ubuntu-latest
    continue-on-error: true
    env:
      QT_QPA_PLATFORM: offscreen
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Qt runtime libraries
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest

  # Auditoria de vulnerabilidades de dependencias de runtime. No bloqueante:
  # un CVE nuevo en una dependencia no debe romper PRs ajenos; se revisa el log.
  audit:
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: pip-audit
        run: |
          pip install pip-audit && pip-audit -r requirements.txt

  # T-004: build/test/package macOS en ambas arquitecturas (mismos runners que
  # release.yml). No reemplaza el job Windows (corren en paralelo).
  macos:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-15-intel
            arch: x86_64
          - os: macos-14
            arch: arm64
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest

      - name: Generate macOS icon (.icns)
        run: python3 build/make_icon_macos.py

      - name: Build .app bundle (PyInstaller)
        env:
          TARGET_ARCH: ${{ matrix.arch }}
        run: pyinstaller build/network_monitor_macos.spec --noconfirm

      - name: Build .dmg
        run: build/make_dmg.sh ${{ matrix.arch }}

      - name: Upload .dmg artifact
        uses: actions/upload-artifact@v4
        with:
          name: NetGauge-macos-${{ matrix.arch }}
          path: dist/*.dmg
          if-no-files-found: error
```

- [ ] **Step 4: Verificar PASS + YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('ok')"`
Run: `python -m pytest tests/test_workflows.py -q`
Expected: `ok`; todos PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml tests/test_workflows.py
git commit -m "ci: runner macOS vigente, job ubuntu offscreen, pip-audit y permisos minimos"
```

---

### Task 6: `release.yml` — gate de tests, SHA256SUMS, permisos minimos, pins

**Files:**
- Modify: `tests/test_workflows.py`
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Job `test` (windows-latest): checkout, setup-python 3.12, install dev reqs, **verifica tag == APP_VERSION**, `pytest`.
- `windows` y `macos`: `needs: test`. Se ELIMINAN los pasos `sed` que reescribian `src/version.py`: la version se bumpea en un commit antes de taguear (el gate lo fuerza).
- `windows`: `python build/gen_version_info.py` antes de PyInstaller; `choco install innosetup -y --no-progress`.
- `publish`: `permissions: contents: write`; genera `SHA256SUMS.txt`; publica con `softprops/action-gh-release` pineado por SHA.

- [ ] **Step 1: Tests que fallan**

Reemplazar en `tests/test_workflows.py` el cuerpo de `test_third_party_actions_pinned_by_sha` por la version final y agregar los tests de release:

```python
def test_third_party_actions_pinned_by_sha():
    for name in ("ci.yml", "release.yml"):
        for ref in _uses(_load(name)):
            if ref.startswith(FIRST_PARTY):
                continue
            assert SHA_RE.search(ref + "\n"), f"accion de terceros sin pin por SHA: {ref}"


def test_release_default_permissions_read_only_and_publish_writes():
    wf = _load("release.yml")
    assert wf["permissions"] == {"contents": "read"}
    assert wf["jobs"]["publish"]["permissions"] == {"contents": "write"}
    for job in ("test", "windows", "macos"):
        assert "permissions" not in wf["jobs"][job]


def test_release_builds_are_gated_by_tests():
    jobs = _load("release.yml")["jobs"]
    assert "test" in jobs
    for job in ("windows", "macos"):
        assert "test" in jobs[job]["needs"]
    assert set(jobs["publish"]["needs"]) == {"windows", "macos"}


def test_release_generates_checksums_and_attaches_them():
    text = (WF / "release.yml").read_text(encoding="utf-8")
    assert "sha256sum" in text and "SHA256SUMS.txt" in text


def test_release_no_longer_rewrites_version_py():
    assert "sed -i" not in (WF / "release.yml").read_text(encoding="utf-8")


def test_release_windows_generates_version_info_before_pyinstaller():
    steps = _load("release.yml")["jobs"]["windows"]["steps"]
    cmds = [s.get("run", "") for s in steps]
    gen = next(i for i, c in enumerate(cmds) if "gen_version_info.py" in c)
    pyi = next(i for i, c in enumerate(cmds) if "pyinstaller" in c)
    assert gen < pyi


def test_release_innosetup_pinned():
    text = (WF / "release.yml").read_text(encoding="utf-8")
    assert re.search(r"choco install innosetup --version=\d+\.\d+\.\d+", text)
```

- [ ] **Step 2: Verificar FAIL**

Run: `python -m pytest tests/test_workflows.py -q`
Expected: FAIL en pin SHA, permisos, gate, checksums, sed, gen_version_info, innosetup.

- [ ] **Step 3: Resolver el SHA de `softprops/action-gh-release` (instruccion explicita, no placeholder)**

YA RESUELTO por el orquestador (2026-10-21, vía API pública de GitHub): `refs/tags/v2` → commit `3bb12739c298aeb8a4eeaf626c5b8d85266b0e65`. El YAML del paso 4 ya lo usa. Este paso no requiere acción.

- [ ] **Step 4: Implementar `.github/workflows/release.yml` (contenido completo)**

```yaml
name: Release

# T-008: publica instaladores Windows + macOS al GitHub Release cuando se
# pushea un tag v*. Workflow independiente de ci.yml: no modifica ni
# reemplaza sus triggers ni jobs (corren por separado).
#
# Proceso: bumpear src/version.py (+ build/installer.iss default si cambia el
# formato) en un commit, taguear vX.Y.Z sobre ese commit y pushear el tag. El
# job `test` falla si el tag no coincide con APP_VERSION.
on:
  push:
    tags:
      - 'v*'

# Minimo privilegio: solo el job publish necesita escribir.
permissions:
  contents: read

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Verify tag matches src/version.py
        shell: bash
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          TAG_VERSION="${TAG#v}"
          FILE_VERSION="$(python build/gen_version_info.py --print-version)"
          if [ "$TAG_VERSION" != "$FILE_VERSION" ]; then
            echo "::error::El tag $TAG no coincide con APP_VERSION=$FILE_VERSION de src/version.py. Bumpear la version antes de taguear."
            exit 1
          fi

      - name: Run tests
        run: pytest

  windows:
    needs: test
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Derive version from tag
        id: ver
        shell: bash
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          VERSION="${TAG#v}"
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Generate version_info.txt from src/version.py
        run: python build/gen_version_info.py

      - name: Build .exe (PyInstaller)
        run: pyinstaller build/network_monitor.spec --noconfirm

      - name: Install Inno Setup
        run: choco install innosetup -y --no-progress

      - name: Build Windows installer
        shell: cmd
        run: |
          "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\installer.iss /DAppVersion=${{ steps.ver.outputs.version }}

      - name: Upload .exe artifact
        uses: actions/upload-artifact@v4
        with:
          name: NetGauge-windows-exe
          path: build/Output/NetGauge-Setup-*-x64.exe
          if-no-files-found: error

  macos:
    needs: test
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-15-intel
            arch: x86_64
          - os: macos-14
            arch: arm64
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - name: Derive version from tag
        id: ver
        run: |
          TAG="${GITHUB_REF#refs/tags/}"
          VERSION="${TAG#v}"
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Generate macOS icon (.icns)
        run: python3 build/make_icon_macos.py

      - name: Build .app bundle (PyInstaller)
        env:
          TARGET_ARCH: ${{ matrix.arch }}
        run: pyinstaller build/network_monitor_macos.spec --noconfirm

      - name: Build .dmg
        env:
          DMG_VERSION: ${{ steps.ver.outputs.version }}
        run: build/make_dmg.sh ${{ matrix.arch }}

      - name: Upload .dmg artifact
        uses: actions/upload-artifact@v4
        with:
          name: NetGauge-macos-${{ matrix.arch }}
          path: dist/*.dmg
          if-no-files-found: error

  publish:
    needs: [windows, macos]
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Download Windows artifact
        uses: actions/download-artifact@v4
        with:
          name: NetGauge-windows-exe
          path: release-assets

      - name: Download macOS x86_64 artifact
        uses: actions/download-artifact@v4
        with:
          name: NetGauge-macos-x86_64
          path: release-assets

      - name: Download macOS arm64 artifact
        uses: actions/download-artifact@v4
        with:
          name: NetGauge-macos-arm64
          path: release-assets

      - name: Generate SHA256SUMS.txt
        working-directory: release-assets
        run: |
          sha256sum NetGauge-* > SHA256SUMS.txt
          cat SHA256SUMS.txt

      - name: Publish to GitHub Release
        uses: softprops/action-gh-release@3bb12739c298aeb8a4eeaf626c5b8d85266b0e65 # v2
        with:
          files: release-assets/*
          fail_on_unmatched_files: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Nota: innosetup no se pinea (no se pudo verificar una versión exacta en Chocolatey); queda anotado como mejora.

- [ ] **Step 5: Verificar PASS + YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml', encoding='utf-8')); print('ok')"`
Run: `python -m pytest tests/test_workflows.py tests/test_version_consistency.py tests/test_requirements.py -q`
Run: `rg "softprops" .github/workflows/release.yml` — debe mostrar `@` + 40 hex + `# v2.x.y`.
Expected: `ok`; todos PASS.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/release.yml tests/test_workflows.py
git commit -m "ci(release): gate de tests, SHA256SUMS, permisos minimos y acciones pineadas"
```

---

## Self-Review

- Cobertura del scope: version unica (Tasks 1-3: version_info generado, specs, iss, dmg, test ancla); ci.yml macos-13 -> macos-15-intel/14 + ubuntu offscreen + pip-audit + python 3.12 (Task 5); release.yml test gate, SHA256SUMS, permisos solo en publish, pin SHA con lookup `gh api`, choco pineado, gen_version_info previo a PyInstaller (Task 6); requirements acotados + pyinstaller a dev (Task 4); dependabot (Task 4); RunOnceId evaluado y renombrado con explicacion (Task 3); specs/AUMID sin tocar.
- Placeholders: el unico valor no verificable (SHA40/TAG de softprops) tiene instruccion explicita ejecutable (Task 6 paso 3) y un test que bloquea el commit si queda sin pin; innosetup queda sin pin (anotado como mejora).
- Consistencia de nombres: `read_app_version`, `version_tuple`, `render`, `write_version_info` usados identicos en tests, specs y CLI; jobs `tests-windows/tests-linux/audit/macos` en ci.yml coinciden con `test_workflows.py`.
- Correccion inline hecha: el test `test_third_party_actions_pinned_by_sha` de la Task 5 era provisorio (contiene `raise AssertionError`, solo valido porque ci.yml no tiene terceros); se reemplaza completo en Task 6 paso 1.
- `tests/test_requirements.py::test_runtime_requirements_have_upper_bounds` ignora el marker (`split(";")`) y exige `>=X,<N`: coincide con las 5 lineas de runtime.
