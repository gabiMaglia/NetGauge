"""Conexiones de red activas por proceso, vía psutil.

psutil.net_connections() SÍ da el PID de cada conexión (a diferencia del tráfico
por byte, que necesita ETW). Con admin vemos las conexiones de todos los procesos.
"""
from __future__ import annotations

import psutil

from ...domain.models import Connection
from ...domain.ports import ConnectionProvider
from .app_names import friendly_name

# Estados que vale la pena mostrar (descartamos los efímeros sin remoto).
_INTERESTING = {"ESTABLISHED", "SYN_SENT", "CLOSE_WAIT", "LISTEN"}


class PsutilConnectionProvider(ConnectionProvider):
    def connections(self) -> list[Connection]:
        out: list[Connection] = []
        try:
            conns = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, OSError):
            return out
        for c in conns:
            if c.pid is None or c.status not in _INTERESTING:
                continue
            raddr = getattr(c, "raddr", None)
            if not raddr:
                continue
            out.append(Connection(
                app_name=friendly_name(c.pid), pid=c.pid,
                raddr=raddr.ip, rport=raddr.port, status=c.status))
        return out

    def exe_paths(self) -> dict[str, str]:
        paths: dict[str, str] = {}
        for proc in psutil.process_iter(["pid", "exe"]):
            try:
                exe = proc.info.get("exe")
                if not exe:
                    continue
                name = friendly_name(proc.info["pid"])
                paths.setdefault(name, exe)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return paths
