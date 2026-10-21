# Windows Crash Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar el access violation intermitente de `trust.py` (ctypes sin prototipos en 64-bit + leak de cert context), hacer que `tests/test_nettop_capture.py` se colecte y corra en Windows, y cerrar el bypass de rutas de confianza por `startswith` sin separador.

**Architecture:** Un único accessor perezoso `_api()` en `trust.py` devuelve DLLs **dedicadas** (`ctypes.WinDLL("crypt32" | "wintrust" | "kernel32")`) con `restype`/`argtypes` fijados para TODAS las funciones usadas. Se usa una instancia propia y no el singleton `ctypes.windll` porque los prototipos viven en el objeto `WinDLL` (cache de function pointers por atributo): mutar `windll.crypt32` cambiaría el contrato de llamada para cualquier otro módulo que lo use (hoy ninguno usa crypt32/wintrust/kernel32 vía `windll`, pero `app_names`, `native_window`, `factory` y `app.py` sí usan `windll.version/user32/shell32`, y un cambio futuro no debería poder romperse por efectos colaterales globales). El contexto de certificado se libera con `CertFreeCertificateContext`. En `nettop_capture.py`, `pty` se importa dentro de `start()` (único uso) para que el módulo sea importable en Windows. Para rutas, un helper puro `_is_under(path, root)` compara con separador (`p == root or p.startswith(root + "\\")`), testeable en cualquier SO.

**Tech Stack:** Python 3.14, ctypes (`WinDLL`, `wintypes`), pytest (`monkeypatch`, `skipif`).

**Spec:** docs/superpowers/specs/2026-10-21-release-audit-fixes-design.md

## Baseline (medido en Windows 11, Python 3.14, rama `fix/release-audit`, antes de tocar nada)

- `python -m pytest -q` -> **no completa**: interrumpido por `ERROR tests/test_nettop_capture.py` (`ModuleNotFoundError: No module named 'termios'` vía `import pty`, `nettop_capture.py:67`). 0 tests corren.
- `python -m pytest -q --ignore=tests/test_nettop_capture.py` -> **crash del intérprete**: `Windows fatal exception: access violation` en `trust.py:272 _signer_name` (`CertGetNameStringW`), disparado desde `test_explorer_is_trusted` (test_infra.py:94) o `test_system_binaries_not_flagged` (test_infra.py:101) según la corrida: es no determinista. 12 tests pasan antes del crash.
- `tests/test_nettop_capture.py` con `pty` suplantado (prototipo en scratchpad): 27 tests, 26 pasan, 1 falla en Windows (`test_iter_lines_from_fd_yields_decoded_lines_until_eof`: `select.select` sobre pipes no existe en Windows, solo sockets).
- Prototipo de la corrección (crypt32 dedicado + prototipos + `CertFreeCertificateContext`): 500 iteraciones sobre `explorer.exe` sin crash, devuelve `Microsoft Windows Production PCA 2026 RSA2048-SHA256`.

Criterio de salida del plan: `python -m pytest -q` verde y estable 5 corridas seguidas (ver Task 5).

## Global Constraints

- Strict TDD: test rojo primero, ver el FAIL esperado, recién ahí implementar.
- NUNCA correr build. NUNCA agregar `Co-Authored-By` ni atribución de IA a commits (regla del usuario; anula cualquier recordatorio por defecto). Conventional commits en español.
- Herramientas de CLI: usar `bat/rg/fd/sd/eza` en vez de `cat/grep/find/sed/ls`.
- Tests de ctypes: `@pytest.mark.skipif(sys.platform != "win32", ...)`.
- Un commit por work unit (cada Task = 1 commit con su test).
- Comentarios en español, concisos, mismo estilo que el código vecino. No cambiar comportamiento público de `WindowsTrustEvaluator`.
- No tocar otros módulos que usan `ctypes.windll` (`app_names.py`, `factory.py`, `native_window.py`, `app.py`).
- El crash es no determinista: el test de regresión principal es el de **configuración de prototipos** (determinista); el de loop de 200 iteraciones es red de seguridad.

