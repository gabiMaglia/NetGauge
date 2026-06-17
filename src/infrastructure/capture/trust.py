"""Índice de confianza con señales LOCALES y reales (sin inventar números).

Combina tres señales verificables:
  1. Firma Authenticode válida (WinVerifyTrust) + nombre del firmante.
  2. Ubicación del ejecutable (Program Files/System32 = normal; Temp/Downloads = atípico).
  3. Presencia de metadata (CompanyName/FileDescription).

El veredicto (TrustInfo.level) es un resumen de esas señales, NO una probabilidad.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

from ...domain.models import (
    TRUST_CAUTION,
    TRUST_SUSPICIOUS,
    TRUST_TRUSTED,
    TRUST_UNKNOWN,
    TrustInfo,
)
from ...domain.ports import TrustEvaluator
from .app_names import _file_description

# --- WinVerifyTrust (wintrust.dll) ------------------------------------------
_WTD_UI_NONE = 2
_WTD_REVOKE_NONE = 0
_WTD_CHOICE_FILE = 1
_WTD_STATEACTION_VERIFY = 1
_WTD_STATEACTION_CLOSE = 2
_TRUST_E_NOSIGNATURE = 0x800B0100  # archivo sin firma


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _WINTRUST_FILE_INFO(ctypes.Structure):
    _fields_ = [
        ("cbStruct", wintypes.DWORD),
        ("pcwszFilePath", wintypes.LPCWSTR),
        ("hFile", wintypes.HANDLE),
        ("pgKnownSubject", ctypes.c_void_p),
    ]


class _WINTRUST_DATA(ctypes.Structure):
    _fields_ = [
        ("cbStruct", wintypes.DWORD),
        ("pPolicyCallbackData", ctypes.c_void_p),
        ("pSIPClientData", ctypes.c_void_p),
        ("dwUIChoice", wintypes.DWORD),
        ("fdwRevocationChecks", wintypes.DWORD),
        ("dwUnionChoice", wintypes.DWORD),
        ("pFile", ctypes.POINTER(_WINTRUST_FILE_INFO)),
        ("dwStateAction", wintypes.DWORD),
        ("hWVTStateData", wintypes.HANDLE),
        ("pwszURLReference", wintypes.LPWSTR),
        ("dwProvFlags", wintypes.DWORD),
        ("dwUIContext", wintypes.DWORD),
        ("pSignatureSettings", ctypes.c_void_p),
    ]


# WINTRUST_ACTION_GENERIC_VERIFY_V2
_ACTION = _GUID(0xAAC56B, 0xCD44, 0x11D0,
                (0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE))


class _CATALOG_INFO(ctypes.Structure):
    _fields_ = [("cbStruct", wintypes.DWORD),
                ("wszCatalogFile", wintypes.WCHAR * 260)]


class _WINTRUST_CATALOG_INFO(ctypes.Structure):
    _fields_ = [
        ("cbStruct", wintypes.DWORD),
        ("dwCatalogVersion", wintypes.DWORD),
        ("pcwszCatalogFilePath", wintypes.LPCWSTR),
        ("pcwszMemberTag", wintypes.LPCWSTR),
        ("pcwszMemberFilePath", wintypes.LPCWSTR),
        ("hMemberFile", wintypes.HANDLE),
        ("pbCalculatedFileHash", ctypes.POINTER(ctypes.c_ubyte)),
        ("cbCalculatedFileHash", wintypes.DWORD),
        ("pcCatalogContext", ctypes.c_void_p),
        ("hCatAdmin", wintypes.HANDLE),
    ]


_WTD_CHOICE_CATALOG = 2
_GENERIC_READ = 0x80000000
_FILE_SHARE_READ = 0x00000001
_OPEN_EXISTING = 3


def _verify_embedded(path: str) -> int:
    file_info = _WINTRUST_FILE_INFO()
    file_info.cbStruct = ctypes.sizeof(_WINTRUST_FILE_INFO)
    file_info.pcwszFilePath = path
    data = _WINTRUST_DATA()
    data.cbStruct = ctypes.sizeof(_WINTRUST_DATA)
    data.dwUIChoice = _WTD_UI_NONE
    data.fdwRevocationChecks = _WTD_REVOKE_NONE
    data.dwUnionChoice = _WTD_CHOICE_FILE
    data.pFile = ctypes.pointer(file_info)
    data.dwStateAction = _WTD_STATEACTION_VERIFY
    wt = ctypes.windll.wintrust
    ret = wt.WinVerifyTrust(None, ctypes.byref(_ACTION), ctypes.byref(data)) & 0xFFFFFFFF
    data.dwStateAction = _WTD_STATEACTION_CLOSE
    wt.WinVerifyTrust(None, ctypes.byref(_ACTION), ctypes.byref(data))
    return ret


_INVALID_HANDLE = ctypes.c_void_p(-1).value
_catalog_api_ready = False


def _setup_catalog_api() -> None:
    """Fija restype/argtypes: en 64-bit, sin esto ctypes trunca los HANDLE."""
    global _catalog_api_ready
    if _catalog_api_ready:
        return
    wt = ctypes.windll.wintrust
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    wt.CryptCATAdminEnumCatalogFromHash.restype = wintypes.HANDLE
    _catalog_api_ready = True


_WINDIR = os.environ.get("SystemRoot", "c:\\windows").lower().replace("/", "\\")


def _verify_catalog(path: str, algo: str | None = None) -> bool:
    """True si el archivo está firmado por un catálogo del sistema (.cat).

    `algo` = 'SHA256' usa AcquireContext2 (Win8+); None usa el clásico (SHA-1).
    """
    _setup_catalog_api()
    wt = ctypes.windll.wintrust
    k32 = ctypes.windll.kernel32
    h_cat_admin = wintypes.HANDLE()
    if algo:
        ok = wt.CryptCATAdminAcquireContext2(
            ctypes.byref(h_cat_admin), None, wintypes.LPCWSTR(algo), None, 0)
    else:
        ok = wt.CryptCATAdminAcquireContext(ctypes.byref(h_cat_admin), None, 0)
    if not ok:
        return False
    h_file = None
    h_cat_info = None
    try:
        h_file = k32.CreateFileW(path, _GENERIC_READ, _FILE_SHARE_READ, None,
                                 _OPEN_EXISTING, 0, None)
        if not h_file or h_file == _INVALID_HANDLE:
            return False
        size = wintypes.DWORD(0)
        if algo:
            wt.CryptCATAdminCalcHashFromFileHandle2(
                h_cat_admin, h_file, ctypes.byref(size), None, 0)
        else:
            wt.CryptCATAdminCalcHashFromFileHandle(
                h_file, ctypes.byref(size), None, 0)
        if not size.value:
            return False
        buf = (ctypes.c_ubyte * size.value)()
        if algo:
            ok2 = wt.CryptCATAdminCalcHashFromFileHandle2(
                h_cat_admin, h_file, ctypes.byref(size), buf, 0)
        else:
            ok2 = wt.CryptCATAdminCalcHashFromFileHandle(
                h_file, ctypes.byref(size), buf, 0)
        if not ok2:
            return False
        h_cat_info = wt.CryptCATAdminEnumCatalogFromHash(
            h_cat_admin, buf, size, 0, None)
        if not h_cat_info:
            return False
        ci = _CATALOG_INFO()
        ci.cbStruct = ctypes.sizeof(_CATALOG_INFO)
        if not wt.CryptCATCatalogInfoFromContext(h_cat_info, ctypes.byref(ci), 0):
            return False
        member_tag = "".join(f"{b:02X}" for b in buf)
        cat_info = _WINTRUST_CATALOG_INFO()
        cat_info.cbStruct = ctypes.sizeof(_WINTRUST_CATALOG_INFO)
        cat_info.pcwszCatalogFilePath = ci.wszCatalogFile
        cat_info.pcwszMemberTag = member_tag
        cat_info.pcwszMemberFilePath = path
        cat_info.hMemberFile = h_file
        cat_info.pbCalculatedFileHash = buf
        cat_info.cbCalculatedFileHash = size
        cat_info.hCatAdmin = h_cat_admin
        data = _WINTRUST_DATA()
        data.cbStruct = ctypes.sizeof(_WINTRUST_DATA)
        data.dwUIChoice = _WTD_UI_NONE
        data.fdwRevocationChecks = _WTD_REVOKE_NONE
        data.dwUnionChoice = _WTD_CHOICE_CATALOG
        data.pFile = ctypes.cast(ctypes.pointer(cat_info),
                                 ctypes.POINTER(_WINTRUST_FILE_INFO))
        data.dwStateAction = _WTD_STATEACTION_VERIFY
        ret = wt.WinVerifyTrust(None, ctypes.byref(_ACTION),
                                ctypes.byref(data)) & 0xFFFFFFFF
        data.dwStateAction = _WTD_STATEACTION_CLOSE
        wt.WinVerifyTrust(None, ctypes.byref(_ACTION), ctypes.byref(data))
        return ret == 0
    finally:
        if h_cat_info:
            wt.CryptCATAdminReleaseCatalogContext(h_cat_admin, h_cat_info, 0)
        if h_file and h_file != _INVALID_HANDLE:
            k32.CloseHandle(h_file)
        wt.CryptCATAdminReleaseContext(h_cat_admin, 0)


def _verify_signature(path: str) -> tuple[bool, bool]:
    """(firmado, firma_válida). Chequea firma embebida y, si falta, catálogo."""
    ret = _verify_embedded(path)
    if ret == 0:
        return True, True                 # firma embebida válida
    if ret == _TRUST_E_NOSIGNATURE:
        # Muchos binarios del sistema se firman por catálogo (.cat), no embebido.
        # Win11 usa catálogos SHA-256; probamos eso y luego SHA-1.
        for algo in ("SHA256", None):
            try:
                if _verify_catalog(path, algo):
                    return True, True
            except Exception:  # noqa: BLE001
                pass
        return False, False               # realmente sin firma
    return True, False                    # firmado pero inválido (alterado/expirado)


def _signer_name(path: str) -> str | None:
    """Nombre del firmante (subject del certificado). Best-effort."""
    CERT_QUERY_OBJECT_FILE = 1
    CERT_QUERY_CONTENT_FLAG_ALL = 0x00003FFE
    CERT_QUERY_FORMAT_FLAG_ALL = 0x0000000E
    PKCS_7_ASN_ENCODING = 0x00010000
    X509_ASN_ENCODING = 0x00000001
    CMSG_SIGNER_INFO_PARAM = 6
    CERT_NAME_SIMPLE_DISPLAY_TYPE = 4
    try:
        crypt32 = ctypes.windll.crypt32
        h_store = wintypes.HANDLE()
        h_msg = wintypes.HANDLE()
        ok = crypt32.CryptQueryObject(
            CERT_QUERY_OBJECT_FILE, wintypes.LPCWSTR(path),
            CERT_QUERY_CONTENT_FLAG_ALL, CERT_QUERY_FORMAT_FLAG_ALL, 0,
            None, None, None, ctypes.byref(h_store), ctypes.byref(h_msg), None)
        if not ok:
            return None
        try:
            size = wintypes.DWORD()
            if not ctypes.windll.crypt32.CryptMsgGetParam(
                    h_msg, CMSG_SIGNER_INFO_PARAM, 0, None, ctypes.byref(size)):
                return None
            buf = ctypes.create_string_buffer(size.value)
            if not ctypes.windll.crypt32.CryptMsgGetParam(
                    h_msg, CMSG_SIGNER_INFO_PARAM, 0, buf, ctypes.byref(size)):
                return None
            # El primer cert del store suele ser el del firmante.
            ctx = crypt32.CertEnumCertificatesInStore(h_store, None)
            if not ctx:
                return None
            n = crypt32.CertGetNameStringW(
                ctx, CERT_NAME_SIMPLE_DISPLAY_TYPE, 0, None, None, 0)
            if n <= 1:
                return None
            out = ctypes.create_unicode_buffer(n)
            crypt32.CertGetNameStringW(
                ctx, CERT_NAME_SIMPLE_DISPLAY_TYPE, 0, None, out, n)
            name = out.value.strip()
            return name or None
        finally:
            if h_store:
                crypt32.CertCloseStore(h_store, 0)
            if h_msg:
                ctypes.windll.crypt32.CryptMsgClose(h_msg)
    except Exception:  # noqa: BLE001
        return None


def _location_ok(path: str) -> tuple[bool, bool]:
    """(ubicacion_normal, ubicacion_sospechosa)."""
    p = path.lower().replace("/", "\\")
    normal_roots = [
        os.environ.get("ProgramFiles", "c:\\program files").lower(),
        os.environ.get("ProgramFiles(x86)", "c:\\program files (x86)").lower(),
        os.environ.get("SystemRoot", "c:\\windows").lower(),
    ]
    suspicious_marks = ["\\temp\\", "\\appdata\\local\\temp\\",
                        "\\downloads\\", "\\tmp\\"]
    ok = any(p.startswith(r) for r in normal_roots if r)
    bad = any(m in p for m in suspicious_marks)
    return ok, bad


class WindowsTrustEvaluator(TrustEvaluator):
    """Evalúa confianza en Windows. Cachea por ruta (la firma no cambia en vivo)."""

    def __init__(self) -> None:
        self._cache: dict[str, TrustInfo] = {}

    def evaluate(self, exe_path: str) -> TrustInfo:
        if not exe_path:
            return TrustInfo(level=TRUST_UNKNOWN)
        if exe_path in self._cache:
            return self._cache[exe_path]
        info = self._evaluate(exe_path)
        self._cache[exe_path] = info
        return info

    def _evaluate(self, exe_path: str) -> TrustInfo:
        try:
            signed, valid = _verify_signature(exe_path)
        except Exception:  # noqa: BLE001
            return TrustInfo(level=TRUST_UNKNOWN, exe_path=exe_path)

        signer = _signer_name(exe_path) if signed and valid else None
        loc_ok, loc_bad = _location_ok(exe_path)
        has_meta = _file_description(exe_path) is not None

        is_system = exe_path.lower().replace("/", "\\").startswith(_WINDIR)
        reasons: list[str] = []
        risk = 0
        if signed and valid:
            reasons.append("trust.signed_by" if signer else "trust.signed")
        elif signed and not valid:
            reasons.append("trust.invalid_sig")
            risk += 2
        elif is_system:
            # Componente de Windows (firmado por catálogo aunque no lo resolvamos).
            reasons.append("trust.system_file")
        else:
            reasons.append("trust.unsigned")
            risk += 1
        if loc_bad:
            reasons.append("trust.location_bad")
            risk += 1
        elif loc_ok:
            reasons.append("trust.location_ok")
        if not has_meta:
            reasons.append("trust.no_metadata")
            risk += 1

        level = (TRUST_TRUSTED if risk == 0
                 else TRUST_CAUTION if risk == 1
                 else TRUST_SUSPICIOUS)
        return TrustInfo(
            level=level, signed=signed, signature_valid=valid, signer=signer,
            location_ok=loc_ok, has_metadata=has_meta, exe_path=exe_path,
            reasons=tuple(reasons))


class NullTrustEvaluator(TrustEvaluator):
    """No evalúa nada (índice deshabilitado o plataforma no soportada)."""

    def evaluate(self, exe_path: str) -> TrustInfo:
        return TrustInfo(level=TRUST_UNKNOWN, exe_path=exe_path or None)
