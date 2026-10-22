"""Tests de seguridad de `trust.py`: límites de ruta y prototipos ctypes."""
from __future__ import annotations

import sys

import pytest

from src.infrastructure.capture import trust

win_only = pytest.mark.skipif(sys.platform != "win32", reason="ctypes/crypt32 solo en Windows")


# --- límites de ruta ---------------------------------------------------------

def test_is_under_requiere_separador():
    assert trust._is_under("C:\\Windows\\System32\\x.exe", "c:\\windows")
    assert trust._is_under("c:/windows/system32/x.exe", "C:\\Windows")  # / y mayúsculas
    assert trust._is_under("C:\\Windows", "c:\\windows\\")               # igual a la raíz
    assert not trust._is_under("C:\\Windows.old\\x.exe", "c:\\windows")
    assert not trust._is_under("C:\\Program Files-evil\\x.exe", "c:\\program files")
    assert not trust._is_under("C:\\Windowsx\\x.exe", "c:\\windows")


def test_location_ok_no_confia_en_prefijos_hermanos(monkeypatch):
    monkeypatch.setenv("ProgramFiles", "C:\\Program Files")
    monkeypatch.setenv("ProgramFiles(x86)", "C:\\Program Files (x86)")
    monkeypatch.setenv("SystemRoot", "C:\\Windows")
    assert trust._location_ok("C:\\Program Files\\App\\a.exe") == (True, False)
    assert trust._location_ok("C:\\Windows\\System32\\a.exe") == (True, False)
    assert trust._location_ok("C:\\Windows.old\\a.exe") == (False, False)
    assert trust._location_ok("C:\\Program Files-evil\\a.exe") == (False, False)
    assert trust._location_ok("C:\\Users\\x\\Downloads\\a.exe") == (False, True)


# --- prototipos ctypes crypt32 -----------------------------------------------

@win_only
def test_crypt32_prototipos_configurados():
    """En 64-bit, sin restype/argtypes ctypes trunca punteros a int de 32 bits
    (access violation intermitente). El crash es no determinista: verificamos
    la configuración, que sí lo es."""
    import ctypes

    c32 = trust._api().c32
    assert c32.CertEnumCertificatesInStore.restype == ctypes.c_void_p
    assert c32.CertEnumCertificatesInStore.argtypes == [ctypes.c_void_p, ctypes.c_void_p]
    assert c32.CertGetNameStringW.argtypes is not None
    for nombre in ("CryptQueryObject", "CryptMsgGetParam", "CertGetNameStringW",
                   "CertFreeCertificateContext", "CertCloseStore", "CryptMsgClose"):
        assert getattr(c32, nombre).argtypes is not None, nombre


@win_only
def test_crypt32_no_muta_windll():
    """Usamos un WinDLL dedicado: el singleton `ctypes.windll` queda intacto."""
    import ctypes

    trust._api()
    assert ctypes.windll.crypt32.CertEnumCertificatesInStore.restype != ctypes.c_void_p


@win_only
def test_signer_name_explorer_estable_en_loop():
    """Red de seguridad: el access violation original aparecía a las pocas
    iteraciones. 200 llamadas seguidas no deben crashear ni variar."""
    import os

    path = os.path.join(os.environ["SystemRoot"], "explorer.exe")
    nombres = {trust._signer_name(path) for _ in range(200)}
    assert len(nombres) == 1
    (nombre,) = nombres
    assert nombre and "Microsoft" in nombre


# --- prototipos ctypes wintrust / kernel32 -----------------------------------

@win_only
def test_wintrust_y_kernel32_prototipos_configurados():
    import ctypes
    from ctypes import wintypes

    api = trust._api()
    for nombre in ("WinVerifyTrust", "CryptCATAdminAcquireContext",
                   "CryptCATAdminAcquireContext2", "CryptCATAdminCalcHashFromFileHandle",
                   "CryptCATAdminCalcHashFromFileHandle2",
                   "CryptCATAdminEnumCatalogFromHash", "CryptCATCatalogInfoFromContext",
                   "CryptCATAdminReleaseCatalogContext", "CryptCATAdminReleaseContext"):
        assert getattr(api.wt, nombre).argtypes is not None, nombre
    for nombre in ("CreateFileW", "CloseHandle"):
        assert getattr(api.k32, nombre).argtypes is not None, nombre
    # Devuelven HANDLE: sin restype ctypes los trunca a int de 32 bits.
    assert api.wt.CryptCATAdminEnumCatalogFromHash.restype == wintypes.HANDLE
    assert api.k32.CreateFileW.restype == wintypes.HANDLE
    assert api.wt.WinVerifyTrust.restype == ctypes.c_long


