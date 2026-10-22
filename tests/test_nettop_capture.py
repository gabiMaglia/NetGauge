"""Tests del parseo de `nettop` (backend de captura macOS) y de la fábrica.

No requieren macOS ni el binario `nettop` instalado: testean funciones puras
de parseo y la lógica de deltas/fallback con fakes.
"""
from __future__ import annotations

import os
import threading

import pytest

from src.infrastructure.capture.nettop_capture import (
    NettopCaptureService,
    _is_own_nettop_cmdline,
    parse_nettop_block,
)


def test_parse_nettop_block_basic():
    lines = [
        ",bytes_in,bytes_out,",
        "Spotify.893,1349395,40520,",
        "Google Chrome H.811,4485341,355531,",
    ]
    result = parse_nettop_block(lines)
    assert result[893] == ("Spotify", 1349395, 40520)
    assert result[811] == ("Google Chrome H", 4485341, 355531)


def test_parse_nettop_block_ignores_malformed_lines():
    lines = [
        ",bytes_in,bytes_out,",
        "no-dot-no-pid,1,2,",
        "Name.notapid,1,2,",
        "short,1",
        "",
        "  ",
        "Valid.42,10,20,",
    ]
    result = parse_nettop_block(lines)
    assert list(result.keys()) == [42]
    assert result[42] == ("Valid", 10, 20)


def test_parse_nettop_block_strips_carriage_return():
    """T-011: bajo PTY, nettop emite líneas terminadas en "\\r\\n" (traducción
    de terminal). El parseo debe tolerar el "\\r" igual que hace con espacios."""
    lines = [
        ",bytes_in,bytes_out,\r",
        "Spotify.893,1349395,40520,\r",
        "Google Chrome H.811,4485341,355531,\r",
    ]
    result = parse_nettop_block(lines)
    assert result[893] == ("Spotify", 1349395, 40520)
    assert result[811] == ("Google Chrome H", 4485341, 355531)











def test_emit_deltas_skips_first_sample_then_emits_delta():
    svc = NettopCaptureService()
    samples = []

    # Primer sample: no hay base previa, no debe emitir nada.
    svc._emit_deltas({1: ("App", 100, 50)}, samples.append)
    assert samples == []

    # Segundo sample: emite el delta acumulado -> instantáneo.
    svc._emit_deltas({1: ("App", 150, 80)}, samples.append)
    assert len(samples) == 1
    sample = samples[0]
    assert sample.pid == 1
    assert sample.app_name == "App"
    assert sample.bytes_recv == 50
    assert sample.bytes_sent == 30


def test_new_pid_after_baseline_counts_full_counter_but_baseline_pids_do_not():
    svc = NettopCaptureService()
    samples = []
    # Snapshot de base: solo fija bases, nada se cuenta.
    svc._emit_deltas({1: ("Old", 9000, 9000)}, samples.append)
    assert samples == []
    # PID 2 aparece después de la base: su contador completo es tráfico nuevo.
    svc._emit_deltas({1: ("Old", 9000, 9000), 2: ("New", 700, 30)}, samples.append)
    assert [(s.pid, s.bytes_recv, s.bytes_sent) for s in samples] == [(2, 700, 30)]
    # Y luego sigue con deltas normales (sin recontar).
    svc._emit_deltas({1: ("Old", 9000, 9000), 2: ("New", 900, 30)}, samples.append)
    assert [(s.pid, s.bytes_recv) for s in samples] == [(2, 700), (2, 200)]


def test_emit_deltas_ignores_counter_reset_without_negative_bytes():
    svc = NettopCaptureService()
    svc._has_baseline = True
    svc._prev = {1: (1000, 1000, 0)}
    samples = []
    # El proceso se reinició: el contador bajó. No debe reportar bytes negativos
    # ni inventar un pico; se descarta el delta inválido sin emitir evento.
    svc._emit_deltas({1: ("App", 10, 10)}, samples.append)
    assert samples == []
    # La siguiente lectura ya usa el valor bajo como nueva base (sin pico falso).
    svc._emit_deltas({1: ("App", 40, 30)}, samples.append)
    assert len(samples) == 1
    assert samples[0].bytes_recv == 30
    assert samples[0].bytes_sent == 20


