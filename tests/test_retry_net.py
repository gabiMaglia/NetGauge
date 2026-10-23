"""retry_net (build/retry_net.sh): reintenta solo ante errores de red."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "build" / "retry_net.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or BASH is None, reason="requiere bash POSIX"
)

CLOUDKIT = (
    'error is Error Domain=NSURLErrorDomain Code=-1005 "The network connection '
    'was lost." NSErrorFailingURLStringKey=https://api.apple-cloudkit.com/x\n'
    "The validate action failed! Error 68."
)


def _run(tmp_path: Path, fail_times: int, message: str, rc: int = 68):
    fake = tmp_path / "bin"
    fake.mkdir()
    counter = tmp_path / "count"
    counter.write_text("0")
    xcrun = fake / "xcrun"
    xcrun.write_text(
        "#!/bin/bash\n"
        f'n=$(($(cat "{counter}") + 1)); echo $n > "{counter}"\n'
        f'if [ "$n" -le {fail_times} ]; then cat <<\'MSG\'\n{message}\nMSG\n'
        f"exit {rc}; fi\necho ok-$n\n"
    )
    xcrun.chmod(0o755)
    script = f'source "{LIB}"; retry_net test xcrun stapler validate x'
    env = {"PATH": f"{fake}:/usr/bin:/bin", "NETGAUGE_RETRY_DELAYS": "0 0 0"}
    p = subprocess.run(
        [BASH, "-c", "set -euo pipefail; " + script],
        capture_output=True, text=True, env=env, timeout=30,
    )
    return p, int(counter.read_text())


def test_retries_network_errors_then_succeeds(tmp_path):
    p, calls = _run(tmp_path, 2, CLOUDKIT)
    assert p.returncode == 0, p.stderr
    assert calls == 3
    assert "OK en el intento 3" in p.stdout


def test_gives_up_after_all_attempts_with_network_error(tmp_path):
    p, calls = _run(tmp_path, 99, CLOUDKIT)
    assert p.returncode == 68
    assert calls == 4
    assert "persistente" in p.stderr


def test_does_not_retry_non_network_error(tmp_path):
    p, calls = _run(tmp_path, 99, "stapler: The ticket is invalid.", rc=65)
    assert p.returncode == 65
    assert calls == 1
    assert "NO de red" in p.stderr
    assert "invalid" in p.stdout