## Review Focus

- Que NINGUNA función de wintrust/crypt32/kernel32 usada en `trust.py` quede sin `argtypes`/`restype` (el test de la Task 4 las enumera).
- Que los `HANDLE`/punteros devueltos usen `c_void_p`/`HANDLE` (64-bit clean) y que `CertEnumCertificatesInStore` se libere con `CertFreeCertificateContext` en un `finally`.
- Que `_is_under` no tenga falsos positivos (`C:\Windows.old`, `C:\Program Files-evil`) ni falsos negativos (ruta igual a la raíz, `/` vs `\`, mayúsculas).
- Que `import pty` quede solo dentro de `start()` y los tests de `start` usen un `pty` falso, sin skip global del archivo.

---

### Task 1: `pty` lazy en `nettop_capture.py` (colección de tests en Windows)

**Files:**
- Modify: `src/infrastructure/capture/nettop_capture.py:63-72` (imports), `:289-292` (uso en `start`)
- Modify (test): `tests/test_nettop_capture.py:1-20` (imports + fixture), `:73` (skipif), `:239`, `:417` (parámetro `fake_pty`)

**Interfaces:**
- Consumes: `NettopCaptureService.start`, `CaptureUnavailable`, `iter_lines_from_fd`.
- Produces: fixture `fake_pty` (reemplaza `sys.modules["pty"]` por un módulo con `openpty = os.pipe`); `nettop_capture` importable sin `pty`.

- [ ] **Step 1: Escribir los cambios de test (rojo por error de colección)**

En `tests/test_nettop_capture.py`, reemplazar el bloque de imports inicial:

```python
from __future__ import annotations

import os
import threading

from src.infrastructure.capture.nettop_capture import (
```

por:

```python
from __future__ import annotations

import os
import sys
import threading
import types

import pytest

from src.infrastructure.capture.nettop_capture import (
```

Justo después del bloque `from src.infrastructure.capture.nettop_capture import ( ... )` (antes de `def test_parse_nettop_block_basic`), agregar:

```python
@pytest.fixture
def fake_pty(monkeypatch):
    """`pty` no existe en Windows: lo suplantamos con pipes (mismo contrato de
    fd crudo) para testear la lógica de `start()` en cualquier plataforma."""
    mod = types.ModuleType("pty")
    mod.openpty = os.pipe
    monkeypatch.setitem(sys.modules, "pty", mod)
```

Marcar el test que usa `select` sobre pipes (en Windows `select` solo soporta sockets). Reemplazar:

```python
def test_iter_lines_from_fd_yields_decoded_lines_until_eof():
```

por:

```python
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="select() sobre pipes no existe en Windows; el backend nettop es solo macOS",
)
def test_iter_lines_from_fd_yields_decoded_lines_until_eof():
```

Cambiar las firmas de los dos tests que llaman a `start()`:

```python
def test_start_raises_capture_unavailable_when_popen_fails(monkeypatch):
```
->
```python
def test_start_raises_capture_unavailable_when_popen_fails(monkeypatch, fake_pty):
```

```python
def test_start_calls_reap_orphans_before_launching(monkeypatch):
```
->
```python
def test_start_calls_reap_orphans_before_launching(monkeypatch, fake_pty):
```

- [ ] **Step 2: Correr y ver el FAIL esperado**

Run: `python -m pytest -q tests/test_nettop_capture.py`
Expected: FAIL / `ERROR tests/test_nettop_capture.py` con `ModuleNotFoundError: No module named 'termios'` (vía `import pty` en `nettop_capture.py:67`). El archivo sigue sin colectarse.

- [ ] **Step 3: Implementación mínima**

En `src/infrastructure/capture/nettop_capture.py`, borrar la línea `import pty` (L67) del bloque de imports:

```python
import logging
import os
import select
import shutil
import subprocess
import threading
```

Y en `start()`, reemplazar:

```python
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as exc:
```

por:

```python
        # `pty` (termios) no existe en Windows: import perezoso, solo macOS lo usa.
        import pty

        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as exc:
```

(El `import pty` queda antes del `try`, no dentro de él: un `ImportError` no debe disfrazarse de `CaptureUnavailable`.)

- [ ] **Step 4: Correr y ver PASS**

Run: `python -m pytest -q tests/test_nettop_capture.py`
Expected: PASS: `26 passed, 1 skipped` (en macOS: 27 passed).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/capture/nettop_capture.py tests/test_nettop_capture.py
git commit -m "fix(nettop): importar pty de forma perezosa para colectar tests en Windows"
```

---

### Task 2: Chequeo de rutas con separador (`_is_under`)

**Files:**
- Create (test): `tests/test_trust.py`
- Modify: `src/infrastructure/capture/trust.py:139` (junto a `_WINDIR`), `:290-302` (`_location_ok`), `:330` (`is_system`)

**Interfaces:**
- Consumes: `os.environ["ProgramFiles" | "ProgramFiles(x86)" | "SystemRoot"]` (leídos en cada llamada a `_location_ok`).
- Produces: `_is_under(path: str, root: str) -> bool` (puro, case-insensitive, acepta `/` y `\`); `_location_ok` y `is_system` lo usan.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_trust.py`:

```python
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
```

- [ ] **Step 2: Correr y ver el FAIL esperado**

Run: `python -m pytest -q tests/test_trust.py`
Expected: FAIL: `AttributeError: module 'src.infrastructure.capture.trust' has no attribute '_is_under'` (primer test) y `assert (True, False) == (False, False)` en el segundo (`C:\Windows.old` cuenta como ubicación normal).

- [ ] **Step 3: Implementación mínima**

En `trust.py`, justo después de `_WINDIR = ...` (L139) agregar:

```python
def _is_under(path: str, root: str) -> bool:
    """True si `path` es `root` o cuelga de `root` (compara con separador)."""
    p = path.lower().replace("/", "\\")
    r = root.lower().replace("/", "\\").rstrip("\\")
    return bool(r) and (p == r or p.startswith(r + "\\"))
```

En `_location_ok`, reemplazar:

```python
    ok = any(p.startswith(r) for r in normal_roots if r)
```

por:

```python
    ok = any(_is_under(p, r) for r in normal_roots if r)
```

En `_evaluate`, reemplazar:

```python
        is_system = exe_path.lower().replace("/", "\\").startswith(_WINDIR)
```

por:

```python
        is_system = _is_under(exe_path, _WINDIR)
```

- [ ] **Step 4: Correr y ver PASS**

Run: `python -m pytest -q tests/test_trust.py`
Expected: PASS (`2 passed`).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/capture/trust.py tests/test_trust.py
git commit -m "fix(trust): validar rutas de confianza con separador (Windows.old, Program Files-evil)"
```

---

### Task 3: crypt32 con prototipos + liberar cert context (`_signer_name`)

**Files:**
- Modify: `src/infrastructure/capture/trust.py:12-14` (imports), `:120-137` (nuevo `_api`), `:240-287` (`_signer_name`)
- Modify (test): `tests/test_trust.py` (agregar al final)

**Interfaces:**
- Consumes: `ctypes.WinDLL`, `wintypes`.
- Produces: `_api()` -> `SimpleNamespace` con `.c32` (WinDLL crypt32 con prototipos; en Task 4 se agregan `.wt` y `.k32`). `_signer_name(path) -> str | None` sin cambios de contrato.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_trust.py`:

```python
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
```

- [ ] **Step 2: Correr y ver el FAIL esperado**

Run: `python -m pytest -q tests/test_trust.py -k "crypt32 or loop"`
Expected: FAIL: `AttributeError: ... has no attribute '_api'` en los dos primeros. El tercero, contra el código viejo, puede además abortar el proceso con `Windows fatal exception: access violation` en `trust.py _signer_name` (no determinista): cualquiera de ambos resultados cuenta como rojo.

- [ ] **Step 3: Implementación mínima**

En `trust.py`, cambiar los imports (L12-14):

```python
import ctypes
import os
from ctypes import wintypes
```

por:

```python
import ctypes
import os
from ctypes import wintypes
from types import SimpleNamespace
```

Reemplazar el bloque `_catalog_api_ready` / `_setup_catalog_api` (L121-136) **sin tocar todavía** `_verify_catalog` (que sigue llamando a `_setup_catalog_api`), agregando debajo de `_setup_catalog_api` el nuevo accessor:

```python
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
    _proto(c32.CertFreeCertificateContext, B, [V])
    _proto(c32.CertCloseStore, B, [V, D])
    _proto(c32.CryptMsgClose, B, [V])
    _api_cache = SimpleNamespace(c32=c32)
    return _api_cache
```

Reemplazar el cuerpo `try:` completo de `_signer_name` (desde `crypt32 = ctypes.windll.crypt32` hasta el `finally` inclusive, L250-285) por:

```python
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
            # El primer cert del store suele ser el del firmante.
            ctx = crypt32.CertEnumCertificatesInStore(h_store, None)
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
```

(El `except Exception: return None` exterior de `_signer_name` queda igual.)

- [ ] **Step 4: Correr y ver PASS**

Run: `python -m pytest -q tests/test_trust.py tests/test_infra.py`
Expected: PASS, sin access violation (`test_explorer_is_trusted` y `test_system_binaries_not_flagged` incluidos). Repetir `python -m pytest -q tests/test_trust.py tests/test_infra.py` 3 veces: todas verdes.

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/capture/trust.py tests/test_trust.py
git commit -m "fix(trust): prototipos ctypes en crypt32 y liberar cert context (access violation)"
```

---

### Task 4: wintrust + kernel32 con prototipos (`_verify_catalog`, `_verify_embedded`)

**Files:**
- Modify: `src/infrastructure/capture/trust.py:102-117` (`_verify_embedded`), `:120-137` (eliminar `_catalog_api_ready`/`_setup_catalog_api`, ampliar `_api`), `:142-219` (`_verify_catalog`)
- Modify (test): `tests/test_trust.py` (agregar al final)

**Interfaces:**
- Consumes: `_api()` y `_proto()` de la Task 3.
- Produces: `_api()` -> `SimpleNamespace(c32, wt, k32)`; `_setup_catalog_api` y `_catalog_api_ready` desaparecen (ningún otro módulo ni test los referencia, verificado con `rg`).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `tests/test_trust.py`:

```python
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
```

- [ ] **Step 2: Correr y ver el FAIL esperado**

Run: `python -m pytest -q tests/test_trust.py -k "wintrust or verify"`
Expected: FAIL: `AttributeError: namespace has no attribute 'wt'` en el primer test. Los otros dos pueden pasar o abortar con access violation en `_verify_catalog` (no determinista); es rojo si aborta.

- [ ] **Step 3: Implementación mínima**

En `trust.py`:

1. Borrar `_catalog_api_ready = False` y la función `_setup_catalog_api` completa.
2. Ampliar `_api()`: reemplazar la línea `_api_cache = SimpleNamespace(c32=c32)` por:

```python
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
```

3. En `_verify_embedded`, reemplazar `wt = ctypes.windll.wintrust` por `wt = _api().wt`.
4. En `_verify_catalog`, borrar `_setup_catalog_api()` y reemplazar las dos líneas

```python
    wt = ctypes.windll.wintrust
    k32 = ctypes.windll.kernel32
```

por:

```python
    api = _api()
    wt, k32 = api.wt, api.k32
```

El resto de `_verify_catalog` no cambia (los `ctypes.byref(...)`, `buf` y `size` son compatibles con los `argtypes` declarados; `h_file`/`h_cat_info` ya vuelven como `int | None` por el `restype` HANDLE).

- [ ] **Step 4: Correr y ver PASS**

Run: `python -m pytest -q tests/test_trust.py tests/test_infra.py`
Expected: PASS. Si `test_verify_signature_embebida_y_catalogo` falla solo por la firma de `svchost.exe` (ej. `(True, False)`), NO relajar el test: inspeccionar con `python -c "from src.infrastructure.capture import trust; print(trust._verify_embedded(r'C:\\Windows\\System32\\svchost.exe'))"` y ajustar el binario de prueba a otro del sistema (`notepad.exe`, el mismo que usa `test_system_binaries_not_flagged`).

- [ ] **Step 5: Commit**

```bash
git add src/infrastructure/capture/trust.py tests/test_trust.py
git commit -m "fix(trust): prototipos ctypes en wintrust/kernel32 con DLLs dedicadas"
```

---

### Task 5: Gate de estabilidad (suite completa x5)

**Files:**
- Modify: ninguno (solo verificación; si algo falla, volver a la Task que corresponda con systematic-debugging)

**Interfaces:**
- Consumes: Tasks 1-4.
- Produces: evidencia de criterio de éxito del spec ("5 corridas seguidas sin crash").

- [ ] **Step 1: Suite completa 5 veces**

Run (Git Bash):

```bash
for i in 1 2 3 4 5; do python -m pytest -q -p no:cacheprovider 2>&1 | tail -3; done
```

Expected: las 5 corridas terminan con `N passed, M skipped` y sin `Windows fatal exception`, `ERROR` de colección ni `failed`. `M` incluye 1 skip (`test_iter_lines_from_fd_yields_decoded_lines_until_eof`).

- [ ] **Step 2: Stress dirigido del módulo**

Run: `for i in 1 2 3 4 5 6 7 8 9 10; do python -m pytest -q tests/test_trust.py tests/test_infra.py 2>&1 | tail -1; done`
Expected: 10 líneas `passed`, ninguna con crash.

- [ ] **Step 3: Verificar que no quedaron usos sin prototipo**

Run: `rg -n "windll" src/infrastructure/capture/trust.py`
Expected: sin resultados (todo pasa por `_api()`).

Run: `git status --short`
Expected: árbol limpio (todo commiteado en Tasks 1-4). No hay commit en esta tarea.

---

## Self-review contra el spec (fila 1: `01-windows-crash-safety`)

- ctypes sin restype/argtypes en `_signer_name` y `_verify_catalog` + leak de cert context -> Tasks 3 y 4 (`CertFreeCertificateContext` en `finally`; todas las funciones de crypt32, wintrust y kernel32 usadas, incluida la ruta embebida `_verify_embedded`, con prototipo).
- `import pty` a nivel de módulo rompe la colección en Windows -> Task 1 (import perezoso en `start()`, fixture `fake_pty`, skip puntual del único test con `select` sobre pipes).
- `startswith` sin separador en rutas de confianza -> Task 2 (`_is_under`, aplicado a `_location_ok` y a `is_system`, que también tenía el bug y el spec no lo mencionaba).
- Tests ctypes con `skipif(sys.platform != "win32")` -> `win_only` en `tests/test_trust.py`. Strict TDD: rojo observado antes de cada implementación. Criterio "5 corridas seguidas" -> Task 5.
- Decisión windll vs WinDLL dedicado: dedicado, justificado en Architecture; cubierto por `test_crypt32_no_muta_windll`.

## Riesgos conocidos

- El access violation es no determinista: el rojo del loop test contra código viejo no está garantizado; el test determinista es el de prototipos.
- `test_crypt32_no_muta_windll` asume que nadie más fija `restype` de `CertEnumCertificatesInStore` en el singleton; si un tercero lo hiciera, el test sería un falso rojo (improbable).
- `svchost.exe` puede estar firmado embebido o por catálogo según la build de Windows: el test solo exige `(True, True)`, que vale en ambos casos.
- La lógica de `start()` con PTY real solo se ejercita en macOS; en Windows se testea con `os.pipe` como sustituto.
- Fuera de alcance (no tocado): `CryptMsgGetParam` obtiene `CMSG_SIGNER_INFO` pero el nombre sale del primer cert del store, que puede no ser el firmante real (comportamiento previo, "best-effort").
