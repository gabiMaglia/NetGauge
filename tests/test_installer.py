"""El instalador debe mostrar PRIVACY.md y los bundles deben incluirlo."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"


def test_installer_shows_privacy_policy_before_install():
    text = (BUILD / "installer.iss").read_text(encoding="utf-8")
    m = re.search(r'^\s*InfoBeforeFile\s*=\s*(\S+)\s*$', text, re.MULTILINE)
    assert m, "installer.iss no define InfoBeforeFile"
    rel = m.group(1)
    assert rel.endswith("PRIVACY.md")
    # Ruta relativa al .iss, igual que LicenseFile.
    assert (BUILD / rel.replace("\\", "/")).resolve() == (ROOT / "PRIVACY.md").resolve()
    assert (ROOT / "PRIVACY.md").is_file()


def test_privacy_policy_is_bundled_in_specs_and_installer():
    for spec in ("network_monitor.spec", "network_monitor_macos.spec"):
        assert "PRIVACY.md" in (BUILD / spec).read_text(encoding="utf-8"), spec
    assert "PRIVACY.md" in (BUILD / "installer.iss").read_text(encoding="utf-8")


def test_privacy_policy_documents_every_outbound_connection():
    text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    for host in ("api.github.com", "ip-api.com", "virustotal.com"):
        assert host in text, host
