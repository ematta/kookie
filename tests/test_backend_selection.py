from dataclasses import dataclass

import pytest

from kookie.assets import ResolvedAssets
from kookie.backends import BackendSelectionError, select_backend
from kookie.backends.mock import MockSpeechBackend
from kookie.config import AppConfig


@dataclass
class _FakeRealBackend:
    model_path: str
    voices_path: str


def test_select_backend_auto_falls_back_to_mock_when_assets_missing() -> None:
    cfg = AppConfig(backend_mode="auto")
    assets = ResolvedAssets(model_path=None, voices_path=None, ready=False, errors=["missing"])

    backend = select_backend(
        cfg,
        assets,
        kokoro_factory=lambda model_path, voices_path: _FakeRealBackend(str(model_path), str(voices_path)),
        dependency_probe=lambda: True,
    )

    assert isinstance(backend, MockSpeechBackend)


def test_select_backend_auto_prefers_real_when_ready() -> None:
    cfg = AppConfig(backend_mode="auto")
    assets = ResolvedAssets(
        model_path="/tmp/model.onnx",
        voices_path="/tmp/voices.bin",
        ready=True,
        errors=[],
    )

    backend = select_backend(
        cfg,
        assets,
        kokoro_factory=lambda model_path, voices_path: _FakeRealBackend(str(model_path), str(voices_path)),
        dependency_probe=lambda: True,
    )

    assert isinstance(backend, _FakeRealBackend)


def test_select_backend_real_mode_raises_when_dependencies_unavailable() -> None:
    cfg = AppConfig(backend_mode="real")
    assets = ResolvedAssets(
        model_path="/tmp/model.onnx",
        voices_path="/tmp/voices.bin",
        ready=True,
        errors=[],
    )

    with pytest.raises(BackendSelectionError):
        select_backend(
            cfg,
            assets,
            kokoro_factory=lambda model_path, voices_path: _FakeRealBackend(str(model_path), str(voices_path)),
            dependency_probe=lambda: False,
        )
