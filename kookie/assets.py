from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.request import urlopen as _stdlib_urlopen

from .config import AppConfig


@dataclass(frozen=True, slots=True)
class AssetSpec:
    name: str
    filename: str
    url: str
    sha256: str | None = None


@dataclass(slots=True)
class ResolvedAssets:
    model_path: Path | str | None
    voices_path: Path | str | None
    ready: bool
    errors: list[str] = field(default_factory=list)


class AssetDownloadError(RuntimeError):
    """Raised when an asset download cannot be completed safely."""


def resolve_assets(
    config: AppConfig,
    ensure_download: bool = False,
    downloader: Callable[..., Path] | None = None,
) -> ResolvedAssets:
    target_dir = config.asset_dir.expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    specs = _specs_from_config(config)
    errors: list[str] = []

    model_path = _existing_path(target_dir / specs[0].filename)
    voices_path = _existing_path(target_dir / specs[1].filename)

    if ensure_download:
        if model_path is None:
            model_path = _attempt_download(specs[0], target_dir, config.download_timeout, downloader, errors)
        if voices_path is None:
            voices_path = _attempt_download(specs[1], target_dir, config.download_timeout, downloader, errors)

    ready = model_path is not None and voices_path is not None
    return ResolvedAssets(model_path=model_path, voices_path=voices_path, ready=ready, errors=errors)


def download_asset(
    spec: AssetSpec,
    target_dir: Path,
    timeout: float,
    urlopen: Callable[..., object] = _stdlib_urlopen,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / spec.filename
    temp_path = target_dir / f"{spec.filename}.tmp"

    _remove_if_exists(temp_path)

    try:
        with urlopen(spec.url, timeout=timeout) as response:  # type: ignore[call-arg]
            payload = response.read()

        digest = hashlib.sha256(payload).hexdigest()
        if spec.sha256 and digest.lower() != spec.sha256.lower():
            raise AssetDownloadError(
                f"checksum mismatch for {spec.name}: expected {spec.sha256}, got {digest}"
            )

        temp_path.write_bytes(payload)
        os.replace(temp_path, final_path)
        return final_path
    except AssetDownloadError:
        _remove_if_exists(temp_path)
        raise
    except Exception as exc:  # pragma: no cover - depends on system/network state
        _remove_if_exists(temp_path)
        raise AssetDownloadError(f"failed to download {spec.name}: {exc}") from exc


def _specs_from_config(config: AppConfig) -> tuple[AssetSpec, AssetSpec]:
    return (
        AssetSpec(
            name="model",
            filename=config.model_filename,
            url=config.model_url,
            sha256=config.model_sha256,
        ),
        AssetSpec(
            name="voices",
            filename=config.voices_filename,
            url=config.voices_url,
            sha256=config.voices_sha256,
        ),
    )


def _attempt_download(
    spec: AssetSpec,
    target_dir: Path,
    timeout: float,
    downloader: Callable[..., Path] | None,
    errors: list[str],
) -> Path | None:
    selected_downloader = downloader if downloader is not None else download_asset
    try:
        return selected_downloader(spec, target_dir=target_dir, timeout=timeout)
    except AssetDownloadError as exc:
        errors.append(f"{spec.name} download failed: {exc}")
        return None


def _existing_path(path: Path) -> Path | None:
    return path if path.exists() else None


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
