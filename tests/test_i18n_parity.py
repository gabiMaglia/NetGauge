"""Paridad de i18n: mismas claves y mismos placeholders en todos los idiomas."""
import re

import pytest

from src.presentation.qt.i18n import LANGUAGES, _STR

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _placeholders(text: str) -> set[str]:
    return set(_PLACEHOLDER.findall(text))


def test_all_languages_declared_have_strings():
    assert set(LANGUAGES) == set(_STR)


def test_all_languages_have_identical_key_sets():
    reference = set(_STR["es"])
    for lang, table in _STR.items():
        missing = reference - set(table)
        extra = set(table) - reference
        assert not missing and not extra, f"{lang}: faltan={sorted(missing)} sobran={sorted(extra)}"


@pytest.mark.parametrize("lang", ["en", "pt"])
def test_placeholders_match_reference_language(lang):
    for key, ref_text in _STR["es"].items():
        assert _placeholders(_STR[lang][key]) == _placeholders(ref_text), (lang, key)


@pytest.mark.parametrize("lang", sorted(_STR))
def test_geoip_hint_warns_about_unencrypted_http(lang):
    hint = _STR[lang]["dlg.settings.geoip_hint"]
    assert "HTTP" in hint
    assert "ip-api.com" in hint
