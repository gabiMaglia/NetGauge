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
from types import SimpleNamespace

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
_TRUST_E_BAD_DIGEST = 0x80096010
_TRUST_E_EXPLICIT_DISTRUST = 0x800B0111
_TRUST_E_CERT_SIGNATURE = 0x80096004


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


class _BLOB(ctypes.Structure):
    """CRYPT_INTEGER_BLOB / CERT_NAME_BLOB / CRYPT_OBJID_BLOB: {cbData, pbData}."""
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.c_void_p)]


class _CMSG_SIGNER_INFO(ctypes.Structure):
    # Sólo el prefijo que usamos (el resto del struct no se accede).
    _fields_ = [("dwVersion", wintypes.DWORD),
                ("Issuer", _BLOB),
                ("SerialNumber", _BLOB)]


class _CRYPT_ALGORITHM_IDENTIFIER(ctypes.Structure):
    _fields_ = [("pszObjId", ctypes.c_void_p), ("Parameters", _BLOB)]


class _CERT_INFO(ctypes.Structure):
    # Prefijo hasta Issuer; CertFindCertificateInStore(SUBJECT_CERT) sólo lee
    # Issuer y SerialNumber.
    _fields_ = [("dwVersion", wintypes.DWORD),
                ("SerialNumber", _BLOB),
                ("SignatureAlgorithm", _CRYPT_ALGORITHM_IDENTIFIER),
                ("Issuer", _BLOB)]


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
    wt = _api().wt
    ret = wt.WinVerifyTrust(None, ctypes.byref(_ACTION), ctypes.byref(data)) & 0xFFFFFFFF
    data.dwStateAction = _WTD_STATEACTION_CLOSE
    wt.WinVerifyTrust(None, ctypes.byref(_ACTION), ctypes.byref(data))
    return ret


_INVALID_HANDLE = ctypes.c_void_p(-1).value


_api_cache: SimpleNamespace | None = None


def _proto(fn, restype, argtypes) -> None:
    """Fija el prototipo de una función Win32 (obligatorio en 64-bit)."""
    fn.restype = restype
    fn.argtypes = argtypes


def _api() -> SimpleNamespace:
    """DLLs DEDICADAS con prototipos. No tocamos el singleton `ctypes.windll`:
    los prototipos viven en el objeto WinDLL, y mutarlo afectaría a cualquier
    otro módulo que use la misma DLL."""
    global _api_cache
    if _api_cache is not None:
        return _api_cache
    c32 = ctypes.WinDLL("crypt32")
    V, D, B = ctypes.c_void_p, wintypes.DWORD, wintypes.BOOL
    # CryptQueryObject(tipo, objeto, contentFlags, formatFlags, flags,
    #                  pdwEnc, pdwContent, pdwFormat, phStore, phMsg, ppvCtx)
    _proto(c32.CryptQueryObject, B, [D, V, D, D, D, V, V, V, V, V, V])
    _proto(c32.CryptMsgGetParam, B, [V, D, D, V, V])
    _proto(c32.CertEnumCertificatesInStore, V, [V, V])
    _proto(c32.CertGetNameStringW, D, [V, D, D, V, V, D])
    _proto(c32.CertFindCertificateInStore, V, [V, D, D, D, V, V])
    _proto(c32.CertFreeCertificateContext, B, [V])
    _proto(c32.CertCloseStore, B, [V, D])
    _proto(c32.CryptMsgClose, B, [V])
    wt = ctypes.WinDLL("wintrust")
    k32 = ctypes.WinDLL("kernel32")
    H, P = wintypes.HANDLE, ctypes.POINTER
    # WinVerifyTrust(hwnd, GUID*, WINTRUST_DATA*) -> LONG
    _proto(wt.WinVerifyTrust, ctypes.c_long, [H, V, V])
    _proto(wt.CryptCATAdminAcquireContext, B, [P(H), V, D])
    _proto(wt.CryptCATAdminAcquireContext2, B, [P(H), V, wintypes.LPCWSTR, V, D])
    _proto(wt.CryptCATAdminCalcHashFromFileHandle, B, [H, P(D), V, D])
    _proto(wt.CryptCATAdminCalcHashFromFileHandle2, B, [H, H, P(D), V, D])
    _proto(wt.CryptCATAdminEnumCatalogFromHash, H, [H, V, D, D, V])
    _proto(wt.CryptCATCatalogInfoFromContext, B, [H, V, D])
    _proto(wt.CryptCATAdminReleaseCatalogContext, B, [H, H, D])
    _proto(wt.CryptCATAdminReleaseContext, B, [H, D])
    _proto(k32.CreateFileW, H,
           [wintypes.LPCWSTR, D, D, V, D, D, H])
    _proto(k32.CloseHandle, B, [H])
    _api_cache = SimpleNamespace(c32=c32, wt=wt, k32=k32)
    return _api_cache


_WINDIR = os.environ.get("SystemRoot", "c:\\windows").lower().replace("/", "\\")


def _is_under(path: str, root: str) -> bool:
    """True si `path` es `root` o cuelga de `root` (compara con separador)."""
    p = path.lower().replace("/", "\\")
    r = root.lower().replace("/", "\\").rstrip("\\")
    return bool(r) and (p == r or p.startswith(r + "\\"))


