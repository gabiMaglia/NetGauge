"""Genera el informe de sesión (CSV) al cerrar la app."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ...domain.models import UsageRecord, human_bytes
from ...domain.ports import ReportGenerator
from .safe_output import escape_formula, safe_filename


class CsvReportGenerator(ReportGenerator):
    def __init__(self, output_dir: str | Path) -> None:
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self, records: Iterable[UsageRecord], destination_hint: str | None = None
    ) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = safe_filename(destination_hint, f"network_report_{stamp}.csv")
        path = self._dir / name

        records = list(records)
        with path.open("w", newline="", encoding="utf-8-sig") as fh:  # BOM: Excel abre bien los acentos
            writer = csv.writer(fh)
            writer.writerow(
                ["Aplicación", "Subida", "Bajada", "Total", "Subida (B)", "Bajada (B)"]
            )
            for r in sorted(records, key=lambda x: -(x.bytes_sent + x.bytes_recv)):
                total = r.bytes_sent + r.bytes_recv
                writer.writerow(
                    [
                        escape_formula(r.app_name),
                        human_bytes(r.bytes_sent),
                        human_bytes(r.bytes_recv),
                        human_bytes(total),
                        r.bytes_sent,
                        r.bytes_recv,
                    ]
                )
        return str(path)
