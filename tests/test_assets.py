import io
from urllib.error import URLError

import pytest

from kookie.assets import AssetDownloadError, AssetSpec, download_asset, resolve_assets
from kookie.config import AppConfig


class _BytesResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def test_resolve_assets_prefers_local_files(tmp_path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)
    (tmp_path / cfg.model_filename).write_bytes(b"model")
    (tmp_path / cfg.voices_filename).write_bytes(b"voices")

    resolved = resolve_assets(cfg, ensure_download=False)

    assert resolved.ready is True
    assert resolved.model_path == tmp_path / cfg.model_filename
    assert resolved.voices_path == tmp_path / cfg.voices_filename
    assert resolved.errors == []


def test_config_honors_runtime_url_overrides(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("KOOKIE_MODEL_URL", "https://example.test/model.onnx")
    monkeypatch.setenv("KOOKIE_VOICES_URL", "https://example.test/voices.bin")

    cfg = AppConfig.from_env()

    assert cfg.model_url == "https://example.test/model.onnx"
    assert cfg.voices_url == "https://example.test/voices.bin"


def test_resolve_assets_reports_non_fatal_download_failure(tmp_path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)

    def failing_downloader(*_, **__):
        raise AssetDownloadError("offline")

    resolved = resolve_assets(cfg, ensure_download=True, downloader=failing_downloader)

    assert resolved.ready is False
    assert resolved.model_path is None
    assert resolved.voices_path is None
    assert any("offline" in msg for msg in resolved.errors)


def test_download_asset_cleans_temp_file_on_checksum_failure(tmp_path) -> None:
    spec = AssetSpec(
        name="model",
        filename="model.onnx",
        url="https://example.test/model.onnx",
        sha256="0" * 64,
    )

    def fake_urlopen(url: str, timeout: float):
        assert url == spec.url
        assert timeout == 2.0
        return _BytesResponse(b"incorrect-checksum")

    with pytest.raises(AssetDownloadError):
        download_asset(spec, target_dir=tmp_path, timeout=2.0, urlopen=fake_urlopen)

    assert not (tmp_path / "model.onnx").exists()
    assert not (tmp_path / "model.onnx.tmp").exists()


def test_download_asset_retries_transient_network_error(tmp_path) -> None:
    spec = AssetSpec(
        name="model",
        filename="model.onnx",
        url="https://example.test/model.onnx",
        sha256=None,
    )
    attempts = {"count": 0}

    def fake_urlopen(url: str, timeout: float):
        assert url == spec.url
        assert timeout == 2.0
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise URLError("offline")
        return _BytesResponse(b"model-bytes")

    saved = download_asset(spec, target_dir=tmp_path, timeout=2.0, urlopen=fake_urlopen)

    assert saved == tmp_path / "model.onnx"
    assert saved.read_bytes() == b"model-bytes"
    assert attempts["count"] == 3


def test_download_asset_reports_progress(tmp_path) -> None:
    spec = AssetSpec(
        name="model",
        filename="model.onnx",
        url="https://example.test/model.onnx",
        sha256=None,
    )
    events: list[tuple[int, int | None]] = []

    class _Response(_BytesResponse):
        def __init__(self):
            super().__init__(b"abcdefghij")
            self.headers = {"Content-Length": "10"}

    def fake_urlopen(url: str, timeout: float):
        assert url == spec.url
        assert timeout == 2.0
        return _Response()

    saved = download_asset(
        spec,
        target_dir=tmp_path,
        timeout=2.0,
        urlopen=fake_urlopen,
        progress_callback=lambda downloaded, total: events.append((downloaded, total)),
    )

    assert saved.read_bytes() == b"abcdefghij"
    assert events[-1] == (10, 10)


def test_resolve_assets_writes_manifest_when_ready(tmp_path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)
    (tmp_path / cfg.model_filename).write_bytes(b"model")
    (tmp_path / cfg.voices_filename).write_bytes(b"voices")

    resolved = resolve_assets(cfg, ensure_download=False)

    assert resolved.ready is True
    assert resolved.manifest_path is not None
    assert resolved.manifest_path.exists()
    assert "model_version" in resolved.manifest_path.read_text(encoding="utf-8")


def test_resolve_assets_can_require_checksums(tmp_path) -> None:
    cfg = AppConfig(
        asset_dir=tmp_path,
        require_asset_checksums=True,
        model_sha256=None,
        voices_sha256=None,
    )

    resolved = resolve_assets(cfg, ensure_download=False)

    assert resolved.ready is False
    assert any("checksum is required" in message for message in resolved.errors)
