"""Higiene de dependencias: pyinstaller fuera de runtime y majors acotados."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _reqs(name: str) -> list[str]:
    out = []
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-r"):
            out.append(line)
    return out


def test_runtime_requirements_have_upper_bounds():
    for line in _reqs("requirements.txt"):
        spec = line.split(";", 1)[0]
        assert re.search(r">=[\d.]+,<\d+", spec), f"sin cota superior de major: {line!r}"


def test_pyinstaller_not_in_runtime_requirements():
    assert not any(l.lower().startswith("pyinstaller") for l in _reqs("requirements.txt"))


def test_pyinstaller_in_dev_requirements_bounded():
    dev = [l for l in _reqs("requirements-dev.txt") if l.lower().startswith("pyinstaller")]
    assert dev and re.search(r">=[\d.]+,<\d+", dev[0])


def test_dev_requirements_include_pyyaml_for_workflow_tests():
    assert any(l.lower().startswith("pyyaml") for l in _reqs("requirements-dev.txt"))


def test_dependabot_config_covers_pip_and_actions():
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "pip"' in text
    assert 'package-ecosystem: "github-actions"' in text
    assert text.count('interval: "weekly"') == 2
