from pathlib import Path

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


def test_load_pdf_updates_text_and_status_on_success(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("before")
    target = tmp_path / "notes.pdf"
    capture: dict[str, Path] = {}

    def _loader(path: Path) -> str:
        capture["path"] = path
        return "Imported from PDF"

    loaded = runtime.load_pdf(target, loader=_loader)

    assert loaded == "Imported from PDF"
    assert capture["path"] == target
    assert runtime.text == "Imported from PDF"
    assert runtime.status_message == "Loaded PDF: notes.pdf"


def test_load_pdf_keeps_existing_text_on_failure(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("Existing text")
    original = runtime.text

    def _loader(_path: Path) -> str:
        raise RuntimeError("invalid or encrypted PDF")

    loaded = runtime.load_pdf(tmp_path / "broken.pdf", loader=_loader)

    assert loaded is None
    assert runtime.text == original
    assert runtime.status_message.startswith("Unable to load PDF:")
    assert "invalid or encrypted PDF" in runtime.status_message
