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
