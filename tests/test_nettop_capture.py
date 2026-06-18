"""Tests del parseo de `nettop` (backend de captura macOS) y de la fábrica.

No requieren macOS ni el binario `nettop` instalado: testean funciones puras
de parseo y la lógica de deltas/fallback con fakes.
"""
from __future__ import annotations

from src.infrastructure.capture.nettop_capture import (
    NettopCaptureService,
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


def test_emit_deltas_ignores_counter_reset_with_max_zero():
    svc = NettopCaptureService()
    svc._prev = {1: (1000, 1000)}
    samples = []
    # El proceso se reinició: el contador bajó. No debe reportar bytes negativos.
    svc._emit_deltas({1: ("App", 10, 10)}, samples.append)
    assert samples == []  # delta negativo clamped a 0 en ambos lados -> sin evento


def test_emit_deltas_skips_pids_with_no_traffic_change():
    svc = NettopCaptureService()
    svc._prev = {1: (100, 100)}
    samples = []
    svc._emit_deltas({1: ("App", 100, 100)}, samples.append)
    assert samples == []


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
