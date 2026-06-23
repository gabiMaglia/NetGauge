"""Informe de sesión en PDF vía reportlab."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from ...domain.models import UsageRecord, human_bytes
from ...domain.ports import ReportGenerator


class PdfReportGenerator(ReportGenerator):
    def __init__(self, output_dir: str | Path | None = None) -> None:
        self._dir = Path(output_dir or (Path.home() / "Desktop"))
        self._dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self, records: Iterable[UsageRecord], destination_hint: str | None = None
    ) -> str:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._dir / (destination_hint or f"NetLeak_report_{stamp}.pdf")

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=A4,
                                topMargin=18 * mm, bottomMargin=18 * mm)
        story = [
            Paragraph("NetLeak — Informe de consumo", styles["Title"]),
            Paragraph(datetime.now().strftime("Generado: %Y-%m-%d %H:%M"),
                      styles["Normal"]),
            Spacer(1, 8 * mm),
        ]

        rows = sorted(records, key=lambda x: -(x.bytes_sent + x.bytes_recv))
        data = [["Aplicación", "Subida", "Bajada", "Total"]]
        tot_s = tot_r = 0
        for r in rows:
            data.append([r.app_name, human_bytes(r.bytes_sent),
                         human_bytes(r.bytes_recv),
                         human_bytes(r.bytes_sent + r.bytes_recv)])
            tot_s += r.bytes_sent
            tot_r += r.bytes_recv
        data.append(["TOTAL", human_bytes(tot_s), human_bytes(tot_r),
                     human_bytes(tot_s + tot_r)])

        table = Table(data, colWidths=[80 * mm, 30 * mm, 30 * mm, 30 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2),
             [colors.white, colors.HexColor("#F1F5F9")]),
            ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.HexColor("#94A3B8")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        doc.build(story)
        return str(path)
