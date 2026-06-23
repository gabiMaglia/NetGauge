"""Migración del historial desde la instalación previa trafficMe → NetLeak (T-017)."""
from __future__ import annotations

from main import _migrate_legacy_data


def _seed_legacy(base):
    base.mkdir(parents=True, exist_ok=True)
    (base / "usage.db").write_bytes(b"sqlite-data")
    (base / "settings.json").write_text('{"daily_limit_gb": 10}', encoding="utf-8")
    (base / "monitor.log").write_text("log viejo", encoding="utf-8")
    reports = base / "reports"
    reports.mkdir()
    (reports / "informe.csv").write_text("a,b\n1,2\n", encoding="utf-8")


def test_migra_historial_a_instalacion_limpia(tmp_path):
    legacy = tmp_path / "trafficMe"
    new = tmp_path / "NetLeak"
    _seed_legacy(legacy)

    assert _migrate_legacy_data(new, legacy) is True

    assert (new / "usage.db").read_bytes() == b"sqlite-data"
    assert (new / "settings.json").exists()
    assert (new / "monitor.log").exists()
    assert (new / "reports" / "informe.csv").exists()
    # Copia, no movimiento: la carpeta vieja queda intacta como respaldo.
    assert (legacy / "usage.db").exists()


def test_no_migra_si_la_instalacion_nueva_ya_tiene_datos(tmp_path):
    legacy = tmp_path / "trafficMe"
    new = tmp_path / "NetLeak"
    _seed_legacy(legacy)
    new.mkdir()
    (new / "usage.db").write_bytes(b"datos-nuevos")

    assert _migrate_legacy_data(new, legacy) is False
    # No pisa los datos nuevos.
    assert (new / "usage.db").read_bytes() == b"datos-nuevos"
    assert not (new / "settings.json").exists()


def test_no_migra_si_no_hay_historial_viejo(tmp_path):
    legacy = tmp_path / "trafficMe"
    new = tmp_path / "NetLeak"
    legacy.mkdir()  # existe pero sin usage.db

    assert _migrate_legacy_data(new, legacy) is False


def test_no_migra_sobre_si_mismo(tmp_path):
    same = tmp_path / "NetLeak"
    _seed_legacy(same)
    assert _migrate_legacy_data(same, same) is False
