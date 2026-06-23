"""Chequeo de actualizaciones contra GitHub Releases (no bloqueante, fail-silent).

Compara la última release publicada con la versión actual. NO descarga ni
instala nada: solo informa y deja el link a la release para que el usuario decida.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request

log = logging.getLogger(__name__)

_API = "https://api.github.com/repos/{owner}/{repo}/releases/latest"


def _parse(version: str) -> tuple[int, ...]:
    """'v1.5.0' / '1.5.0' -> (1,5,0). Ignora sufijos no numéricos."""
    nums = re.findall(r"\d+", version or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return _parse(latest) > _parse(current)


def check_latest(owner: str, repo: str, current: str) -> tuple[str, str] | None:
    """(versión, url_html) si hay una release MÁS nueva; None si no/又 error."""
    req = urllib.request.Request(
        _API.format(owner=owner, repo=repo),
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "NetGauge-updater"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — sin red / sin releases / rate limit
        log.debug("Update check falló: %s", exc)
        return None
    tag = data.get("tag_name") or ""
    url = data.get("html_url") or ""
    if tag and is_newer(tag, current):
        return (tag.lstrip("vV"), url)
    return None
