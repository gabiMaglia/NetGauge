"""Captura por proceso en macOS usando el comando `nettop` (best-effort).

Estrategia actual (fix/nettop-cpu): POLLING de snapshots one-shot.
Cada `interval` segundos (2 s por defecto) se ejecuta
`nettop -P -x -L 1 -J bytes_in,bytes_out`, que imprime UN bloque CSV (encabezado
",bytes_in,bytes_out," + una fila "<nombre>.<pid>,<bytes_in>,<bytes_out>," por
proceso) y termina. Los contadores son ACUMULATIVOS por proceso (igual que
psutil.net_io_counters()), así que se calculan deltas entre snapshots
consecutivos por PID, descartando el primero (no hay base de referencia).

Qué se descartó y por qué: el modo streaming `nettop -L 0 -s N` (un proceso
persistente que imprime un bloque cada N s). Ese modo mantiene una suscripción
PERSISTENTE a NetworkStatistics: el proceso recibe y procesa cada evento de
cada flow del kernel (el filtrado -P/-p/-t es del lado cliente) y consume
~100-120 % de CPU constante en un i7 Intel / macOS 14, sin importar -s, -m, -t
ni filtrar a un solo PID (medido). Un snapshot one-shot cuesta ~0.08 s de CPU
(~4-5 % de un core a 1 snapshot/2 s) y la exactitud es la misma (descarga de
10 MB: streaming 10.02 MB, polling 1 s y 2 s: 10.02 MB).

Limitación conocida del polling: un flow que nace y muere ENTRE dos snapshots
no se ve (conexiones sub-intervalo), y los últimos bytes de un flow que cierra
justo antes del siguiente snapshot se pierden (el contador del proceso baja y
ese tramo se descarta). Es aceptable para tráfico sostenido.

Historia que sigue vigente:
- T-010: `nettop` puede omitir transitoriamente a un PID de un snapshot. `_prev`
  conserva la última lectura de cada PID y solo se purga tras
  `_MAX_MISSING_TICKS` snapshots consecutivos sin aparecer, así el delta al
  reaparecer incluye lo transferido durante la ausencia (sin duplicar ni perder).
  Si un contador baja (flows cerrados / PID reciclado) no se emite delta negativo.
- T-011 (PTY) YA NO APLICA: el PTY existía para evitar el buffering completo de
  libc del stream persistente por pipe. Con `-L 1` el proceso termina y
  flushea al salir, así que alcanza un pipe común.
- T-023: con el streaming, un cierre no-limpio dejaba un `nettop -L 0` huérfano
  (ppid=1) para siempre. Ya no se mantiene un hijo vivo (cada snapshot dura
  ~0.1 s y tiene timeout), pero `reap_orphans()` y el handler de señales de
  `main.py` se conservan como red de seguridad contra huérfanos de versiones
  previas que sigan corriendo; solo matchean la firma vieja `-L 0`.
- T-025: `nettop` trunca el nombre; se resuelve el real por PID con psutil.

No requiere privilegios de Administrador. Si el binario no existe lanza
CaptureUnavailable; si los snapshots fallan N veces seguidas se marca
`failed` y se avisa a `on_failure` (FallbackCaptureService degrada a psutil).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
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
    """Captura por proceso en macOS vía snapshots `nettop -L 1`. Best-effort."""

    # Snapshots consecutivos sin ausencia de un PID tras los cuales se purga
    # su base (se asume proceso terminado, no ausencia transitoria).
    _MAX_MISSING_TICKS = 3

    # Fallos SEGUIDOS de snapshot (error, timeout o salida vacía) tras los
    # cuales se abandona nettop. Backoff entre fallos: 1, 2, 4, 8 s (tope 30).
    _MAX_FAILURES = 5
    _FAILURE_BASE_DELAY = 1.0
    _FAILURE_MAX_DELAY = 30.0

    # Un snapshot dura ~0.1 s; si tarda más de esto algo anda mal.
    _SNAPSHOT_TIMEOUT = 5.0

    def __init__(
        self,
        interval: float = 2.0,
        runner: Callable[[list[str], float], str] | None = None,
    ) -> None:
        self.interval = interval
        # Inyectable para tests: (cmd, timeout) -> stdout del snapshot.
        self._runner = runner or self._run_nettop
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        # pid -> (bytes_in, bytes_out, ticks_ausente_consecutivos)
        self._prev: dict[int, tuple[int, int, int]] = {}
        # pid -> nombre real resuelto (T-025), cacheado por PID.
        self._name_cache: dict[int, str] = {}
        self._proc_lock = threading.Lock()
        # Salud: si nettop no se puede sostener, failed=True y se avisa a
        # on_failure (lo engancha FallbackCaptureService para degradar a psutil).
        self.failed = False
        self.on_failure: Callable[[], None] | None = None

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
        return [nettop_path, "-P", "-x", "-L", "1", "-J", "bytes_in,bytes_out"]

    def start(self, on_sample: Callable[[TrafficSample], None]) -> None:
        self.reap_orphans()
        self._build_command()  # falla rápido (CaptureUnavailable) si no hay nettop
        self._stop_event.clear()
        self._prev = {}
        self._name_cache = {}
        self.failed = False
        self._thread = threading.Thread(
            target=self._loop, args=(on_sample,), daemon=True
        )
        self._thread.start()

    def _run_nettop(self, cmd: list[str], timeout: float) -> str:
        """Ejecuta un snapshot y devuelve su stdout. Sin PTY: con `-L 1` el
        proceso termina y flushea. Guarda el Popen para que stop() lo corte."""
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, close_fds=True,
        )
        with self._proc_lock:
            if self._stop_event.is_set():
                proc.kill()
            self._proc = proc
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        finally:
            with self._proc_lock:
                if self._proc is proc:
                    self._proc = None
        return out.decode(errors="replace")

    def _give_up(self) -> None:
        self.failed = True
        callback = self.on_failure
        if callback is not None:
            try:
                callback()
            except Exception:  # noqa: BLE001
                log.exception("nettop: fallo activando el fallback")

    def _loop(self, on_sample: Callable[[TrafficSample], None]) -> None:
        failures = 0  # snapshots fallidos SEGUIDOS
        cmd = self._build_command()
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                output = self._runner(cmd, self._SNAPSHOT_TIMEOUT)
                parsed = parse_nettop_block(output.splitlines())
                if not parsed:
                    raise ValueError("snapshot de nettop sin filas")
            except Exception as exc:  # noqa: BLE001
                if self._stop_event.is_set():
                    return
                failures += 1
                if failures >= self._MAX_FAILURES:
                    log.error("nettop: %d snapshots fallidos seguidos (%s); "
                              "abandono la captura nativa.", failures, exc)
                    self._give_up()
                    return
                delay = min(self._FAILURE_MAX_DELAY,
                            self._FAILURE_BASE_DELAY * 2 ** (failures - 1))
                log.warning("nettop: snapshot falló (%s); reintento %d/%d en %.0fs.",
                            exc, failures, self._MAX_FAILURES, delay)
                if self._stop_event.wait(delay):
                    return
                continue
            failures = 0
            try:
                # Nombre real por PID (T-025) antes de los deltas.
                resolved = {
                    pid: (self._resolve_name(pid, name), bin_, bout)
                    for pid, (name, bin_, bout) in parsed.items()
                }
                self._emit_deltas(resolved, on_sample)
            except Exception:  # noqa: BLE001
                log.exception("nettop: fallo procesando un snapshot; se descarta")
            remaining = self.interval - (time.monotonic() - started)
            if self._stop_event.wait(max(0.0, remaining)):
                return

    def _emit_deltas(
        self,
        current: dict[int, tuple[str, int, int]],
        on_sample: Callable[[TrafficSample], None],
    ) -> None:
        new_prev: dict[int, tuple[int, int, int]] = {}
        samples: list[TrafficSample] = []

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
                samples.append(
                    TrafficSample(
                        pid=pid, app_name=name, bytes_sent=sent, bytes_recv=recv
                    )
                )

        # PIDs que tenían base previa pero no aparecieron en este snapshot:
        # conservar su última lectura conocida (no perder la base de delta
        # por una ausencia transitoria) salvo que ya lleven demasiados
        # snapshots ausentes, en cuyo caso se asume que el proceso terminó.
        for pid, (bytes_in, bytes_out, missing) in self._prev.items():
            if pid in new_prev:
                continue
            missing += 1
            if missing <= self._MAX_MISSING_TICKS:
                new_prev[pid] = (bytes_in, bytes_out, missing)
            else:
                # proceso terminado de verdad: limpiar también la caché de
                # nombre para no servir un nombre viejo si el PID se recicla.
                self._name_cache.pop(pid, None)
            # si supera el límite, se purga (no se copia a new_prev) y un
            # futuro reaparición se trata como primer sample, no como reset.

        # La base se actualiza ANTES de emitir: si un on_sample falla, el
        # próximo snapshot no re-cuenta lo ya emitido.
        self._prev = new_prev
        for sample in samples:
            try:
                on_sample(sample)
            except Exception:  # noqa: BLE001
                log.exception("nettop: on_sample falló; se descarta la muestra")

    def _resolve_name(self, pid: int, fallback: str) -> str:
        """Devuelve el nombre REAL del proceso por PID (T-025).

        `nettop` trunca el nombre a un ancho fijo (~15 chars); si el corte cae
        en medio de un carácter multibyte, los bytes parciales decodean a
        U+FFFD ("cajas" en la UI). `psutil.Process(pid).name()` da el nombre
        completo y bien codificado. Se cachea por PID; si psutil no puede
        resolver (proceso ya terminado / sin permisos), cae al nombre de
        nettop SIN cachear, para reintentar en el próximo snapshot.
        """
        cached = self._name_cache.get(pid)
        if cached is not None:
            return cached
        try:
            import psutil
            real = psutil.Process(pid).name()
        except Exception:  # noqa: BLE001 — best-effort, nunca romper la captura
            return fallback
        name = real or fallback
        self._name_cache[pid] = name
        return name

    def stop(self) -> None:
        self._stop_event.set()
        with self._proc_lock:
            proc, self._proc = self._proc, None
        if proc is not None:  # snapshot en vuelo: cortarlo ya
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        thread, self._thread = self._thread, None
        # on_failure -> FallbackCaptureService -> stop() corre en el propio hilo.
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self._SNAPSHOT_TIMEOUT + 2)