def test_emit_deltas_skips_pids_with_no_traffic_change():
    svc = NettopCaptureService()
    svc._has_baseline = True
    svc._prev = {1: (100, 100, 0)}
    samples = []
    svc._emit_deltas({1: ("App", 100, 100)}, samples.append)
    assert samples == []


def test_emit_deltas_survives_transient_pid_absence_without_losing_traffic():
    """Caso real T-010: nettop omite un PID en un bloque puntual aunque el
    proceso siga transmitiendo. Antes esto perdía la base de delta y el
    tráfico real acumulado durante la ausencia se descartaba (aparecía como
    0 en vez de como consumo continuo)."""
    svc = NettopCaptureService()
    samples = []

    svc._emit_deltas({1: ("App", 100, 50)}, samples.append)  # primer sample
    assert samples == []

    svc._emit_deltas({1: ("App", 200, 50)}, samples.append)  # delta = 100
    assert len(samples) == 1 and samples[0].bytes_recv == 100

    # El PID no aparece en este bloque (ausencia transitoria), pero sigue
    # transmitiendo en la realidad. No debe perderse la base de referencia.
    svc._emit_deltas({}, samples.append)
    assert len(samples) == 1  # sin nuevo evento, pero sin pérdida de base
    assert 1 in svc._prev

    # Reaparece con el contador acumulado avanzado durante la ausencia:
    # debe emitir el delta completo (300), no tratarlo como primer sample.
    svc._emit_deltas({1: ("App", 500, 50)}, samples.append)
    assert len(samples) == 2
    assert samples[1].bytes_recv == 300
    assert samples[1].bytes_sent == 0


def test_emit_deltas_purges_pid_after_too_many_missing_ticks():
    """Si el PID falta más de `_MAX_MISSING_TICKS` bloques seguidos, se asume
    que el proceso terminó: se purga la base para no calcular un delta
    gigante (pico falso) si el PID se reciclara para otro proceso distinto."""
    svc = NettopCaptureService()
    samples = []

    svc._emit_deltas({1: ("App", 100, 50)}, samples.append)
    svc._emit_deltas({1: ("App", 200, 50)}, samples.append)
    assert len(samples) == 1

    for _ in range(svc._MAX_MISSING_TICKS + 1):
        svc._emit_deltas({}, samples.append)
    assert 1 not in svc._prev  # purgado tras exceder el límite de ausencias

    # Reaparece (otro proceso reciclando el PID): en one-shot su contador solo
    # refleja flows vivos, así que cuenta completo como un PID nuevo.
    svc._emit_deltas({1: ("OtroProceso", 5000, 5000)}, samples.append)
    assert len(samples) == 2 and samples[1].bytes_recv == 5000


def test_is_available_reflects_shutil_which(monkeypatch):
    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.shutil.which",
        lambda name: "/usr/bin/nettop" if name == "nettop" else None,
    )
    assert NettopCaptureService.is_available() is True

    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.shutil.which", lambda name: None
    )
    assert NettopCaptureService.is_available() is False


def test_factory_returns_nettop_backend_on_macos(monkeypatch):
    import src.infrastructure.capture.factory as factory_mod

    monkeypatch.setattr(factory_mod.sys, "platform", "darwin")
    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.NettopCaptureService.is_available",
        staticmethod(lambda: True),
    )
    service, per_process = factory_mod.create_capture_service()
    from src.infrastructure.capture.fallback import FallbackCaptureService
    from src.infrastructure.capture.nettop_capture import NettopCaptureService

    assert isinstance(service, FallbackCaptureService)
    assert isinstance(service.primary, NettopCaptureService)
    assert per_process is True


def test_factory_falls_back_to_psutil_on_macos_without_nettop(monkeypatch):
    import src.infrastructure.capture.factory as factory_mod
    from src.infrastructure.capture.psutil_fallback import PsutilCaptureService

    monkeypatch.setattr(factory_mod.sys, "platform", "darwin")
    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.NettopCaptureService.is_available",
        staticmethod(lambda: False),
    )
    service, per_process = factory_mod.create_capture_service()
    assert isinstance(service, PsutilCaptureService)
    assert per_process is False


# ---- T-023: reap de huérfanos -----------------------------------------

def test_is_own_nettop_cmdline_matches_exact_signature():
    assert _is_own_nettop_cmdline(
        ["/usr/bin/nettop", "-P", "-x", "-L", "0", "-s", "1",
         "-J", "bytes_in,bytes_out"]
    ) is True