def _verify_catalog(path: str, algo: str | None = None) -> bool:
    """True si el archivo está firmado por un catálogo del sistema (.cat).

    `algo` = 'SHA256' usa AcquireContext2 (Win8+); None usa el clásico (SHA-1).
    """
    api = _api()
    wt, k32 = api.wt, api.k32
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


def _is_invalid_signature(ret: int) -> bool:
    """Códigos que significan 'hay firma pero NO es válida' (alterado, revocado,
    expirado, cadena no confiable)."""
    return (ret in (_TRUST_E_BAD_DIGEST, _TRUST_E_EXPLICIT_DISTRUST,
                    _TRUST_E_CERT_SIGNATURE)
            or (ret & 0xFFFFFF00) == 0x800B0100)   # CERT_E_* (0x800B01xx)


def _verify_signature(path: str) -> tuple[bool, bool] | None:
    """(firmado, firma_válida), o None si el resultado es indeterminado (error
    de IO/permisos: no es evidencia de nada). Chequea firma embebida y catálogo."""
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
    if _is_invalid_signature(ret):
        return True, False                # firmado pero inválido (alterado/expirado)
    return None                           # CRYPT_E_FILE_ERROR, acceso denegado, etc.


def _signer_name(path: str) -> str | None:
    """Nombre del firmante (subject del certificado). Best-effort."""
    CERT_QUERY_OBJECT_FILE = 1
    CERT_QUERY_CONTENT_FLAG_ALL = 0x00003FFE
    CERT_QUERY_FORMAT_FLAG_ALL = 0x0000000E
    PKCS_7_ASN_ENCODING = 0x00010000
    X509_ASN_ENCODING = 0x00000001
    CMSG_SIGNER_INFO_PARAM = 6
    CERT_NAME_SIMPLE_DISPLAY_TYPE = 4
    CERT_FIND_SUBJECT_CERT = 0x000B0000
    try:
        crypt32 = _api().c32
        h_store = ctypes.c_void_p()
        h_msg = ctypes.c_void_p()
        ok = crypt32.CryptQueryObject(
            CERT_QUERY_OBJECT_FILE, ctypes.c_wchar_p(path),
            CERT_QUERY_CONTENT_FLAG_ALL, CERT_QUERY_FORMAT_FLAG_ALL, 0,
            None, None, None, ctypes.byref(h_store), ctypes.byref(h_msg), None)
        if not ok:
            return None
        try:
            size = wintypes.DWORD()
            if not crypt32.CryptMsgGetParam(
                    h_msg, CMSG_SIGNER_INFO_PARAM, 0, None, ctypes.byref(size)):
                return None
            buf = ctypes.create_string_buffer(size.value)
            if not crypt32.CryptMsgGetParam(
                    h_msg, CMSG_SIGNER_INFO_PARAM, 0, buf, ctypes.byref(size)):
                return None
            # El store PKCS7 trae también CA y timestamp: hay que ubicar el cert
            # del firmante por Issuer+SerialNumber del SignerInfo.
            signer = ctypes.cast(buf, ctypes.POINTER(_CMSG_SIGNER_INFO)).contents
            cert_info = _CERT_INFO()
            cert_info.Issuer = signer.Issuer
            cert_info.SerialNumber = signer.SerialNumber
            ctx = crypt32.CertFindCertificateInStore(
                h_store, X509_ASN_ENCODING | PKCS_7_ASN_ENCODING, 0,
                CERT_FIND_SUBJECT_CERT, ctypes.byref(cert_info), None)
            if not ctx:
                return None
            try:
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
                crypt32.CertFreeCertificateContext(ctx)  # antes se filtraba
        finally:
            if h_store:
                crypt32.CertCloseStore(h_store, 0)
            if h_msg:
                crypt32.CryptMsgClose(h_msg)
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
    ok = any(_is_under(p, r) for r in normal_roots if r)
    bad = any(m in p for m in suspicious_marks)
    return ok, bad


class WindowsTrustEvaluator(TrustEvaluator):
    """Evalúa confianza en Windows. Cachea por (ruta, mtime_ns, tamaño): si el
    archivo cambia se re-evalúa. Los resultados indeterminados (UNKNOWN) no se
    cachean para que un error transitorio no quede fijado."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[tuple[int, int], TrustInfo]] = {}

    def evaluate(self, exe_path: str) -> TrustInfo:
        if not exe_path:
            return TrustInfo(level=TRUST_UNKNOWN)
        try:
            st = os.stat(exe_path)
        except OSError:
            return TrustInfo(level=TRUST_UNKNOWN, exe_path=exe_path)
        key = (st.st_mtime_ns, st.st_size)
        hit = self._cache.get(exe_path)
        if hit is not None and hit[0] == key:
            return hit[1]
        info = self._evaluate(exe_path)
        if info.level != TRUST_UNKNOWN:
            self._cache[exe_path] = (key, info)
        else:
            self._cache.pop(exe_path, None)
        return info

    def _evaluate(self, exe_path: str) -> TrustInfo:
        try:
            result = _verify_signature(exe_path)
        except Exception:  # noqa: BLE001
            return TrustInfo(level=TRUST_UNKNOWN, exe_path=exe_path)
        if result is None:
            return TrustInfo(level=TRUST_UNKNOWN, exe_path=exe_path)
        signed, valid = result

        signer = _signer_name(exe_path) if signed and valid else None
        loc_ok, loc_bad = _location_ok(exe_path)
        has_meta = _file_description(exe_path) is not None

        is_system = _is_under(exe_path, _WINDIR)
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
