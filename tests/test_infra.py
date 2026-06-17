"""Tests de infraestructura: VirusTotal, GeoIP y (en Windows) índice de confianza."""
import sys

from src.infrastructure.capture.geoip_ipapi import _is_public
from src.infrastructure.capture.reputation_virustotal import (
    VirusTotalReputation, _sha256,
)


def test_geoip_classifies_private_vs_public():
    assert _is_public("8.8.8.8") is True
    assert _is_public("1.1.1.1") is True
    assert _is_public("192.168.0.1") is False
    assert _is_public("10.0.0.5") is False
    assert _is_public("127.0.0.1") is False
    assert _is_public("not-an-ip") is False


def test_vt_lookup_without_key_returns_none_no_network():
    vt = VirusTotalReputation()  # sin api key -> no debe tocar la red
    assert vt.lookup("C:/whatever.exe") is None


def test_sha256_of_this_file_is_stable():
    h1 = _sha256(__file__)
    h2 = _sha256(__file__)
    assert h1 and h1 == h2 and len(h1) == 64


# --- específico de Windows: firma real -------------------------------------
if sys.platform == "win32":
    import os

    from src.domain.models import TRUST_TRUSTED
    from src.infrastructure.capture.trust import WindowsTrustEvaluator

    def test_explorer_is_trusted():
        path = os.path.join(os.environ["SystemRoot"], "explorer.exe")
        info = WindowsTrustEvaluator().evaluate(path)
        assert info.level == TRUST_TRUSTED

    def test_system_binaries_not_flagged():
        ev = WindowsTrustEvaluator()
        for exe in ("notepad.exe", "svchost.exe"):
            p = os.path.join(os.environ["SystemRoot"], "System32", exe)
            assert ev.evaluate(p).level == TRUST_TRUSTED