def test_is_own_nettop_cmdline_rejects_other_nettop_invocations():
    # Otro proceso (no nuestro) corriendo nettop con flags distintos: no debe
    # matchear, para no matar un nettop ajeno al usuario.
    assert _is_own_nettop_cmdline(["/usr/bin/nettop", "-l", "1"]) is False
    assert _is_own_nettop_cmdline(["/usr/bin/nettop"]) is False
    assert _is_own_nettop_cmdline([]) is False


def test_is_own_nettop_cmdline_rejects_non_nettop_executable():
    assert _is_own_nettop_cmdline(
        ["/usr/bin/top", "-P", "-x", "-L", "0", "-s", "1",
         "-J", "bytes_in,bytes_out"]
    ) is False


def test_is_own_nettop_cmdline_requires_numeric_interval():
    assert _is_own_nettop_cmdline(
        ["/usr/bin/nettop", "-P", "-x", "-L", "0", "-s", "abc",
         "-J", "bytes_in,bytes_out"]
    ) is False


class _FakeProc:
    """Doble de psutil.Process suficiente para testear reap_orphans()."""

    def __init__(self, pid: int, cmdline: list[str], uid: int = 501) -> None:
        self.pid = pid
        self.info = {"pid": pid, "cmdline": cmdline,
                     "uids": _FakeUids(uid)}
        self.terminated = False
        self.killed = False
        self._alive = True

    def send_signal(self, signum) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self._alive = False

    def is_running(self) -> bool:
        return self._alive


class _FakeUids:
    def __init__(self, real: int) -> None:
        self.real = real


def test_reap_orphans_terminates_only_own_signature(monkeypatch):
    import src.infrastructure.capture.nettop_capture as mod

    own = _FakeProc(111, ["/usr/bin/nettop", "-P", "-x", "-L", "0", "-s", "1",
                          "-J", "bytes_in,bytes_out"])
    other_nettop = _FakeProc(222, ["/usr/bin/nettop", "-l", "1"])
    unrelated = _FakeProc(333, ["/usr/bin/top"])

    monkeypatch.setattr(os, "getuid", lambda: 501, raising=False)

    fake_psutil = type("FakePsutilModule", (), {})()
    fake_psutil.process_iter = lambda attrs: [own, other_nettop, unrelated]
    fake_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
    fake_psutil.AccessDenied = type("AccessDenied", (Exception,), {})

    monkeypatch.setitem(__import__("sys").modules, "psutil", fake_psutil)

    reaped = mod.NettopCaptureService.reap_orphans()

    assert reaped == 1
    assert own.terminated is True
    assert other_nettop.terminated is False
    assert unrelated.terminated is False


def test_reap_orphans_skips_other_users_processes(monkeypatch):
    import src.infrastructure.capture.nettop_capture as mod

    other_user = _FakeProc(
        444, ["/usr/bin/nettop", "-P", "-x", "-L", "0", "-s", "1",
              "-J", "bytes_in,bytes_out"], uid=999,
    )

    monkeypatch.setattr(os, "getuid", lambda: 501, raising=False)

    fake_psutil = type("FakePsutilModule", (), {})()
    fake_psutil.process_iter = lambda attrs: [other_user]
    fake_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
    fake_psutil.AccessDenied = type("AccessDenied", (Exception,), {})

    monkeypatch.setitem(__import__("sys").modules, "psutil", fake_psutil)

    reaped = mod.NettopCaptureService.reap_orphans()

    assert reaped == 0
    assert other_user.terminated is False


def test_reap_orphans_is_safe_without_psutil(monkeypatch):
    """Si psutil no se puede importar, reap_orphans() no debe lanzar (best-effort)."""
    import builtins
    import src.infrastructure.capture.nettop_capture as mod

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("no psutil")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert mod.NettopCaptureService.reap_orphans() == 0


def test_resolve_name_cae_al_fallback_sin_cachear(monkeypatch):
    """Si psutil no puede resolver (proceso terminado/sin permisos), devuelve el
    nombre de nettop SIN cachearlo, para reintentar en el próximo bloque."""
    import psutil

    def _boom(pid):
        raise psutil.NoSuchProcess(pid)

    monkeypatch.setattr(psutil, "Process", _boom)
    svc = NettopCaptureService()
    assert svc._resolve_name(999, "truncad") == "truncad"
    assert 999 not in svc._name_cache


