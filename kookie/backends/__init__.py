from __future__ import annotations

from importlib.util import find_spec

from ..assets import ResolvedAssets
from ..config import AppConfig
from .mock import MockSpeechBackend


class BackendSelectionError(RuntimeError):
    """Raised when the configured backend cannot be started."""


def select_backend(
    config: AppConfig,
    assets: ResolvedAssets,
    *,
    kokoro_factory=None,
    dependency_probe=None,
):
    dependency_probe = dependency_probe or _kokoro_dependencies_available
    kokoro_factory = kokoro_factory or _default_kokoro_factory

    mode = config.backend_mode
    if mode == "mock":
        return MockSpeechBackend()

    if mode == "real":
        if not assets.ready or assets.model_path is None or assets.voices_path is None:
            raise BackendSelectionError("real backend requested but assets are unavailable")
        if not dependency_probe():
            raise BackendSelectionError("real backend requested but dependencies are unavailable")
        return kokoro_factory(assets.model_path, assets.voices_path)

    if mode == "auto":
        if assets.ready and assets.model_path is not None and assets.voices_path is not None and dependency_probe():
            try:
                return kokoro_factory(assets.model_path, assets.voices_path)
            except Exception:
                return MockSpeechBackend()
        return MockSpeechBackend()

    raise BackendSelectionError(f"unsupported backend mode: {mode}")


def _kokoro_dependencies_available() -> bool:
    return find_spec("kokoro_onnx") is not None and find_spec("onnxruntime") is not None


def _default_kokoro_factory(model_path, voices_path):
    from .kokoro import KokoroSpeechBackend

    return KokoroSpeechBackend(model_path=model_path, voices_path=voices_path)


__all__ = [
    "BackendSelectionError",
    "select_backend",
    "MockSpeechBackend",
]
