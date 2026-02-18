from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess

import pytest

from kookie.ui import (
    _default_dialog_dir,
    _native_file_dialog,
    _prompt_mp3_output_path,
    _prompt_pdf_path,
)


class _RootStub:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def withdraw(self) -> None:
        self.calls.append(("withdraw",))

    def attributes(self, *args: object) -> None:
        self.calls.append(("attributes", *args))

    def destroy(self) -> None:
        self.calls.append(("destroy",))


def test_default_dialog_dir_prefers_downloads_when_present(tmp_path: Path) -> None:
    home = tmp_path / "home"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)

    assert _default_dialog_dir(home_dir=home) == downloads


def test_default_dialog_dir_falls_back_to_home_when_downloads_missing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    assert _default_dialog_dir(home_dir=home) == home


def test_native_file_dialog_open_uses_open_dialog_and_cleans_up_root() -> None:
    root = _RootStub()
    capture: dict[str, object] = {}

    def _open_dialog(**kwargs: object) -> str:
        capture.update(kwargs)
        return "/tmp/notes.pdf"

    result = _native_file_dialog(
        mode="open",
        title="Load PDF",
        initial_dir=Path("/tmp"),
        filetypes=(("PDF files", "*.pdf"),),
        platform_name="linux",
        tk_factory=lambda: root,
        askopenfilename=_open_dialog,
        asksaveasfilename=lambda **_: pytest.fail("save dialog should not be used for open mode"),
    )

    assert result == Path("/tmp/notes.pdf")
    assert capture["title"] == "Load PDF"
    assert capture["initialdir"] == "/tmp"
    assert capture["filetypes"] == (("PDF files", "*.pdf"),)
    assert capture["parent"] is root
    assert root.calls[0] == ("withdraw",)
    assert ("attributes", "-topmost", True) in root.calls
    assert root.calls[-1] == ("destroy",)


def test_native_file_dialog_save_uses_save_dialog_and_supports_cancel() -> None:
    root = _RootStub()
    capture: dict[str, object] = {}

    def _save_dialog(**kwargs: object) -> str:
        capture.update(kwargs)
        return ""

    result = _native_file_dialog(
        mode="save",
        title="Save MP3",
        initial_dir=Path("/tmp"),
        filetypes=(("MP3 files", "*.mp3"),),
        initial_file="kookie-20260218-100000.mp3",
        default_extension=".mp3",
        platform_name="linux",
        tk_factory=lambda: root,
        askopenfilename=lambda **_: pytest.fail("open dialog should not be used for save mode"),
        asksaveasfilename=_save_dialog,
    )

    assert result is None
    assert capture["title"] == "Save MP3"
    assert capture["initialdir"] == "/tmp"
    assert capture["initialfile"] == "kookie-20260218-100000.mp3"
    assert capture["defaultextension"] == ".mp3"
    assert capture["filetypes"] == (("MP3 files", "*.mp3"),)
    assert capture["parent"] is root
    assert root.calls[0] == ("withdraw",)
    assert root.calls[-1] == ("destroy",)


def test_native_file_dialog_on_macos_uses_osascript_runner() -> None:
    capture: dict[str, object] = {}

    def _runner(*args: object, **kwargs: object):
        capture["args"] = args
        capture["kwargs"] = kwargs
        return subprocess.CompletedProcess(args=["osascript"], returncode=0, stdout="/tmp/from-panel.pdf\n", stderr="")

    result = _native_file_dialog(
        mode="open",
        title="Load PDF",
        initial_dir=Path("/tmp"),
        filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
        platform_name="darwin",
        osascript_runner=_runner,
    )

    assert result == Path("/tmp/from-panel.pdf")
    assert capture["args"][0] == ["osascript", "-e", capture["args"][0][2]]
    assert "choose file" in capture["args"][0][2]
    assert "of type {\"pdf\"}" in capture["args"][0][2]
    assert capture["kwargs"]["check"] is True
    assert capture["kwargs"]["capture_output"] is True
    assert capture["kwargs"]["text"] is True


def test_native_file_dialog_on_macos_returns_none_for_cancel() -> None:
    def _runner(*_args: object, **_kwargs: object):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["osascript"],
            stderr="execution error: User canceled. (-128)",
        )

    result = _native_file_dialog(
        mode="save",
        title="Save MP3",
        initial_dir=Path("/tmp"),
        filetypes=(("MP3 files", "*.mp3"),),
        platform_name="darwin",
        osascript_runner=_runner,
    )

    assert result is None


def test_native_file_dialog_on_macos_raises_for_non_cancel_error() -> None:
    def _runner(*_args: object, **_kwargs: object):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["osascript"],
            stderr="execution error: dialog failed",
        )

    with pytest.raises(RuntimeError, match="Native file dialog failed"):
        _native_file_dialog(
            mode="save",
            title="Save MP3",
            initial_dir=Path("/tmp"),
            filetypes=(("MP3 files", "*.mp3"),),
            platform_name="darwin",
            osascript_runner=_runner,
        )


def test_prompt_pdf_path_requests_pdf_dialog() -> None:
    capture: dict[str, object] = {}

    def _dialog(**kwargs: object) -> Path | None:
        capture.update(kwargs)
        return Path("/tmp/file.pdf")

    result = _prompt_pdf_path(dialog=_dialog, home_dir=Path("/Users/tester"))

    assert result == Path("/tmp/file.pdf")
    assert capture["mode"] == "open"
    assert capture["title"] == "Load PDF"
    assert capture["initial_dir"] == Path("/Users/tester")


def test_prompt_mp3_output_path_sets_defaults_and_appends_extension() -> None:
    capture: dict[str, object] = {}

    def _dialog(**kwargs: object) -> Path | None:
        capture.update(kwargs)
        return Path("/tmp/export-audio")

    result = _prompt_mp3_output_path(
        dialog=_dialog,
        home_dir=Path("/Users/tester"),
        now=datetime(2026, 2, 18, 12, 30, 45),
    )

    assert result == Path("/tmp/export-audio.mp3")
    assert capture["mode"] == "save"
    assert capture["title"] == "Save MP3"
    assert capture["initial_dir"] == Path("/Users/tester")
    assert capture["initial_file"] == "kookie-20260218-123045.mp3"
    assert capture["default_extension"] == ".mp3"
