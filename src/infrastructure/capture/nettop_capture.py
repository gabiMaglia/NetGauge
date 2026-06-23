"""Captura por proceso en macOS usando el comando `nettop` (best-effort).

`nettop -P -x -L 0 -J bytes_in,bytes_out` imprime, cada `-s` segundos, un bloque
CSV con una fila de encabezado (",bytes_in,bytes_out,") seguida de una fila por
proceso con el formato "<nombre>.<pid>,<bytes_in>,<bytes_out>,". Los contadores
son ACUMULATIVOS desde que el proceso abrió sus sockets (igual que
psutil.net_io_counters()), por lo que esta clase calcula deltas entre samples
consecutivos por PID, descartando el primer sample (no hay base de referencia).

Verificado empíricamente en este Mac (T-010) con `nettop -P -x -L 0 -s 1 -J
bytes_in,bytes_out` mientras corría una descarga sostenida: para un mismo PID
los valores de `bytes_in` crecen monótonamente entre bloques consecutivos
(ej. 42000 -> 226800 -> 453600 -> 694400 -> 963200), confirmando que SON
acumulativos. El parseo y el delta simple (current - prev) son correctos.

El bug real de T-010 (picos seguidos de 0 con tráfico sostenido) NO era un
"doble delta": era que `nettop` puede omitir transitoriamente a un PID de un
bloque puntual (timing del pipe, proceso sin syscalls de red ese tick, bloque
truncado, etc.) aunque el proceso siga generando tráfico. La implementación
anterior reconstruía `_prev` solo con los PIDs presentes en el bloque actual,
así que un PID ausente en un solo bloque perdía su base de referencia; al
reaparecer se trataba como "primer sample" y el delta acumulado real (todo lo
transferido durante la ausencia) se descartaba en silencio -> aparecía como 0
en vez de como el consumo continuo real. Ahora `_prev` conserva la última
lectura conocida de cada PID entre bloques (no se borra por ausencia
puntual), y solo se purga tras `_MAX_MISSING_TICKS` bloques consecutivos sin
aparecer (proceso terminado de verdad), evitando además que un PID que vuelve
a aparecer DESPUÉS de purgado se confunda con un reset de contador.

No requiere privilegios de Administrador ni entitlements especiales; es
best-effort (puede no ver todo el tráfico, p.ej. de la propia VPN/proxy).
Si el binario no existe o el proceso falla, lanza CaptureUnavailable y la
fábrica cae a PsutilCaptureService, igual que hace Windows con ETW.

T-011 (bug raíz de los picos→0): `nettop` detecta que su stdout no es un
TTY cuando se lo lanza con `stdout=PIPE` (caso de `subprocess.Popen` común)
y pasa a usar buffering completo de libc, acumulando varios bloques antes
de volcarlos de una sola vez al pipe. Verificado empíricamente en este Mac:
con pipe simple, 8 bloques esperados en ~8s (a 1/s) llegaron TODOS juntos
en una sola ráfaga a t+12.02s. Lanzando `nettop` bajo un pseudo-terminal
(PTY, vía `os.openpty`) en vez de un pipe, `nettop` ve un TTY en su stdout y
usa line-buffering: los mismos 8 bloques llegaron a t=[0.05, 1.05, 2.03,
3.03, 4.03, 5.03, 6.03, 7.02]s, es decir ~1 bloque/seg, cadencia pareja.
Esto elimina el aliasing con el `_rate_tick` de 1s que causaba el patrón
pico-luego-0. Bajo PTY, las líneas llegan terminadas en "\r\n" (traducción
de terminal); el parseo ya tolera esto porque tanto `parse_nettop_block`
como `split_into_blocks` hacen `.strip()` antes de evaluar cada línea.

T-023 (leak de huérfanos): con cierre NO-limpio del proceso padre (force-quit,
crash, `kill -9`, logout), `stop()`/`atexit` no llegan a ejecutarse y el
`nettop` hijo queda reparentado a launchd (ppid=1), vivo indefinidamente.
Cada arranque nuevo lanza otro más -> se acumulan (confirmado empíricamente:
tras `kill -9` al padre, el `nettop` siguió corriendo con ppid=1). Mitigación
de dos capas: (1) al arrancar, `_reap_orphans()` mata cualquier `nettop`
previo del usuario actual cuya línea de comando matchee EXACTAMENTE la
firma propia (ver `_OWN_SIGNATURE_ARGS`), por las dudas que haya quedado
alguno de una sesión anterior; (2) manejo de SIGTERM/SIGINT (instalado desde
`main.py`, solo en macOS) para correr el mismo cleanup que `atexit` ante un
cierre "casi limpio" (ej. `kill` sin -9, logout ordenado). `SIGKILL` no es
atrapable por ningún proceso, así que (1) sigue siendo la red de seguridad
final para los casos que ningún handler puede cubrir.
"""
from __future__ import annotations

