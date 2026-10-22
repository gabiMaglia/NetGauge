# tests/test_github_updater.py
from src.infrastructure.update.github_updater import _parse, is_newer


def test_parse_rellena_a_tres_componentes():
    assert _parse("2.0") == (2, 0, 0)
    assert _parse("v2") == (2, 0, 0)
    assert _parse("v1.5.0") == (1, 5, 0)


def test_parse_vacio_o_basura():
    assert _parse("") == (0, 0, 0)
    assert _parse("sin numeros") == (0, 0, 0)


def test_parse_ignora_sufijos_y_cuartos_componentes():
    assert _parse("v2.0.1-beta.3") == (2, 0, 1)


def test_dos_cero_y_dos_cero_cero_son_iguales():
    assert is_newer("2.0", "2.0.0") is False
    assert is_newer("2.0.0", "2.0") is False


def test_is_newer_basico():
    assert is_newer("v2.0.2", "2.0.1") is True
    assert is_newer("2.0.1", "2.0.1") is False
    assert is_newer("2.1", "2.0.9") is True


def test_docstring_sin_caracteres_perdidos():
    from src.infrastructure.update import github_updater
    with open(github_updater.__file__, encoding="utf-8") as fh:
        assert "\u53c8" not in fh.read()
