from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.request import Request
from urllib.request import urlopen as _stdlib_urlopen

_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    url: str
    release_name: str


def check_for_update(
    *,
    current_version: str,
    repo: str,
    fetcher=_stdlib_urlopen,
    timeout: float = 10.0,
) -> UpdateInfo | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "kookie-update-checker",
        },
    )
    with fetcher(request, timeout=timeout) as response:  # type: ignore[call-arg]
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict):
        return None
    if bool(payload.get("prerelease", False)):
        return None

    latest_tag = str(payload.get("tag_name", "")).strip()
    latest_version = _normalize_version(latest_tag)
    current_normalized = _normalize_version(current_version)
    if latest_version is None or current_normalized is None:
        return None
    if latest_version <= current_normalized:
        return None

    return UpdateInfo(
        version=_version_string(latest_version),
        url=str(payload.get("html_url", "")).strip(),
        release_name=str(payload.get("name", "")).strip() or latest_tag,
    )


def _normalize_version(raw: str) -> tuple[int, int, int] | None:
    match = _VERSION_PATTERN.match(raw.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _version_string(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"
