from __future__ import annotations

from pathlib import Path

from kookie.config import AppConfig, load_config


def test_load_config_reads_toml_file(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "kookie.toml"
    config_file.write_text(
        """
backend_mode = "mock"
sample_rate = 16000
download_timeout = 12.5
default_voice = "af_nicole"
telemetry_enabled = true
language = "es"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KOOKIE_CONFIG_FILE", str(config_file))

    cfg = load_config()

    assert cfg.backend_mode == "mock"
    assert cfg.sample_rate == 16000
    assert cfg.download_timeout == 12.5
    assert cfg.default_voice == "af_nicole"
    assert cfg.telemetry_enabled is True
    assert cfg.language == "es"


def test_env_overrides_toml_values(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "kookie.toml"
    config_file.write_text(
        """
sample_rate = 16000
default_voice = "af_nicole"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KOOKIE_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("KOOKIE_SAMPLE_RATE", "24000")
    monkeypatch.setenv("KOOKIE_DEFAULT_VOICE", "af_sarah")

    cfg = load_config()

    assert cfg.sample_rate == 24000
    assert cfg.default_voice == "af_sarah"


def test_invalid_config_values_are_safely_sanitized(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "kookie.toml"
    config_file.write_text(
        """
backend_mode = "invalid"
sample_rate = -1
download_timeout = -5
audio_queue_timeout = 0
theme = "???"
language = ""
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KOOKIE_CONFIG_FILE", str(config_file))

    cfg = load_config()

    assert cfg.backend_mode == "auto"
    assert cfg.sample_rate == 24000
    assert cfg.download_timeout == 30.0
    assert cfg.audio_queue_timeout > 0
    assert cfg.theme in {"system", "light", "dark"}
    assert cfg.language == "en"


def test_config_defaults_include_supported_migration_version() -> None:
    cfg = AppConfig()

    assert cfg.config_version >= 1