@win_only
def test_verify_signature_embebida_y_catalogo():
    import os

    root = os.environ["SystemRoot"]
    # explorer.exe: firma embebida; svchost.exe: según build puede ir por catálogo.
    assert trust._verify_signature(os.path.join(root, "explorer.exe")) == (True, True)
    assert trust._verify_signature(os.path.join(root, "System32", "svchost.exe")) == (True, True)


@win_only
def test_verify_catalog_en_loop_no_crashea():
    import os

    path = os.path.join(os.environ["SystemRoot"], "System32", "svchost.exe")
    for _ in range(100):
        trust._verify_catalog(path, "SHA256")
        trust._verify_catalog(path, None)


@win_only
def test_signer_name_es_el_firmante_no_la_ca():
    import os
    import sys

    explorer = os.path.join(os.environ["SystemRoot"], "explorer.exe")
    name = trust._signer_name(explorer)
    assert name and name.startswith("Microsoft Windows")
    assert "PCA" not in name
    py = trust._signer_name(sys.executable)
    if py is not None:  # python.exe puede no estar firmado en todos los entornos
        assert "PCA" not in py and "Timestamp" not in py


@win_only
@pytest.mark.parametrize("code,expected", [
    (0x80096010, (True, False)),   # TRUST_E_BAD_DIGEST
    (0x800B0111, (True, False)),   # TRUST_E_EXPLICIT_DISTRUST
    (0x800B0101, (True, False)),   # CERT_E_EXPIRED
    (0x80096004, (True, False)),   # TRUST_E_CERT_SIGNATURE
    (0x80092003, None),            # CRYPT_E_FILE_ERROR: error de IO, indeterminado
    (0x80070005, None),            # acceso denegado
])
def test_verify_signature_clasifica_errores(monkeypatch, code, expected):
    monkeypatch.setattr(trust, "_verify_embedded", lambda p: code)
    assert trust._verify_signature("x.exe") == expected


@win_only
def test_verify_signature_sin_firma(monkeypatch):
    monkeypatch.setattr(trust, "_verify_embedded", lambda p: 0x800B0100)
    monkeypatch.setattr(trust, "_verify_catalog", lambda p, a=None: False)
    assert trust._verify_signature("x.exe") == (False, False)


@win_only
def test_evaluate_ruta_inexistente_es_unknown_y_no_se_cachea():
    from src.domain.models import TRUST_UNKNOWN

    ev = trust.WindowsTrustEvaluator()
    info = ev.evaluate(r"C:\no\existe\nada.exe")
    assert info.level == TRUST_UNKNOWN
    assert ev._cache == {}


@win_only
def test_evaluate_indeterminado_no_se_cachea(monkeypatch, tmp_path):
    from src.domain.models import TRUST_UNKNOWN

    f = tmp_path / "a.exe"
    f.write_bytes(b"MZ")
    monkeypatch.setattr(trust, "_verify_embedded", lambda p: 0x80092003)
    ev = trust.WindowsTrustEvaluator()
    assert ev.evaluate(str(f)).level == TRUST_UNKNOWN
    assert ev._cache == {}


@win_only
def test_evaluate_cache_se_invalida_si_cambia_el_archivo(monkeypatch, tmp_path):
    f = tmp_path / "a.exe"
    f.write_bytes(b"MZ")
    calls = []
    ev = trust.WindowsTrustEvaluator()
    orig = ev._evaluate
    monkeypatch.setattr(ev, "_evaluate", lambda p: (calls.append(p), orig(p))[1])
    monkeypatch.setattr(trust, "_verify_embedded", lambda p: 0)
    ev.evaluate(str(f))
    ev.evaluate(str(f))
    assert len(calls) == 1
    f.write_bytes(b"MZ-modificado")
    ev.evaluate(str(f))
    assert len(calls) == 2
