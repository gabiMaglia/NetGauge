# tests/test_report_safety.py
"""Informes: BOM, inyección de fórmulas, path traversal, sin default a Desktop."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

from src.domain.models import UsageRecord
from src.infrastructure.reporting.pdf_report_generator import PdfReportGenerator
from src.infrastructure.reporting.report_generator import CsvReportGenerator
from src.infrastructure.reporting.safe_output import escape_formula, safe_filename
from src.infrastructure.reporting.xlsx_report_generator import XlsxReportGenerator

EVIL = "=HYPERLINK(\"http://evil\",\"x\")"


def _recs():
    now = datetime.now()
    return [UsageRecord(EVIL, 9000, 9000, now),
            UsageRecord("Chrome", 100, 200, now)]


@pytest.mark.parametrize("raw", ["=1+1", "+1", "-1", "@SUM(A1)", "\tx", "\rx"])
def test_escape_formula_prefija_comilla(raw):
    assert escape_formula(raw) == "'" + raw


def test_escape_formula_no_toca_texto_normal_ni_numeros():
    assert escape_formula("Chrome") == "Chrome"
    assert escape_formula("") == ""
    assert escape_formula(123) == 123


@pytest.mark.parametrize("hint,expected", [
    ("../../evil.csv", "evil.csv"),
    ("..\\..\\evil.csv", "evil.csv"),
    ("C:\\Windows\\evil.csv", "evil.csv"),
    ("/etc/passwd", "passwd"),
    ("ok.csv", "ok.csv"),
    ("a.csv:stream", "a.csv_stream"),
    ("..", "DEF"), (".", "DEF"), ("", "DEF"), (None, "DEF"), ("dir/", "DEF"),
])
def test_safe_filename(hint, expected):
    assert safe_filename(hint, "DEF") == expected


def test_csv_tiene_bom_utf8(tmp_path):
    path = CsvReportGenerator(tmp_path).generate(_recs())
    with open(path, "rb") as fh:
        assert fh.read(3) == b"\xef\xbb\xbf"


def test_csv_escapa_formulas(tmp_path):
    path = CsvReportGenerator(tmp_path).generate(_recs())
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    assert rows[1][0] == "'" + EVIL      # la más pesada va primero
    assert rows[2][0] == "Chrome"


def test_csv_hint_con_traversal_queda_dentro_del_directorio(tmp_path):
    out = tmp_path / "reports"
    path = CsvReportGenerator(out).generate(_recs(), "../../evil.csv")
    assert Path(path).parent == out and Path(path).name == "evil.csv"
    assert not (tmp_path.parent / "evil.csv").exists()


def test_xlsx_escapa_formulas_y_las_deja_como_texto(tmp_path):
    from openpyxl import load_workbook
    path = XlsxReportGenerator(tmp_path).generate(_recs())
    cell = load_workbook(path)["Consumo"]["A2"]
    assert cell.value == "'" + EVIL
    assert cell.data_type == "s"


def test_xlsx_y_pdf_sanitizan_el_hint(tmp_path):
    out = tmp_path / "r"
    for gen, hint in ((XlsxReportGenerator(out), "../x.xlsx"),
                      (PdfReportGenerator(out), "..\\x.pdf")):
        assert Path(gen.generate(_recs(), hint)).parent == out


@pytest.mark.parametrize("cls", [CsvReportGenerator, XlsxReportGenerator,
                                 PdfReportGenerator])
def test_output_dir_es_obligatorio_sin_default_a_desktop(cls):
    with pytest.raises(TypeError):
        cls()