# --- plan 03: resiliencia del loop (errores por bloque + relanzamiento) ---

_HDR = ",bytes_in,bytes_out,"


def _no_resolve(svc, monkeypatch):
    monkeypatch.setattr(svc, "_resolve_name", lambda pid, fallback: fallback)


class _Runner:
    """Runner inyectable: devuelve snapshots (str) o lanza si el item es Exception."""

    def __init__(self, items, on_empty=None):
        self.items = list(items)
        self.cmds: list[list[str]] = []
        self.on_empty = on_empty
        self.exhausted = threading.Event()

    def __call__(self, cmd, timeout):
        self.cmds.append(list(cmd))
        if not self.items:
            self.exhausted.set()
            if self.on_empty is not None:
                return self.on_empty
            raise RuntimeError("sin más snapshots")
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _svc(monkeypatch, runner, **kw):
    import src.infrastructure.capture.nettop_capture as mod

    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/nettop")
    monkeypatch.setattr(NettopCaptureService, "reap_orphans", staticmethod(lambda: 0))
    svc = NettopCaptureService(interval=kw.pop("interval", 0.01), runner=runner, **kw)
    monkeypatch.setattr(svc, "_resolve_name", lambda pid, fallback: fallback)
    svc._FAILURE_BASE_DELAY = 0.0
    return svc


# --- fix/nettop-cpu: polling de snapshots `-L 1` en vez de `-L 0` persistente ---
# `nettop -L 0` mantiene una suscripción persistente a NetworkStatistics (~100%
# de CPU constante). Un snapshot one-shot cuesta ~0.08 s de CPU.

def _snap(*rows: str) -> str:
    return "\n".join([_HDR, *rows, ""])


class _Runner:
    """Runner inyectable: devuelve snapshots (str) o lanza si el item es Exception."""

    def __init__(self, items, on_empty=None):
        self.items = list(items)
        self.cmds: list[list[str]] = []
        self.on_empty = on_empty
        self.exhausted = threading.Event()

    def __call__(self, cmd, timeout):
        self.cmds.append(list(cmd))
        if not self.items:
            self.exhausted.set()
            if self.on_empty is not None:
                return self.on_empty
            raise RuntimeError("sin más snapshots")
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _svc(monkeypatch, runner, **kw):
    import src.infrastructure.capture.nettop_capture as mod

    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/nettop")
    monkeypatch.setattr(NettopCaptureService, "reap_orphans", staticmethod(lambda: 0))
    svc = NettopCaptureService(interval=kw.pop("interval", 0.01), runner=runner, **kw)
    monkeypatch.setattr(svc, "_resolve_name", lambda pid, fallback: fallback)
    svc._FAILURE_BASE_DELAY = 0.0
    return svc


def test_snapshot_command_is_one_shot_and_not_persistent(monkeypatch):
    svc = _svc(monkeypatch, _Runner([]))
    cmd = svc._build_command()
    assert cmd[1:] == ["-P", "-x", "-L", "1", "-J", "bytes_in,bytes_out"]
    assert "0" not in cmd and "-s" not in cmd


def test_default_interval_is_2_seconds():
    assert NettopCaptureService().interval == 2.0


def test_service_polls_snapshots_with_configured_interval(monkeypatch):
    import time

    runner = _Runner([_snap("A.1,100,100,")] * 3, on_empty=_snap("A.1,100,100,"))
    svc = _svc(monkeypatch, runner, interval=0.05)
    t0 = time.monotonic()
    svc.start(lambda s: None)
    while len(runner.cmds) < 4 and time.monotonic() - t0 < 5:
        time.sleep(0.005)
    elapsed = time.monotonic() - t0
    svc.stop()
    assert len(runner.cmds) >= 4
    assert all(c[1:] == ["-P", "-x", "-L", "1", "-J", "bytes_in,bytes_out"]
               for c in runner.cmds)
    assert elapsed >= 3 * 0.05 * 0.9  # respeta el intervalo entre snapshots


