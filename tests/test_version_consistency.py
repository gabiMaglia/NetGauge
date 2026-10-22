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
