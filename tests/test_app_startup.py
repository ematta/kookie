from dataclasses import dataclass
from types import SimpleNamespace

from kookie.app import run
from kookie.config import AppConfig


@dataclass
class _Runtime:
    config: AppConfig


def test_run_preloads_assets_before_normal_launch(monkeypatch, tmp_path) -> None:
    cfg = AppConfig(backend_mode="auto", asset_dir=tmp_path)
    preload_calls: list[AppConfig] = []
    create_calls: list[tuple[AppConfig, bool]] = []
    startup_prompts: list[object | None] = []

    def fake_preload(config: AppConfig):
        preload_calls.append(config)
        return SimpleNamespace(ready=True, message="ready")

    def fake_create(config: AppConfig, *, ensure_download: bool, **_):
        create_calls.append((config, ensure_download))
        return _Runtime(config=config)

    def fake_ui(runtime, startup_prompt=None):
        startup_prompts.append(startup_prompt)
        assert runtime.config == cfg
        return None

    monkeypatch.setattr("kookie.app.load_config", lambda: cfg)
    monkeypatch.setattr("kookie.app.preload_assets", fake_preload, raising=False)
    monkeypatch.setattr("kookie.app.create_app", fake_create)
    monkeypatch.setattr("kookie.ui.run_kivy_ui", fake_ui)

    run()

    assert preload_calls == [cfg]
    assert create_calls == [(cfg, False)]
    assert startup_prompts == [None]


def test_run_launches_mock_when_preload_fails_and_user_continues(monkeypatch, tmp_path) -> None:
    cfg = AppConfig(backend_mode="auto", asset_dir=tmp_path)
    preload_calls: list[AppConfig] = []
    create_calls: list[tuple[AppConfig, bool]] = []
    startup_prompts: list[object | None] = []

    def fake_preload(config: AppConfig):
        preload_calls.append(config)
        return SimpleNamespace(ready=False, message="voices download failed: offline")

    def fake_create(config: AppConfig, *, ensure_download: bool, **_):
        create_calls.append((config, ensure_download))
        return _Runtime(config=config)

    def fake_ui(runtime, startup_prompt=None):
        startup_prompts.append(startup_prompt)
        assert runtime.config.backend_mode == "mock"
        assert isinstance(startup_prompt, dict)
        assert "title" in startup_prompt
        assert "message" in startup_prompt
        assert startup_prompt.get("can_retry") is True
        return "continue_mock"

    monkeypatch.setattr("kookie.app.load_config", lambda: cfg)
    monkeypatch.setattr("kookie.app.preload_assets", fake_preload, raising=False)
    monkeypatch.setattr("kookie.app.create_app", fake_create)
    monkeypatch.setattr("kookie.ui.run_kivy_ui", fake_ui)

    run()

    assert preload_calls == [cfg]
    assert len(create_calls) == 1
    created_cfg, ensure_download = create_calls[0]
    assert ensure_download is False
    assert created_cfg.backend_mode == "mock"
    assert startup_prompts[0] is not None


def test_run_stops_when_preload_fails_and_user_quits(monkeypatch, tmp_path) -> None:
    cfg = AppConfig(backend_mode="auto", asset_dir=tmp_path)
    preload_calls: list[AppConfig] = []
    create_calls: list[tuple[AppConfig, bool]] = []

    def fake_preload(config: AppConfig):
        preload_calls.append(config)
        return SimpleNamespace(ready=False, message="model download failed: offline")

    def fake_create(config: AppConfig, *, ensure_download: bool, **_):
        create_calls.append((config, ensure_download))
        return _Runtime(config=config)

    def fake_ui(runtime, startup_prompt=None):
        assert runtime.config.backend_mode == "mock"
        assert startup_prompt is not None
        return "quit"

    monkeypatch.setattr("kookie.app.load_config", lambda: cfg)
    monkeypatch.setattr("kookie.app.preload_assets", fake_preload, raising=False)
    monkeypatch.setattr("kookie.app.create_app", fake_create)
    monkeypatch.setattr("kookie.ui.run_kivy_ui", fake_ui)

    run()

    assert preload_calls == [cfg]
    assert len(create_calls) == 1


def test_run_retries_preload_when_requested(monkeypatch, tmp_path) -> None:
    cfg = AppConfig(backend_mode="auto", asset_dir=tmp_path)
    preload_calls: list[AppConfig] = []
    create_calls: list[tuple[AppConfig, bool]] = []
    startup_prompts: list[object | None] = []
    preload_results = [
        SimpleNamespace(ready=False, message="voices download failed: offline"),
        SimpleNamespace(ready=True, message="ready"),
    ]

    def fake_preload(config: AppConfig):
        preload_calls.append(config)
        return preload_results.pop(0)

    def fake_create(config: AppConfig, *, ensure_download: bool, **_):
        create_calls.append((config, ensure_download))
        return _Runtime(config=config)

    def fake_ui(runtime, startup_prompt=None):
        startup_prompts.append(startup_prompt)
        if len(startup_prompts) == 1:
            assert runtime.config.backend_mode == "mock"
            return "retry"
        assert runtime.config.backend_mode == "auto"
        return None

    monkeypatch.setattr("kookie.app.load_config", lambda: cfg)
    monkeypatch.setattr("kookie.app.preload_assets", fake_preload, raising=False)
    monkeypatch.setattr("kookie.app.create_app", fake_create)
    monkeypatch.setattr("kookie.ui.run_kivy_ui", fake_ui)

    run()

    assert preload_calls == [cfg, cfg]
    assert len(create_calls) == 2
    first_cfg, first_ensure_download = create_calls[0]
    second_cfg, second_ensure_download = create_calls[1]
    assert first_cfg.backend_mode == "mock"
    assert second_cfg.backend_mode == "auto"
    assert first_ensure_download is False
    assert second_ensure_download is False
    assert startup_prompts[0] is not None
    assert startup_prompts[1] is None
