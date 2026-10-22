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
