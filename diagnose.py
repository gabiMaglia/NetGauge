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


def try_session(seconds: int = 15) -> None:
    print("\n[3] Capturando eventos de kernel-network para VALIDAR el mapeo...")
    print("    >>> Generá tráfico real: abrí webs, mirá un video, descargá algo. <<<")
    try:
        import time
        from collections import defaultdict

        from etw import ETW, ProviderInfo
        from etw.GUID import GUID

        guid = GUID("{7DD42A49-5329-4832-8DFD-43D979153A88}")
        # Estadística por event_id: cuántos, bytes totales, y un sample de campos.
        stats = defaultdict(lambda: {"count": 0, "bytes": 0, "sample": None})

        def _get(d, *keys):
            for k in keys:
                if k in d:
                    return d[k]
            # búsqueda case-insensitive
            low = {str(kk).lower(): vv for kk, vv in d.items()}
            for k in keys:
                if k.lower() in low:
                    return low[k.lower()]
            return None

        def cb(event):
            try:
                event_id, data = event
            except (ValueError, TypeError):
                return
            s = stats[event_id]
            s["count"] += 1
            size = _get(data, "size", "Size", "NumBytes", "TransferSize")
            if isinstance(size, (int, float)):
                s["bytes"] += int(size)
            if s["sample"] is None and isinstance(data, dict):
                s["sample"] = dict(list(data.items())[:12])

        session = ETW(providers=[ProviderInfo("KN", guid)], event_callback=cb)
        session.start()
        print(f"    Sesión iniciada. Capturando {seconds}s...")
        time.sleep(seconds)
        session.stop()

        total = sum(v["count"] for v in stats.values())
        print(f"\n    === RESULTADO: {total} eventos en {len(stats)} event_ids ===")
        if total == 0:
            print("    [!] 0 eventos. El provider no emitió (¿sin tráfico? ¿IDs?).")
            return
        print("    event_id |  count |     bytes_sum | campos (sample)")
        print("    ---------+--------+---------------+------------------------------")
        for eid in sorted(stats):
            v = stats[eid]
            keys = ", ".join(str(k) for k in (v["sample"] or {}).keys())
            print(f"    {eid:>8} | {v['count']:>6} | {v['bytes']:>13} | {keys}")
        print("\n    >>> PEGAME ESTA TABLA + un sample de campos de 1-2 event_ids:")
        for eid in sorted(stats)[:4]:
            print(f"      [{eid}] {stats[eid]['sample']}")
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