import logging
import os
import pty
import select
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


def iter_lines_from_fd(
    fd: int, stop_event: threading.Event, chunk_size: int = 65536
) -> Iterable[str]:
    """Lee de un file descriptor (master de un PTY) y yieldea líneas de texto.

    Usa `select` con timeout corto para poder revisar `stop_event`
    periódicamente y no bloquear `stop()` indefinidamente. Decodea con
    `errors="replace"` (best-effort, igual que `text=True` en Popen).
    """
    buf = b""
    while not stop_event.is_set():
        try:
            ready, _, _ = select.select([fd], [], [], 0.5)
        except (OSError, ValueError):
            break
        if fd not in ready:
            continue
        try:
            chunk = os.read(fd, chunk_size)
        except OSError:
            break  # PTY cerrado del otro lado (proceso terminó)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            yield line.decode(errors="replace")
    if buf:
        yield buf.decode(errors="replace")


def _is_own_nettop_cmdline(cmdline: list[str]) -> bool:
    """True si `cmdline` (de `psutil.Process.cmdline()`) matchea EXACTAMENTE
    la firma de argumentos que usa esta clase (sin contar el intervalo `-s`,
    que varía). Evita matar cualquier otro `nettop` que el usuario/sistema
    pueda tener corriendo con flags distintos.
    """
    if len(cmdline) < 2:
        return False
    exe = cmdline[0]
    if os.path.basename(exe) != "nettop":
        return False
    args = cmdline[1:]
    # Firma propia: ["-P", "-x", "-L", "0", "-s", "<N>", "-J", "bytes_in,bytes_out"]
    if len(args) != 8:
        return False
    if args[0:5] != ["-P", "-x", "-L", "0", "-s"]:
        return False
    if not args[5].isdigit():
        return False
    if args[6:8] != ["-J", "bytes_in,bytes_out"]:
        return False
    return True


