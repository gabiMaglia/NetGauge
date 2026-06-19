"""Tests del parseo de `nettop` (backend de captura macOS) y de la fábrica.

No requieren macOS ni el binario `nettop` instalado: testean funciones puras
de parseo y la lógica de deltas/fallback con fakes.
"""
from __future__ import annotations

import os
import threading

from src.infrastructure.capture.nettop_capture import (
    NettopCaptureService,
    iter_lines_from_fd,
    parse_nettop_block,
    split_into_blocks,
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


def test_split_into_blocks_groups_by_header_with_carriage_return():
    stream = [
        ",bytes_in,bytes_out,\r\n",
        "A.1,10,20,\r\n",
        ",bytes_in,bytes_out,\r\n",
        "A.1,15,25,\r\n",
        "B.2,5,5,\r\n",
    ]
    blocks = list(split_into_blocks(stream))
    assert len(blocks) == 2
    assert parse_nettop_block(blocks[0]) == {1: ("A", 10, 20)}
    assert parse_nettop_block(blocks[1]) == {1: ("A", 15, 25), 2: ("B", 5, 5)}


def test_iter_lines_from_fd_yields_decoded_lines_until_eof():
    """Simula el extremo maestro de un PTY: escribe en el extremo write de un
    pipe os.pipe() (mismo contrato de fd crudo que un PTY) con "\\r\\n" y
    confirma que iter_lines_from_fd reconstruye las líneas completas."""
    read_fd, write_fd = os.pipe()
    stop_event = threading.Event()

    def writer():
        os.write(write_fd, b",bytes_in,bytes_out,\r\n")
        os.write(write_fd, b"App.1,10,20,\r\n")
        os.close(write_fd)

    t = threading.Thread(target=writer)
    t.start()
    lines = list(iter_lines_from_fd(read_fd, stop_event))
    t.join()
    os.close(read_fd)

    assert lines == [",bytes_in,bytes_out,\r", "App.1,10,20,\r"]


def test_iter_lines_from_fd_stops_when_stop_event_set():
    read_fd, write_fd = os.pipe()
    stop_event = threading.Event()
    stop_event.set()  # ya detenido antes de empezar a leer

    lines = list(iter_lines_from_fd(read_fd, stop_event))

    os.close(read_fd)
    os.close(write_fd)
    assert lines == []


def test_split_into_blocks_groups_by_header():
    stream = [
        ",bytes_in,bytes_out,\n",
        "A.1,10,20,\n",
        ",bytes_in,bytes_out,\n",
        "A.1,15,25,\n",
        "B.2,5,5,\n",
    ]
    blocks = list(split_into_blocks(stream))
    assert len(blocks) == 2
    assert blocks[0] == [",bytes_in,bytes_out,\n", "A.1,10,20,\n"]
    assert blocks[1] == [
        ",bytes_in,bytes_out,\n", "A.1,15,25,\n", "B.2,5,5,\n",
    ]


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


def test_emit_deltas_ignores_counter_reset_without_negative_bytes():
    svc = NettopCaptureService()
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

    # Reaparece (probablemente otro proceso reciclando el PID): se trata
    # como primer sample, sin emitir un delta gigante espurio.
    svc._emit_deltas({1: ("OtroProceso", 5000, 5000)}, samples.append)
    assert len(samples) == 1  # no se agregó un nuevo evento por el "reset"


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


def test_build_command_raises_when_nettop_missing(monkeypatch):
    from src.infrastructure.capture.nettop_capture import CaptureUnavailable

    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.shutil.which", lambda name: None
    )
    svc = NettopCaptureService()
    try:
        svc._build_command()
        assert False, "debía lanzar CaptureUnavailable"
    except CaptureUnavailable:
        pass


def test_start_raises_capture_unavailable_when_popen_fails(monkeypatch):
    """Si Popen falla, start() degrada a CaptureUnavailable (no a un OSError
    crudo por doble-close del slave_fd) para que la factory caiga a psutil.
    Regresión T-011 (defecto QA: except + finally cerraban slave_fd dos veces)."""
    from src.infrastructure.capture.nettop_capture import CaptureUnavailable

    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.shutil.which",
        lambda name: "/usr/bin/nettop",
    )

    def _boom(*args, **kwargs):
        raise OSError("no se pudo ejecutar nettop")

    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.subprocess.Popen", _boom
    )
    svc = NettopCaptureService()
    try:
        svc.start(lambda sample: None)
        assert False, "debía lanzar CaptureUnavailable"
    except CaptureUnavailable:
        pass
    except OSError as exc:  # el doble-close se manifestaba acá (Bad file descriptor)
        assert False, f"esperaba CaptureUnavailable, no OSError crudo: {exc}"


def test_factory_returns_nettop_backend_on_macos(monkeypatch):
    import src.infrastructure.capture.factory as factory_mod

    monkeypatch.setattr(factory_mod.sys, "platform", "darwin")
    monkeypatch.setattr(
        "src.infrastructure.capture.nettop_capture.NettopCaptureService.is_available",
        staticmethod(lambda: True),
    )
    service, per_process = factory_mod.create_capture_service()
    from src.infrastructure.capture.nettop_capture import NettopCaptureService

    assert isinstance(service, NettopCaptureService)
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
