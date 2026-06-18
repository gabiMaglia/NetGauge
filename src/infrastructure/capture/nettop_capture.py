"""Captura por proceso en macOS usando el comando `nettop` (best-effort).

`nettop -P -x -L 0 -J bytes_in,bytes_out` imprime, cada `-s` segundos, un bloque
CSV con una fila de encabezado (",bytes_in,bytes_out,") seguida de una fila por
proceso con el formato "<nombre>.<pid>,<bytes_in>,<bytes_out>,". Los contadores
son ACUMULATIVOS desde que el proceso abrió sus sockets (igual que
psutil.net_io_counters()), por lo que esta clase calcula deltas entre samples
consecutivos por PID, descartando el primer sample (no hay base de referencia).

No requiere privilegios de Administrador ni entitlements especiales; es
best-effort (puede no ver todo el tráfico, p.ej. de la propia VPN/proxy).
Si el binario no existe o el proceso falla, lanza CaptureUnavailable y la
fábrica cae a PsutilCaptureService, igual que hace Windows con ETW.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from typing import Callable, Iterable

from ...domain.models import TrafficSample
from ...domain.ports import CaptureService

log = logging.getLogger(__name__)


class CaptureUnavailable(RuntimeError):
    """`nettop` no está disponible en este entorno."""


def parse_nettop_block(lines: Iterable[str]) -> dict[int, tuple[str, int, int]]:
    """Parsea un bloque de salida de `nettop -P -x -J bytes_in,bytes_out`.

    Devuelve {pid: (nombre_proceso, bytes_in_acumulados, bytes_out_acumulados)}.
    Ignora la fila de encabezado y cualquier línea que no matchee el formato
    "<nombre>.<pid>,<in>,<out>,".
    """
    result: dict[int, tuple[str, int, int]] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(","):
            continue  # encabezado: ",bytes_in,bytes_out,"
        parts = line.split(",")
        if len(parts) < 3:
            continue
        ident, bytes_in_s, bytes_out_s = parts[0], parts[1], parts[2]
        if "." not in ident:
            continue
        name, _, pid_s = ident.rpartition(".")
        if not name or not pid_s.isdigit():
            continue
        try:
            bytes_in = int(bytes_in_s)
            bytes_out = int(bytes_out_s)
        except ValueError:
            continue
        result[int(pid_s)] = (name, bytes_in, bytes_out)
    return result


def split_into_blocks(stream_lines: Iterable[str]) -> Iterable[list[str]]:
    """Agrupa líneas de salida continua de `nettop -L 0` en bloques por sample.

    Cada bloque nuevo arranca con la fila de encabezado (",bytes_in,bytes_out,").
    """
    block: list[str] = []
    for line in stream_lines:
        if line.strip().startswith(",") and block:
            yield block
            block = []
        block.append(line)
    if block:
        yield block


class NettopCaptureService(CaptureService):
    """Captura por proceso en macOS vía `nettop`. Best-effort, no privilegiada."""

    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._prev: dict[int, tuple[int, int]] = {}

    @staticmethod
    def is_available() -> bool:
        return shutil.which("nettop") is not None

    def _build_command(self) -> list[str]:
        nettop_path = shutil.which("nettop")
        if not nettop_path:
            raise CaptureUnavailable("`nettop` no está disponible en este sistema.")
        return [
            nettop_path, "-P", "-x", "-L", "0", "-s", str(int(self._interval)),
            "-J", "bytes_in,bytes_out",
        ]

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        cmd = self._build_command()
        self._stop_event.clear()
        self._prev = {}
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1,
            )
        except OSError as exc:
            raise CaptureUnavailable(f"No se pudo iniciar nettop: {exc}") from exc

        self._thread = threading.Thread(
            target=self._loop, args=(on_sample,), daemon=True
        )
        self._thread.start()

    def _loop(self, on_sample: Callable[[TrafficSample], None]) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            for block in split_into_blocks(self._proc.stdout):
                if self._stop_event.is_set():
                    break
                self._emit_deltas(parse_nettop_block(block), on_sample)
        except Exception as exc:  # noqa: BLE001
            log.warning("nettop: error leyendo salida (%s).", exc)

    def _emit_deltas(
        self,
        current: dict[int, tuple[str, int, int]],
        on_sample: Callable[[TrafficSample], None],
    ) -> None:
        new_prev: dict[int, tuple[int, int]] = {}
        for pid, (name, bytes_in, bytes_out) in current.items():
            new_prev[pid] = (bytes_in, bytes_out)
            prev = self._prev.get(pid)
            if prev is None:
                continue  # primer sample del proceso: sin base para delta
            prev_in, prev_out = prev
            recv = max(0, bytes_in - prev_in)
            sent = max(0, bytes_out - prev_out)
            if sent or recv:
                on_sample(
                    TrafficSample(
                        pid=pid, app_name=name, bytes_sent=sent, bytes_recv=recv
                    )
                )
        self._prev = new_prev

    def stop(self) -> None:
        self._stop_event.set()
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=self._interval + 2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 2)