class NettopCaptureService(CaptureService):
    """Captura por proceso en macOS vía `nettop`. Best-effort, no privilegiada."""

    # Cantidad de bloques consecutivos sin aparecer tras los cuales se purga
    # la base de un PID (se asume proceso terminado, no ausencia transitoria).
    _MAX_MISSING_TICKS = 3

    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._master_fd: int | None = None
        # pid -> (bytes_in, bytes_out, ticks_ausente_consecutivos)
        self._prev: dict[int, tuple[int, int, int]] = {}

    @staticmethod
    def is_available() -> bool:
        return shutil.which("nettop") is not None

    @staticmethod
    def reap_orphans() -> int:
        """Termina cualquier `nettop` del usuario actual cuya línea de comando
        matchee exactamente nuestra firma (T-023): red de seguridad contra
        huérfanos acumulados por cierres no-limpios de sesiones anteriores.

        SIGTERM primero; si sigue vivo tras un breve margen, SIGKILL. Devuelve
        la cantidad de procesos reapeados (best-effort: nunca lanza).
        """
        import signal as _signal
        import time as _time

        try:
            import psutil
        except Exception:  # noqa: BLE001
            return 0

        current_uid = os.getuid() if hasattr(os, "getuid") else None
        candidates: list["psutil.Process"] = []
        try:
            for proc in psutil.process_iter(["pid", "uids", "cmdline"]):
                try:
                    if current_uid is not None:
                        uids = proc.info.get("uids")
                        if uids is not None and uids.real != current_uid:
                            continue
                    cmdline = proc.info.get("cmdline") or []
                    if _is_own_nettop_cmdline(cmdline):
                        candidates.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                    continue
        except Exception as exc:  # noqa: BLE001
            log.warning("nettop: fallo enumerando procesos para reap (%s).", exc)
            return 0

        reaped = 0
        for proc in candidates:
            try:
                proc.send_signal(_signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                continue
            except Exception as exc:  # noqa: BLE001
                log.warning("nettop: fallo enviando SIGTERM a huérfano (%s).", exc)
                continue
            reaped += 1

        if candidates:
            _time.sleep(0.2)
            for proc in candidates:
                try:
                    if proc.is_running():
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                    continue
                except Exception as exc:  # noqa: BLE001
                    log.warning("nettop: fallo enviando SIGKILL a huérfano (%s).", exc)

        if reaped:
            log.info("nettop: reapeados %d proceso(s) huérfano(s) al arrancar.", reaped)
        return reaped

    def _build_command(self) -> list[str]:
        nettop_path = shutil.which("nettop")
        if not nettop_path:
            raise CaptureUnavailable("`nettop` no está disponible en este sistema.")
        return [
            nettop_path, "-P", "-x", "-L", "0", "-s", str(int(self._interval)),
            "-J", "bytes_in,bytes_out",
        ]

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self.reap_orphans()
        cmd = self._build_command()
        self._stop_event.clear()
        self._prev = {}

        # Lanzar nettop bajo un PTY (en vez de un pipe simple) para que vea
        # su stdout como un TTY y use line-buffering: así entrega cada
        # bloque ~1/s en vez de bufferear varios y volcarlos en ráfaga
        # (causa raíz de T-011, verificado empíricamente en este Mac).
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as exc:
            raise CaptureUnavailable(f"No se pudo abrir un PTY: {exc}") from exc

        try:
            self._proc = subprocess.Popen(
                cmd, stdout=slave_fd, stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError as exc:
            # slave_fd lo cierra el `finally` (corre siempre); acá solo el master
            # para no fugarlo. Cerrar slave en ambos lados sería un doble-close.
            os.close(master_fd)
            raise CaptureUnavailable(f"No se pudo iniciar nettop: {exc}") from exc
        finally:
            os.close(slave_fd)  # el hijo ya tiene su propio fd duplicado

        self._master_fd = master_fd
        self._thread = threading.Thread(
            target=self._loop, args=(on_sample,), daemon=True
        )
        self._thread.start()

    def _loop(self, on_sample: Callable[[TrafficSample], None]) -> None:
        assert self._master_fd is not None
        try:
            lines = iter_lines_from_fd(self._master_fd, self._stop_event)
            for block in split_into_blocks(lines):
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
        new_prev: dict[int, tuple[int, int, int]] = {}

        for pid, (name, bytes_in, bytes_out) in current.items():
            new_prev[pid] = (bytes_in, bytes_out, 0)
            prev = self._prev.get(pid)
            if prev is None:
                continue  # primer sample del proceso: sin base para delta
            prev_in, prev_out, _missing = prev
            delta_in = bytes_in - prev_in
            delta_out = bytes_out - prev_out
            if delta_in < 0 or delta_out < 0:
                # Contador bajó: el proceso reinició sus sockets/PID reciclado.
                # No hay base válida para un delta; se descarta sin pico falso
                # (la próxima lectura ya arranca limpia con el valor actual).
                continue
            recv, sent = delta_in, delta_out
            if sent or recv:
                on_sample(
                    TrafficSample(
                        pid=pid, app_name=name, bytes_sent=sent, bytes_recv=recv
                    )
                )

        # PIDs que tenían base previa pero no aparecieron en este bloque:
        # conservar su última lectura conocida (no perder la base de delta
        # por una ausencia transitoria) salvo que ya lleven demasiados
        # bloques ausentes, en cuyo caso se asume que el proceso terminó.
        for pid, (bytes_in, bytes_out, missing) in self._prev.items():
            if pid in new_prev:
                continue
            missing += 1
            if missing <= self._MAX_MISSING_TICKS:
                new_prev[pid] = (bytes_in, bytes_out, missing)
            # si supera el límite, se purga (no se copia a new_prev) y un
            # futuro reaparición se trata como primer sample, no como reset.

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
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
