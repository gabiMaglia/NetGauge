"""Utilidades de salida segura compartidas por los generadores de informes."""
from __future__ import annotations

# Un valor que empieza así lo interpretan Excel/LibreOffice como fórmula
# (CSV/formula injection). Los \t y \r también se usan para evadir el filtro.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def escape_formula(value):
    """Prefija con ' los textos que una planilla ejecutaría como fórmula."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def safe_filename(hint: str | None, default: str) -> str:
    """Solo el nombre de archivo del hint (sin rutas ni `..`); si queda vacío, `default`.

    Evita path traversal (`../../x`) y rutas absolutas. Soporta `/` y `\\`
    sin importar la plataforma, y neutraliza ':' (streams alternativos NTFS).
    """
    if not hint:
        return default
    name = hint.replace("\\", "/").rsplit("/", 1)[-1].strip().replace(":", "_")
    return default if name in ("", ".", "..") else name
