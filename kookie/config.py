from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
import tomllib


DEFAULT_MODEL_URL = "https://github.com/hexgrad/kokoro/releases/download/v0.19/kokoro-v0_19.onnx"
DEFAULT_VOICES_URL = "https://github.com/hexgrad/kokoro/releases/download/v0.19/voices.bin"
DEFAULT_CONFIG_FILE = Path.home() / ".config" / "kookie" / "config.toml"
SUPPORTED_THEMES = {"system", "light", "dark"}
SUPPORTED_LANGUAGES = {"en", "es"}


@dataclass(slots=True)
class AppConfig:
    config_version: int = 1
    backend_mode: str = "auto"
    asset_dir: Path = field(
        default_factory=lambda: Path.home() / "Library" / "Application Support" / "Kookie" / "assets"
    )
    config_file: Path = DEFAULT_CONFIG_FILE
    model_filename: str = "kokoro-v0_19.onnx"
    voices_filename: str = "voices.bin"
    model_url: str = DEFAULT_MODEL_URL
    voices_url: str = DEFAULT_VOICES_URL
    model_sha256: str | None = None
    voices_sha256: str | None = None
    default_voice: str = "af_sarah"
    sample_rate: int = 24_000
    download_timeout: float = 30.0
    audio_queue_timeout: float = 0.1
    require_asset_checksums: bool = False
    asset_auto_update: bool = True
    asset_manifest_filename: str = "asset_manifest.json"
    telemetry_enabled: bool = False
    telemetry_file: Path = field(
        default_factory=lambda: Path.home() / "Library" / "Application Support" / "Kookie" / "telemetry.jsonl"
    )
    update_check_enabled: bool = True
    update_repo: str = "ematta/kookie"
    language: str = "en"
    theme: str = "system"
    high_contrast: bool = False
    health_check_enabled: bool = False
    health_check_host: str = "127.0.0.1"
    health_check_port: int = 8765
    synthesis_cache_size: int = 32
    normalization_cache_size: int = 512

    @classmethod
    def from_env(cls, base: "AppConfig | None" = None) -> "AppConfig":
        base_cfg = base or cls()

        backend_mode = os.getenv("KOOKIE_BACKEND_MODE", base_cfg.backend_mode).strip().lower() or "auto"
        if backend_mode not in {"auto", "mock", "real"}:
            backend_mode = "auto"

        asset_dir_raw = os.getenv("KOOKIE_ASSET_DIR", "").strip()
        asset_dir = Path(asset_dir_raw).expanduser() if asset_dir_raw else base_cfg.asset_dir

        sample_rate = _sanitize_sample_rate(_safe_int(os.getenv("KOOKIE_SAMPLE_RATE"), default=base_cfg.sample_rate))
        download_timeout = _sanitize_positive_float(
            _safe_float(os.getenv("KOOKIE_DOWNLOAD_TIMEOUT"), default=base_cfg.download_timeout),
            default=30.0,
        )
        audio_queue_timeout = _sanitize_positive_float(
            _safe_float(os.getenv("KOOKIE_AUDIO_QUEUE_TIMEOUT"), default=base_cfg.audio_queue_timeout),
            default=0.1,
        )
        health_check_port = _sanitize_port(_safe_int(os.getenv("KOOKIE_HEALTH_CHECK_PORT"), default=base_cfg.health_check_port))

        return cls(
            config_version=max(1, _safe_int(os.getenv("KOOKIE_CONFIG_VERSION"), default=base_cfg.config_version)),
            backend_mode=backend_mode,
            asset_dir=asset_dir,
            config_file=Path(os.getenv("KOOKIE_CONFIG_FILE", str(base_cfg.config_file))).expanduser(),
            model_filename=os.getenv("KOOKIE_MODEL_FILENAME", base_cfg.model_filename).strip() or base_cfg.model_filename,
            voices_filename=os.getenv("KOOKIE_VOICES_FILENAME", base_cfg.voices_filename).strip() or base_cfg.voices_filename,
            model_url=os.getenv("KOOKIE_MODEL_URL", base_cfg.model_url).strip() or DEFAULT_MODEL_URL,
            voices_url=os.getenv("KOOKIE_VOICES_URL", base_cfg.voices_url).strip() or DEFAULT_VOICES_URL,
            model_sha256=_clean_optional(os.getenv("KOOKIE_MODEL_SHA256")),
            voices_sha256=_clean_optional(os.getenv("KOOKIE_VOICES_SHA256")),
            default_voice=os.getenv("KOOKIE_DEFAULT_VOICE", base_cfg.default_voice).strip() or "af_sarah",
            sample_rate=sample_rate,
            download_timeout=download_timeout,
            audio_queue_timeout=audio_queue_timeout,
            require_asset_checksums=_safe_bool(
                os.getenv("KOOKIE_REQUIRE_ASSET_CHECKSUMS"),
                default=base_cfg.require_asset_checksums,
            ),
            asset_auto_update=_safe_bool(
                os.getenv("KOOKIE_ASSET_AUTO_UPDATE"),
                default=base_cfg.asset_auto_update,
            ),
            asset_manifest_filename=os.getenv("KOOKIE_ASSET_MANIFEST_FILENAME", base_cfg.asset_manifest_filename).strip()
            or "asset_manifest.json",
            telemetry_enabled=_safe_bool(
                os.getenv("KOOKIE_TELEMETRY_ENABLED"),
                default=base_cfg.telemetry_enabled,
            ),
            telemetry_file=Path(
                os.getenv("KOOKIE_TELEMETRY_FILE", str(base_cfg.telemetry_file))
            ).expanduser(),
            update_check_enabled=_safe_bool(
                os.getenv("KOOKIE_UPDATE_CHECK_ENABLED"),
                default=base_cfg.update_check_enabled,
            ),
            update_repo=os.getenv("KOOKIE_UPDATE_REPO", base_cfg.update_repo).strip() or "ematta/kookie",
            language=_sanitize_language(os.getenv("KOOKIE_LANGUAGE", base_cfg.language)),
            theme=_sanitize_theme(os.getenv("KOOKIE_THEME", base_cfg.theme)),
            high_contrast=_safe_bool(
                os.getenv("KOOKIE_HIGH_CONTRAST"),
                default=base_cfg.high_contrast,
            ),
            health_check_enabled=_safe_bool(
                os.getenv("KOOKIE_HEALTH_CHECK_ENABLED"),
                default=base_cfg.health_check_enabled,
            ),
            health_check_host=os.getenv("KOOKIE_HEALTH_CHECK_HOST", base_cfg.health_check_host).strip() or "127.0.0.1",
            health_check_port=health_check_port,
            synthesis_cache_size=max(1, _safe_int(os.getenv("KOOKIE_SYNTH_CACHE_SIZE"), default=base_cfg.synthesis_cache_size)),
            normalization_cache_size=max(
                64,
                _safe_int(os.getenv("KOOKIE_TEXT_CACHE_SIZE"), default=base_cfg.normalization_cache_size),
            ),
        )

    @classmethod
    def from_toml(cls, path: Path) -> "AppConfig":
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError, tomllib.TOMLDecodeError):
            return cls(config_file=path)

        if not isinstance(payload, dict):
            return cls(config_file=path)

        def _value(name: str, default):
            return payload.get(name, default)

        candidate = cls(
            config_version=max(1, _safe_int(_value("config_version", 1), default=1)),
            backend_mode=str(_value("backend_mode", "auto")).strip().lower() or "auto",
            asset_dir=Path(str(_value("asset_dir", cls().asset_dir))).expanduser(),
            config_file=path,
            model_filename=str(_value("model_filename", cls().model_filename)).strip() or cls().model_filename,
            voices_filename=str(_value("voices_filename", cls().voices_filename)).strip() or cls().voices_filename,
            model_url=str(_value("model_url", DEFAULT_MODEL_URL)).strip() or DEFAULT_MODEL_URL,
            voices_url=str(_value("voices_url", DEFAULT_VOICES_URL)).strip() or DEFAULT_VOICES_URL,
            model_sha256=_clean_optional(_value("model_sha256", None)),
            voices_sha256=_clean_optional(_value("voices_sha256", None)),
            default_voice=str(_value("default_voice", "af_sarah")).strip() or "af_sarah",
            sample_rate=_sanitize_sample_rate(_safe_int(_value("sample_rate", 24_000), default=24_000)),
            download_timeout=_sanitize_positive_float(
                _safe_float(_value("download_timeout", 30.0), default=30.0),
                default=30.0,
            ),
            audio_queue_timeout=_sanitize_positive_float(
                _safe_float(_value("audio_queue_timeout", 0.1), default=0.1),
                default=0.1,
            ),
            require_asset_checksums=_safe_bool(_value("require_asset_checksums", False), default=False),
            asset_auto_update=_safe_bool(_value("asset_auto_update", True), default=True),
            asset_manifest_filename=str(_value("asset_manifest_filename", "asset_manifest.json")).strip()
            or "asset_manifest.json",
            telemetry_enabled=_safe_bool(_value("telemetry_enabled", False), default=False),
            telemetry_file=Path(
                str(_value("telemetry_file", Path.home() / "Library" / "Application Support" / "Kookie" / "telemetry.jsonl"))
            ).expanduser(),
            update_check_enabled=_safe_bool(_value("update_check_enabled", True), default=True),
            update_repo=str(_value("update_repo", "ematta/kookie")).strip() or "ematta/kookie",
            language=_sanitize_language(_value("language", "en")),
            theme=_sanitize_theme(_value("theme", "system")),
            high_contrast=_safe_bool(_value("high_contrast", False), default=False),
            health_check_enabled=_safe_bool(_value("health_check_enabled", False), default=False),
            health_check_host=str(_value("health_check_host", "127.0.0.1")).strip() or "127.0.0.1",
            health_check_port=_sanitize_port(_safe_int(_value("health_check_port", 8765), default=8765)),
            synthesis_cache_size=max(1, _safe_int(_value("synthesis_cache_size", 32), default=32)),
            normalization_cache_size=max(64, _safe_int(_value("normalization_cache_size", 512), default=512)),
        )

        if candidate.backend_mode not in {"auto", "mock", "real"}:
            candidate.backend_mode = "auto"
        return candidate


def load_config() -> AppConfig:
    config_file = Path(os.getenv("KOOKIE_CONFIG_FILE", str(DEFAULT_CONFIG_FILE))).expanduser()
    base = AppConfig.from_toml(config_file)
    return AppConfig.from_env(base)


def _safe_int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _safe_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _sanitize_positive_float(value: float, *, default: float) -> float:
    if value <= 0:
        return default
    return value


def _sanitize_sample_rate(value: int) -> int:
    if value <= 0:
        return 24_000
    return value


def _sanitize_theme(value: object) -> str:
    lowered = str(value).strip().lower()
    if lowered in SUPPORTED_THEMES:
        return lowered
    return "system"


def _sanitize_language(value: object) -> str:
    lowered = str(value).strip().lower()
    if lowered in SUPPORTED_LANGUAGES:
        return lowered
    return "en"


def _sanitize_port(value: int) -> int:
    if 1 <= value <= 65_535:
        return value
    return 8765
