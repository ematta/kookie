from __future__ import annotations

import json

from kookie.update_checker import UpdateInfo, check_for_update


class _Response:
    def __init__(self, payload: object):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_check_for_update_returns_latest_release() -> None:
    payload = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/ematta/kookie/releases/tag/v0.2.0",
        "name": "0.2.0",
        "prerelease": False,
    }

    info = check_for_update(
        current_version="0.1.0",
        repo="ematta/kookie",
        fetcher=lambda *_args, **_kwargs: _Response(payload),
    )

    assert isinstance(info, UpdateInfo)
    assert info.version == "0.2.0"
    assert "v0.2.0" in info.url


def test_check_for_update_returns_none_when_not_newer() -> None:
    payload = {
        "tag_name": "v0.1.0",
        "html_url": "https://github.com/ematta/kookie/releases/tag/v0.1.0",
        "name": "0.1.0",
        "prerelease": False,
    }

    info = check_for_update(
        current_version="0.1.0",
        repo="ematta/kookie",
        fetcher=lambda *_args, **_kwargs: _Response(payload),
    )

    assert info is None
