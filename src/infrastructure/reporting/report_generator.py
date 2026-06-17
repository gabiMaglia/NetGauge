"""Genera el informe de sesión (CSV) al cerrar la app."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ...domain.models import UsageRecord, human_bytes
from ...domain.ports import ReportGenerator


class CsvReportGenerator(ReportGenerator):
    def __init__(self, output_dir: str | Path | None = None) -> None:
        if output_dir is None:
            output_dir = Path.home() / "Desktop"
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self, records: Iterable[UsageRecord], destination_hint: str | None = None
    ) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = destination_hint or f"network_report_{stamp}.csv"
        path = self._dir / name

        records = list(records)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["Aplicación", "Subida", "Bajada", "Total", "Subida (B)", "Bajada (B)"]
            )
            for r in sorted(records, key=lambda x: -(x.bytes_sent + x.bytes_recv)):
                total = r.bytes_sent + r.bytes_recv
                writer.writerow(
                    [
                        r.app_name,
                        human_bytes(r.bytes_sent),
                        human_bytes(r.bytes_recv),
                        human_bytes(total),
                        r.bytes_sent,
                        r.bytes_recv,
                    ]
                )
        return str(path)
