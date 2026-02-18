from pathlib import Path

from kookie.editor_prefs import (
    EditorPreferences,
    load_editor_preferences,
    prefs_path_for_asset_dir,
    sanitize_editor_preferences,
    save_editor_preferences,
)


def test_prefs_path_is_parent_of_asset_dir() -> None:
    asset_dir = Path("/tmp/kookie/assets")
    assert prefs_path_for_asset_dir(asset_dir) == Path("/tmp/kookie/editor_prefs.json")


def test_load_editor_preferences_defaults_when_missing(tmp_path: Path) -> None:
    prefs = load_editor_preferences(tmp_path / "assets")
    assert prefs == EditorPreferences(font_name="Roboto", font_size=20, word_wrap=True)


def test_load_editor_preferences_defaults_when_json_invalid(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    path = prefs_path_for_asset_dir(asset_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-valid-json", encoding="utf-8")

    prefs = load_editor_preferences(asset_dir)
    assert prefs == EditorPreferences(font_name="Roboto", font_size=20, word_wrap=True)


def test_sanitize_editor_preferences_clamps_font_size() -> None:
    low = sanitize_editor_preferences(font_name="Roboto", font_size=1, word_wrap=True)
    high = sanitize_editor_preferences(font_name="Roboto", font_size=999, word_wrap=True)
    assert low.font_size == 10
    assert high.font_size == 72


def test_sanitize_editor_preferences_unknown_font_falls_back() -> None:
    prefs = sanitize_editor_preferences(font_name="Unknown Font", font_size=20, word_wrap=True)
    assert prefs.font_name == "Roboto"


def test_save_and_load_editor_preferences_round_trip(tmp_path: Path) -> None:
    asset_dir = tmp_path / "assets"
    prefs = EditorPreferences(font_name="Courier New", font_size=24, word_wrap=False)

    save_editor_preferences(asset_dir, prefs)
    loaded = load_editor_preferences(asset_dir)

    assert loaded == prefs
    assert prefs_path_for_asset_dir(asset_dir).exists()
