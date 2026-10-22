# tests/test_report_rotation.py
from __future__ import annotations

import os

from src.infrastructure.reporting.rotation import rotate_reports


def _make(dir_, name, mtime):
    p = dir_ / name
    p.write_text("x")
    os.utime(p, (mtime, mtime))
    return p


def test_conserva_los_20_mas_nuevos(tmp_path):
    for i in range(25):
        _make(tmp_path, f"network_report_{i:02d}.csv", 1_000_000 + i)
    removed = rotate_reports(tmp_path, keep=20)
    assert len(removed) == 5
    left = sorted(p.name for p in tmp_path.iterdir())
    assert len(left) == 20
    assert "network_report_04.csv" not in left     # los 5 más viejos se fueron
    assert "network_report_05.csv" in left


def test_cuenta_todos_los_formatos_juntos(tmp_path):
    _make(tmp_path, "network_report_a.csv", 1)
    _make(tmp_path, "NetGauge_report_b.xlsx", 2)
    _make(tmp_path, "NetGauge_report_c.pdf", 3)
    rotate_reports(tmp_path, keep=2)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "NetGauge_report_b.xlsx", "NetGauge_report_c.pdf"]


def test_no_toca_archivos_ajenos(tmp_path):
    for i in range(3):
        _make(tmp_path, f"network_report_{i}.csv", i)
    otro = _make(tmp_path, "notas.txt", 0)
    rotate_reports(tmp_path, keep=1)
    assert otro.exists()


def test_directorio_inexistente_no_falla(tmp_path):
    assert rotate_reports(tmp_path / "nope") == []


def test_menos_que_el_limite_no_borra(tmp_path):
    _make(tmp_path, "network_report_1.csv", 1)
    assert rotate_reports(tmp_path, keep=20) == []
