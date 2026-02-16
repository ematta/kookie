from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MODEL_URL = "https://github.com/hexgrad/kokoro/releases/download/v0.19/kokoro-v0_19.onnx"
DEFAULT_VOICES_URL = "https://github.com/hexgrad/kokoro/releases/download/v0.19/voices.bin"


@dataclass(slots=True)
class AppConfig:
    backend_mode: str = "auto"
    asset_dir: Path = field(
        default_factory=lambda: Path.home() / "Library" / "Application Support" / "Kookie" / "assets"
    )
    model_filename: str = "kokoro-v0_19.onnx"
    voices_filename: str = "voices.bin"
    model_url: str = DEFAULT_MODEL_URL
    voices_url: str = DEFAULT_VOICES_URL
    model_sha256: str | None = None
    voices_sha256: str | None = None
    default_voice: str = "af_sarah"
    sample_rate: int = 24_000
    clipboard_poll_interval: float = 0.5
    download_timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "AppConfig":
        backend_mode = os.getenv("KOOKIE_BACKEND_MODE", "auto").strip().lower() or "auto"
        if backend_mode not in {"auto", "mock", "real"}:
            backend_mode = "auto"

        asset_dir_raw = os.getenv("KOOKIE_ASSET_DIR", "").strip()
        asset_dir = Path(asset_dir_raw).expanduser() if asset_dir_raw else None

        sample_rate = _safe_int(os.getenv("KOOKIE_SAMPLE_RATE"), default=24_000)
        poll_interval = _safe_float(os.getenv("KOOKIE_CLIPBOARD_POLL_INTERVAL"), default=0.5)
        download_timeout = _safe_float(os.getenv("KOOKIE_DOWNLOAD_TIMEOUT"), default=30.0)

        return cls(
            backend_mode=backend_mode,
            asset_dir=asset_dir if asset_dir is not None else cls().asset_dir,
            model_url=os.getenv("KOOKIE_MODEL_URL", DEFAULT_MODEL_URL).strip() or DEFAULT_MODEL_URL,
            voices_url=os.getenv("KOOKIE_VOICES_URL", DEFAULT_VOICES_URL).strip() or DEFAULT_VOICES_URL,
            model_sha256=_clean_optional(os.getenv("KOOKIE_MODEL_SHA256")),
            voices_sha256=_clean_optional(os.getenv("KOOKIE_VOICES_SHA256")),
            default_voice=os.getenv("KOOKIE_DEFAULT_VOICE", "af_sarah").strip() or "af_sarah",
            sample_rate=sample_rate,
            clipboard_poll_interval=poll_interval,
            download_timeout=download_timeout,
        )


def load_config() -> AppConfig:
    return AppConfig.from_env()


def _safe_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _safe_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
