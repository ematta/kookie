from __future__ import annotations

from pathlib import Path

import pytest

from kookie.app import create_app
from kookie.config import AppConfig


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


@pytest.mark.e2e
def test_runtime_smoke_e2e(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("Hello world. End to end.")
    assert runtime.play() is True
    runtime.wait_until_idle(timeout=2.0)
