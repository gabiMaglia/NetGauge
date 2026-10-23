"""Firma Developer ID + notarización macOS opcionales (estructura de los archivos de build)."""
from __future__ import annotations

import plistlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
ENTITLEMENTS = BUILD / "entitlements.plist"
SPEC = BUILD / "network_monitor_macos.spec"
DMG = BUILD / "make_dmg.sh"


def _dmg() -> str:
    return DMG.read_text(encoding="utf-8")


# --- entitlements.plist ---------------------------------------------------

def test_entitlements_plist_has_exactly_the_two_hardened_runtime_exceptions():
    data = plistlib.loads(ENTITLEMENTS.read_bytes())
    assert data == {
        "com.apple.security.cs.allow-unsigned-executable-memory": True,
        "com.apple.security.cs.disable-library-validation": True,
    }


def test_entitlements_plist_does_not_enable_sandbox_or_jit():
    text = ENTITLEMENTS.read_text(encoding="utf-8")
    assert "app-sandbox" not in text
    assert "allow-jit" not in text


# --- spec -----------------------------------------------------------------

def test_spec_reads_codesign_identity_from_env():
    text = SPEC.read_text(encoding="utf-8")
    assert 'os.environ.get("NETGAUGE_CODESIGN_IDENTITY")' in text
    assert "codesign_identity=" in text
    assert "entitlements_file=" in text
    assert "entitlements.plist" in text


def test_spec_keeps_bundle_identifier():
    assert 'bundle_identifier="com.gabrielmaglia.netgauge"' in SPEC.read_text(encoding="utf-8")


# --- make_dmg.sh ----------------------------------------------------------

def test_make_dmg_is_strict_bash():
    assert "set -euo pipefail" in _dmg()


def test_make_dmg_signing_is_guarded_by_identity_env():
    text = _dmg()
    assert '${NETGAUGE_CODESIGN_IDENTITY:-}' in text
    assert "--options runtime" in text
    assert "--timestamp" in text
    assert "--entitlements" in text
    assert "codesign --verify --deep --strict --verbose=2" in text


def test_make_dmg_signs_nested_binaries_inside_out():
    text = _dmg()
    assert "find " in text
    assert "*.dylib" in text and "*.so" in text


def test_make_dmg_notarizes_with_profile_or_apple_id_trio():
    text = _dmg()
    assert "${NETGAUGE_NOTARY_PROFILE:-}" in text
    for var in ("APPLE_ID", "APPLE_TEAM_ID", "APPLE_APP_PASSWORD"):
        assert "${" + var + ":-}" in text
    assert "notarytool submit" in text
    assert "--wait" in text
    assert "--keychain-profile" in text
    assert "Accepted" in text
    assert "notarytool log" in text
    assert "stapler staple" in text
    assert "spctl -a -t open --context context:primary-signature" in text


def test_make_dmg_never_echoes_secrets():
    for line in _dmg().splitlines():
        if line.strip().startswith("echo"):
            assert "APPLE_APP_PASSWORD" not in line
            assert "APPLE_ID" not in line


def test_shell_scripts_forced_to_lf():
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.sh text eol=lf" in attrs


def test_make_dmg_retries_staple_validate_and_spctl_on_network_errors():
    text = _dmg()
    assert "retry_net.sh" in text
    assert 'retry_net "stapler staple+validate"' in text
    assert 'retry_net "spctl"' in text
