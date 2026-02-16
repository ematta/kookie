import io

import pytest

from kookie.assets import AssetDownloadError, AssetSpec, resolve_assets, download_asset
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
