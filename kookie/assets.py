from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from urllib.request import urlopen as _stdlib_urlopen

from .config import AppConfig
from .retry import RetryPolicy, retry_call


@dataclass(frozen=True, slots=True)
class AssetSpec:
    name: str
    filename: str
    url: str
    sha256: str | None = None
    version: str | None = None


@dataclass(slots=True)
class AssetManifest:
    model_version: str | None = None
    voices_version: str | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class ResolvedAssets:
    model_path: Path | str | None
    voices_path: Path | str | None
    ready: bool
    errors: list[str] = field(default_factory=list)
    manifest_path: Path | None = None
    verified: bool = False
    downloaded: bool = False


class AssetDownloadError(RuntimeError):
    """Raised when an asset download cannot be completed safely."""


def resolve_assets(
    config: AppConfig,
    ensure_download: bool = False,
    downloader: Callable[..., Path] | None = None,
    progress_callback: Callable[[str, int, int | None], None] | None = None,
) -> ResolvedAssets:
    target_dir = config.asset_dir.expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    specs = _specs_from_config(config)
    manifest_path = target_dir / getattr(config, "asset_manifest_filename", "asset_manifest.json")
    manifest = _load_manifest(manifest_path)
    errors: list[str] = []

    model_path = _existing_path(target_dir / specs[0].filename)
    voices_path = _existing_path(target_dir / specs[1].filename)
    downloaded = False

    if model_path is not None and specs[0].sha256 and not _verify_existing_checksum(model_path, specs[0].sha256):
        errors.append(f"model verification failed: checksum mismatch for {model_path.name}")
        model_path = None
    if voices_path is not None and specs[1].sha256 and not _verify_existing_checksum(voices_path, specs[1].sha256):
        errors.append(f"voices verification failed: checksum mismatch for {voices_path.name}")
        voices_path = None

    require_checksums = bool(getattr(config, "require_asset_checksums", False))
    if require_checksums:
        for spec in specs:
            if not spec.sha256:
                errors.append(f"{spec.name} checksum is required but missing")

    if ensure_download:
        missing_specs: list[AssetSpec] = []
        if model_path is None:
            missing_specs.append(specs[0])
        if voices_path is None:
            missing_specs.append(specs[1])

        if missing_specs:
            with ThreadPoolExecutor(max_workers=max(1, len(missing_specs))) as executor:
                futures = {}
                for spec in missing_specs:
                    futures[executor.submit(
                        _attempt_download,
                        spec,
                        target_dir,
                        config.download_timeout,
                        downloader,
                        errors,
                        progress_callback,
                    )] = spec

                for future, spec in futures.items():
                    path = future.result()
                    if path is None:
                        continue
                    downloaded = True
                    if spec.name == "model":
                        model_path = path
                    elif spec.name == "voices":
                        voices_path = path

    auto_update = bool(getattr(config, "asset_auto_update", False))
    if ensure_download and auto_update and manifest is not None:
        if (
            (specs[0].version and manifest.model_version and specs[0].version != manifest.model_version)
            or (specs[1].version and manifest.voices_version and specs[1].version != manifest.voices_version)
        ):
            model_path = _attempt_download(specs[0], target_dir, config.download_timeout, downloader, errors, progress_callback)
            voices_path = _attempt_download(specs[1], target_dir, config.download_timeout, downloader, errors, progress_callback)
            downloaded = downloaded or (model_path is not None or voices_path is not None)

    ready = model_path is not None and voices_path is not None
    verified = bool(ready and (not specs[0].sha256 or model_path is not None) and (not specs[1].sha256 or voices_path is not None))

    if ready:
        _save_manifest(
            manifest_path,
            AssetManifest(
                model_version=specs[0].version,
                voices_version=specs[1].version,
                updated_at=datetime.now(timezone.utc).isoformat(),
            ),
        )

    return ResolvedAssets(
        model_path=model_path,
        voices_path=voices_path,
        ready=ready,
        errors=errors,
        manifest_path=manifest_path,
        verified=verified,
        downloaded=downloaded,
    )


def download_asset(
    spec: AssetSpec,
    target_dir: Path,
    timeout: float,
    urlopen: Callable[..., object] = _stdlib_urlopen,
    progress_callback: Callable[[int, int | None], None] | None = None,
    retry_policy: RetryPolicy | None = None,
    chunk_size: int = 64 * 1024,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / spec.filename
    temp_path = target_dir / f"{spec.filename}.tmp"

    _remove_if_exists(temp_path)

    try:
        def _fetch_payload() -> bytes:
            with urlopen(spec.url, timeout=timeout) as response:  # type: ignore[call-arg]
                total = _content_length(response)
                downloaded = 0
                chunks: list[bytes] = []
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if progress_callback is not None:
                        progress_callback(downloaded, total)
                if progress_callback is not None and downloaded == 0:
                    progress_callback(0, total)
                return b"".join(chunks)

        payload = retry_call(_fetch_payload, policy=retry_policy or RetryPolicy())

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
            version=_guess_version(config.model_url),
        ),
        AssetSpec(
            name="voices",
            filename=config.voices_filename,
            url=config.voices_url,
            sha256=config.voices_sha256,
            version=_guess_version(config.voices_url),
        ),
    )


def _attempt_download(
    spec: AssetSpec,
    target_dir: Path,
    timeout: float,
    downloader: Callable[..., Path] | None,
    errors: list[str],
    progress_callback: Callable[[str, int, int | None], None] | None = None,
) -> Path | None:
    selected_downloader = downloader if downloader is not None else download_asset
    try:
        if progress_callback is not None:
            return selected_downloader(
                spec,
                target_dir=target_dir,
                timeout=timeout,
                progress_callback=lambda downloaded, total: progress_callback(spec.name, downloaded, total),
            )
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


def _content_length(response: object) -> int | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("Content-Length")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _guess_version(url: str) -> str | None:
    lowered = url.lower()
    if "/download/" not in lowered:
        return None
    segments = [segment for segment in url.split("/") if segment]
    for idx, segment in enumerate(segments):
        if segment == "download" and idx + 1 < len(segments):
            return segments[idx + 1]
    return None


def _load_manifest(path: Path) -> AssetManifest | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return AssetManifest(
        model_version=_clean_text(payload.get("model_version")),
        voices_version=_clean_text(payload.get("voices_version")),
        updated_at=_clean_text(payload.get("updated_at")),
    )


def _save_manifest(path: Path, manifest: AssetManifest) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp")
    payload = asdict(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        _remove_if_exists(tmp_path)


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _verify_existing_checksum(path: Path, expected_sha256: str) -> bool:
    try:
        payload = path.read_bytes()
    except OSError:
        return False
    digest = hashlib.sha256(payload).hexdigest()
    return digest.lower() == expected_sha256.lower()
