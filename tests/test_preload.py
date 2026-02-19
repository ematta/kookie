from pathlib import Path

from kookie.assets import AssetDownloadError
from kookie.config import AppConfig
from kookie.preload import preload_assets, preload_voice


def test_preload_assets_skips_download_when_model_and_voice_exist(tmp_path: Path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)
    existing_model = tmp_path / cfg.model_filename
    existing_voice = tmp_path / cfg.voices_filename
    existing_model.write_bytes(b"model-bytes")
    existing_voice.write_bytes(b"voice-bytes")

    called = False

    def fake_downloader(*_, **__):
        nonlocal called
        called = True
        raise AssertionError("downloader should not run when assets already exist")

    result = preload_assets(cfg, downloader=fake_downloader)

    assert called is False
    assert result.ready is True
    assert result.model_path == existing_model
    assert result.voices_path == existing_voice
    assert result.downloaded is False
    assert "already available" in result.message.lower()


def test_preload_assets_downloads_missing_model_and_voice(tmp_path: Path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)
    calls: list[str] = []

    def fake_downloader(spec, target_dir: Path, timeout: float):
        calls.append(spec.name)
        assert target_dir == tmp_path
        assert timeout == cfg.download_timeout
        output = target_dir / spec.filename
        output.write_bytes(spec.name.encode("utf-8"))
        return output

    result = preload_assets(cfg, downloader=fake_downloader)

    assert calls == ["model", "voices"]
    assert result.ready is True
    assert result.model_path == tmp_path / cfg.model_filename
    assert result.voices_path == tmp_path / cfg.voices_filename
    assert result.downloaded is True
    assert "downloaded" in result.message.lower()


def test_preload_assets_reports_partial_download_failure(tmp_path: Path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)
    calls: list[str] = []

    def partially_failing_downloader(spec, target_dir: Path, timeout: float):
        calls.append(spec.name)
        assert target_dir == tmp_path
        assert timeout == cfg.download_timeout
        if spec.name == "voices":
            raise AssetDownloadError("offline")
        output = target_dir / spec.filename
        output.write_bytes(b"model-bytes")
        return output

    result = preload_assets(cfg, downloader=partially_failing_downloader)

    assert calls == ["model", "voices"]
    assert result.ready is False
    assert result.model_path == tmp_path / cfg.model_filename
    assert result.voices_path is None
    assert "voices" in result.message.lower()
    assert "offline" in result.message


def test_preload_voice_skips_download_when_voice_exists(tmp_path: Path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)
    existing = tmp_path / cfg.voices_filename
    existing.write_bytes(b"voice-bytes")

    called = False

    def fake_downloader(*_, **__):
        nonlocal called
        called = True
        raise AssertionError("downloader should not run when voice exists")

    result = preload_voice(cfg, downloader=fake_downloader)

    assert called is False
    assert result.voices_path == existing
    assert result.downloaded is False


def test_preload_voice_downloads_when_missing(tmp_path: Path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)

    def fake_downloader(spec, target_dir: Path, timeout: float):
        assert spec.name == "voices"
        assert spec.filename == cfg.voices_filename
        assert target_dir == tmp_path
        assert timeout == cfg.download_timeout

        output = target_dir / spec.filename
        output.write_bytes(b"downloaded-voice")
        return output

    result = preload_voice(cfg, downloader=fake_downloader)

    assert result.voices_path == tmp_path / cfg.voices_filename
    assert result.downloaded is True
    assert result.message.startswith("Downloaded voice")


def test_preload_voice_reports_download_failure(tmp_path: Path) -> None:
    cfg = AppConfig(asset_dir=tmp_path)

    def failing_downloader(*_, **__):
        raise AssetDownloadError("offline")

    result = preload_voice(cfg, downloader=failing_downloader)

    assert result.voices_path is None
    assert result.downloaded is False
    assert "offline" in result.message
