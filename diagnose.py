"""Diagnóstico de ETW. Ejecutar idealmente en PowerShell COMO ADMINISTRADOR:

    .\.venv\Scripts\Activate.ps1
    python diagnose.py

Te dice por qué la captura por proceso (ETW) no se activa.
"""
from __future__ import annotations

import ctypes
import sys


def check_admin() -> bool:
    try:
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] No pude verificar admin: {exc}")
        return False
    print(f"  Admin: {'SÍ' if is_admin else 'NO  <-- ESTE ES EL PROBLEMA si dice NO'}")
    return is_admin


def check_pywintrace() -> bool:
    try:
        import etw  # noqa: F401
        from etw import ETW, ProviderInfo  # noqa: F401
        from etw.GUID import GUID  # noqa: F401
        print("  pywintrace (módulo etw): OK")
        return True
    except ImportError as exc:
        print(f"  pywintrace: NO disponible -> {exc}")
        return False


def try_session() -> None:
    print("\n[3] Intentando abrir sesión ETW de kernel-network...")
    try:
        from etw import ETW, ProviderInfo
        from etw.GUID import GUID

        guid = GUID("{7DD42A49-5329-4832-8DFD-43D979153A88}")
        captured = {"n": 0}

        def cb(event):
            captured["n"] += 1
            if captured["n"] <= 3:
                print(f"    Evento recibido: {event!r}")

        session = ETW(providers=[ProviderInfo("KN", guid)], event_callback=cb)
        session.start()
        print("    Sesión iniciada. Generá tráfico (abrí una web) ~8s...")
        import time
        time.sleep(8)
        session.stop()
        print(f"    Eventos capturados: {captured['n']}")
        if captured["n"] == 0:
            print("    [!] 0 eventos: el provider no emitió. Revisar formato/IDs.")
        else:
            print("    [OK] ETW captura eventos. La integración debería funcionar.")
    except Exception as exc:  # noqa: BLE001
        import traceback
        print(f"    [X] Falló: {exc}")
        traceback.print_exc()


def main() -> None:
    print("=" * 60)
    print("DIAGNÓSTICO ETW - Network Monitor")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print("\n[1] Privilegios:")
    admin = check_admin()
    print("\n[2] Dependencia ETW:")
    has_etw = check_pywintrace()

    if not admin:
        print("\n>>> Abrí PowerShell COMO ADMINISTRADOR y reintentá. Sin admin, ETW no abre.")
        return
    if not has_etw:
        print("\n>>> Instalá pywintrace:  pip install pywintrace")
        return
    try_session()


if __name__ == "__main__":
    main()
