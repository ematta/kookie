from __future__ import annotations

from pathlib import Path

from kookie.app import create_app
from kookie.config import AppConfig
from kookie.update_checker import UpdateInfo


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


def test_runtime_check_for_updates_noop_when_disabled(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path, update_check_enabled=False),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    assert runtime.check_for_updates(checker=lambda **_kwargs: None) is None


def test_runtime_check_for_updates_updates_status_when_newer(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path, update_check_enabled=True),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    info = runtime.check_for_updates(
        checker=lambda **_kwargs: UpdateInfo(
            version="0.2.0",
            url="https://github.com/ematta/kookie/releases/tag/v0.2.0",
            release_name="0.2.0",
        )
    )

    assert info is not None
    assert "Update available" in runtime.status_message
    assert "0.2.0" in runtime.status_message


def test_runtime_check_for_updates_handles_checker_failure(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path, update_check_enabled=True),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    def failing_checker(**_kwargs):
        raise RuntimeError("network down")

    assert runtime.check_for_updates(checker=failing_checker) is None
    assert runtime.status_message.startswith("Unable to check for updates:")
    assert runtime.metrics.snapshot().get("update_check_failed", 0) == 1
