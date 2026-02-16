from kookie.config import AppConfig


def test_auto_clipboard_sync_defaults_to_false() -> None:
    cfg = AppConfig()
    assert cfg.auto_clipboard_sync is False


def test_auto_clipboard_sync_parses_true_from_env(monkeypatch) -> None:
    monkeypatch.setenv("KOOKIE_AUTO_CLIPBOARD_SYNC", "true")
    cfg = AppConfig.from_env()
    assert cfg.auto_clipboard_sync is True
