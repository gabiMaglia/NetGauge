"""Reglas de los workflows de GitHub Actions (parseo YAML, sin red)."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"
SHA_RE = re.compile(r"@[0-9a-f]{40}(\s|$)")
FIRST_PARTY = ("actions/", "github/")


def _load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text(encoding="utf-8"))


def _uses(wf: dict) -> list[str]:
    out = []
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            if "uses" in step:
                out.append(step["uses"])
    return out


def test_ci_has_no_retired_macos13_runner():
    text = (WF / "ci.yml").read_text(encoding="utf-8")
    assert "macos-13" not in text
    assert "macos-15-intel" in text and "macos-14" in text


def test_ci_permissions_read_only():
    assert _load("ci.yml")["permissions"] == {"contents": "read"}


def test_ci_has_linux_and_audit_jobs():
    jobs = _load("ci.yml")["jobs"]
    assert jobs["tests-linux"]["runs-on"] == "ubuntu-latest"
    assert jobs["tests-linux"]["env"]["QT_QPA_PLATFORM"] == "offscreen"
    assert "pip-audit" in (WF / "ci.yml").read_text(encoding="utf-8")


def test_third_party_actions_pinned_by_sha():
    for name in ("ci.yml", "release.yml"):
        for ref in _uses(_load(name)):
            if ref.startswith(FIRST_PARTY):
                continue
            assert SHA_RE.search(ref + "\n"), f"accion de terceros sin pin por SHA: {ref}"


def test_python_version_consistent_across_workflows():
    versions = set()
    for name in ("ci.yml", "release.yml"):
        for job in _load(name)["jobs"].values():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith("actions/setup-python"):
                    versions.add(step["with"]["python-version"])
    assert versions == {"3.12"}


def test_release_default_permissions_read_only_and_publish_writes():
    wf = _load("release.yml")
    assert wf["permissions"] == {"contents": "read"}
    assert wf["jobs"]["publish"]["permissions"] == {"contents": "write"}
    for job in ("test", "windows", "macos"):
        assert "permissions" not in wf["jobs"][job]


def test_release_builds_are_gated_by_tests():
    jobs = _load("release.yml")["jobs"]
    assert "test" in jobs
    for job in ("windows", "macos"):
        assert "test" in jobs[job]["needs"]
    assert set(jobs["publish"]["needs"]) == {"windows", "macos"}


def test_release_generates_checksums_and_attaches_them():
    text = (WF / "release.yml").read_text(encoding="utf-8")
    assert "sha256sum" in text and "SHA256SUMS.txt" in text


def test_release_no_longer_rewrites_version_py():
    assert "sed -i" not in (WF / "release.yml").read_text(encoding="utf-8")


def test_release_windows_generates_version_info_before_pyinstaller():
    steps = _load("release.yml")["jobs"]["windows"]["steps"]
    cmds = [s.get("run", "") for s in steps]
    gen = next(i for i, c in enumerate(cmds) if "gen_version_info.py" in c)
    pyi = next(i for i, c in enumerate(cmds) if "pyinstaller" in c)
    assert gen < pyi
