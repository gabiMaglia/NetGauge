"""Rotación de informes: evita que `reports/` crezca sin límite."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_PATTERNS = ("*_report_*.csv", "*_report_*.xlsx", "*_report_*.pdf")


def rotate_reports(directory: str | Path, keep: int = 20) -> list[Path]:
    """Borra los informes más viejos y deja los `keep` más recientes (por mtime)."""
    d = Path(directory)
    if not d.is_dir():
        return []
    files: list[Path] = []
    for pattern in _PATTERNS:
        files.extend(p for p in d.glob(pattern) if p.is_file())
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    removed: list[Path] = []
    for p in files[max(keep, 0):]:
        try:
            p.unlink()
            removed.append(p)
        except OSError as exc:
            log.debug("No se pudo borrar el informe viejo %s: %s", p, exc)
    return removed
