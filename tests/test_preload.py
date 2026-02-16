from pathlib import Path

from kookie.assets import AssetDownloadError
from kookie.config import AppConfig
from kookie.preload import preload_voice


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
