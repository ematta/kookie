from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .assets import AssetDownloadError, AssetSpec, download_asset
from .config import AppConfig, load_config


@dataclass(slots=True)
class PreloadResult:
    voices_path: Path | None
    downloaded: bool
    message: str


def preload_voice(
    config: AppConfig | None = None,
    *,
    downloader: Callable[..., Path] | None = None,
) -> PreloadResult:
    cfg = config or load_config()
    asset_dir = cfg.asset_dir.expanduser()
    asset_dir.mkdir(parents=True, exist_ok=True)

    voice_path = asset_dir / cfg.voices_filename
    if voice_path.exists():
        return PreloadResult(
            voices_path=voice_path,
            downloaded=False,
            message=f"Voice already available at {voice_path}",
        )

    spec = AssetSpec(
        name="voices",
        filename=cfg.voices_filename,
        url=cfg.voices_url,
        sha256=cfg.voices_sha256,
    )

    selected_downloader = downloader if downloader is not None else download_asset
    try:
        downloaded_path = selected_downloader(spec, target_dir=asset_dir, timeout=cfg.download_timeout)
    except AssetDownloadError as exc:
        return PreloadResult(
            voices_path=None,
            downloaded=False,
            message=f"Voice preload failed: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return PreloadResult(
            voices_path=None,
            downloaded=False,
            message=f"Voice preload failed: {exc}",
        )

    return PreloadResult(
        voices_path=downloaded_path,
        downloaded=True,
        message=f"Downloaded voice to {downloaded_path}",
    )


def main() -> int:
    result = preload_voice()
    print(result.message)
    return 0 if result.voices_path is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