def test_deltas_between_consecutive_snapshots(monkeypatch):
    runner = _Runner([_snap("A.1,100,10,"), _snap("A.1,300,40,"), _snap("A.1,350,40,")])
    svc = _svc(monkeypatch, runner)
    samples = []
    svc._MAX_FAILURES = 1
    svc._loop(samples.append)
    assert [(s.bytes_recv, s.bytes_sent) for s in samples] == [(200, 30), (50, 0)]


def test_transient_pid_absence_across_snapshots_does_not_duplicate(monkeypatch):
    runner = _Runner([_snap("A.1,100,0,"), _snap("B.2,5,5,"), _snap("A.1,400,0,")])
    svc = _svc(monkeypatch, runner)
    svc._MAX_FAILURES = 1
    samples = []
    svc._loop(samples.append)
    a = [s for s in samples if s.pid == 1]
    assert [s.bytes_recv for s in a] == [300]  # una vez, sin duplicar ni perder


def test_decreasing_counter_never_yields_negative_delta(monkeypatch):
    runner = _Runner([_snap("A.1,1000,1000,"), _snap("A.1,200,200,"), _snap("A.1,260,230,")])
    svc = _svc(monkeypatch, runner)
    svc._MAX_FAILURES = 1
    samples = []
    svc._loop(samples.append)
    assert all(s.bytes_recv >= 0 and s.bytes_sent >= 0 for s in samples)
    assert [(s.bytes_recv, s.bytes_sent) for s in samples] == [(60, 30)]


def test_gives_up_after_consecutive_failures_and_notifies(monkeypatch):
    runner = _Runner([_snap("A.1,100,100,"), RuntimeError("x"), RuntimeError("y"),
                      TimeoutError("z")])
    svc = _svc(monkeypatch, runner)
    svc._MAX_FAILURES = 3
    failed = []
    svc.on_failure = lambda: failed.append(True)
    svc._loop(lambda s: None)
    assert svc.failed is True and failed == [True]
    assert len(runner.cmds) == 4


def test_empty_output_counts_as_failure_and_success_resets_counter(monkeypatch):
    runner = _Runner([_snap("A.1,1,1,"), "", "", _snap("A.1,2,2,"), "", ""])
    svc = _svc(monkeypatch, runner)
    svc._MAX_FAILURES = 3
    samples = []
    svc._loop(samples.append)
    # 2 fallos + éxito (resetea) + 2 fallos + runner agotado (3º) => se rinde
    assert svc.failed is True
    assert [s.bytes_recv for s in samples] == [1]


def test_on_sample_error_does_not_double_count(monkeypatch):
    runner = _Runner([_snap("A.1,100,100,"), _snap("A.1,200,200,"), _snap("A.1,300,300,")])
    svc = _svc(monkeypatch, runner)
    svc._MAX_FAILURES = 1
    calls = []

    def on_sample(sample):
        calls.append(sample)
        if len(calls) == 1:
            raise RuntimeError("UI caída")

    svc._loop(on_sample)
    assert [c.bytes_recv for c in calls] == [100, 100]


def test_stop_cuts_loop_quickly_and_leaves_no_process(monkeypatch):
    import time

    runner = _Runner([], on_empty=_snap("A.1,1,1,"))
    svc = _svc(monkeypatch, runner, interval=30.0)  # sin stop() tardaría 30 s
    svc.start(lambda s: None)
    runner.exhausted.wait(2) or time.sleep(0.05)
    t0 = time.monotonic()
    svc.stop()
    assert time.monotonic() - t0 < 1.0
    assert svc._thread is None and svc._proc is None


def test_build_command_raises_when_nettop_missing(monkeypatch):
    from src.infrastructure.capture.nettop_capture import CaptureUnavailable

    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.shutil.which", lambda name: None
    )
    with pytest.raises(CaptureUnavailable):
        NettopCaptureService().start(lambda s: None)


def test_start_calls_reap_orphans_before_first_snapshot(monkeypatch):
    calls: list[str] = []
    runner = _Runner([], on_empty=_snap("A.1,1,1,"))

    def run(cmd, timeout):
        calls.append("snapshot")
        return runner(cmd, timeout)

    svc = _svc(monkeypatch, run, interval=30.0)
    monkeypatch.setattr(NettopCaptureService, "reap_orphans",
                        staticmethod(lambda: calls.append("reap") or 0))
    svc.start(lambda s: None)
    runner.exhausted.wait(2)
    svc.stop()
    assert calls[:2] == ["reap", "snapshot"]
