"""Tests de infraestructura: VirusTotal, GeoIP y (en Windows) índice de confianza."""
import sys
import urllib.error
from unittest.mock import MagicMock, patch

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


def test_test_api_key_empty_returns_false_no_network():
    vt = VirusTotalReputation()
    assert vt.test_api_key("") is False
    assert vt.test_api_key("   ") is False


def test_test_api_key_valid_returns_true():
    """200 OK en GET /users/{key} -> key válida (mock, sin red real)."""
    vt = VirusTotalReputation()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    with patch("urllib.request.urlopen", return_value=mock_resp) as mocked:
        assert vt.test_api_key("a-valid-key") is True
        # Debe pegarle al endpoint de usuarios, no al de archivos.
        req = mocked.call_args[0][0]
        assert "/users/a-valid-key" in req.full_url
        assert req.headers.get("X-apikey") == "a-valid-key"


def test_test_api_key_invalid_returns_false_on_http_error():
    vt = VirusTotalReputation()
    err = urllib.error.HTTPError(
        url="https://www.virustotal.com/api/v3/users/bad-key",
        code=401, msg="Unauthorized", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        assert vt.test_api_key("bad-key") is False


def test_test_api_key_returns_false_on_connection_error():
    vt = VirusTotalReputation()
    with patch("urllib.request.urlopen",
              side_effect=urllib.error.URLError("no network")):
        assert vt.test_api_key("some-key") is False


def test_report_generators_write_nonempty_files(tmp_path):
    from datetime import datetime
    import os

    from src.domain.models import UsageRecord
    from src.infrastructure.reporting.pdf_report_generator import PdfReportGenerator
    from src.infrastructure.reporting.xlsx_report_generator import XlsxReportGenerator

    recs = [UsageRecord("Chrome", 100, 200, datetime.now()),
            UsageRecord("Spotify", 50, 80, datetime.now())]
    for gen, ext in ((XlsxReportGenerator(tmp_path), ".xlsx"),
                     (PdfReportGenerator(tmp_path), ".pdf")):
        path = gen.generate(recs)
        assert path.endswith(ext)
        assert os.path.getsize(path) > 0


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
