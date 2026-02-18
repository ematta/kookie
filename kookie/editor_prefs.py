from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CURATED_FONT_NAMES: tuple[str, ...] = (
    "Roboto",
    "Arial",
    "Courier New",
    "Times New Roman",
)
EDITOR_FONT_SIZES: tuple[int, ...] = (10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 40, 48, 56, 64, 72)
DEFAULT_FONT_NAME = "Roboto"
DEFAULT_FONT_SIZE = 20
DEFAULT_WORD_WRAP = True
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 72


@dataclass(frozen=True, slots=True)
class EditorPreferences:
    font_name: str = DEFAULT_FONT_NAME
    font_size: int = DEFAULT_FONT_SIZE
    word_wrap: bool = DEFAULT_WORD_WRAP


def prefs_path_for_asset_dir(asset_dir: Path) -> Path:
    return asset_dir.expanduser().parent / "editor_prefs.json"


def load_editor_preferences(asset_dir: Path) -> EditorPreferences:
    path = prefs_path_for_asset_dir(asset_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError, ValueError):
        return EditorPreferences()

    if not isinstance(payload, dict):
        return EditorPreferences()

    return sanitize_editor_preferences(
        font_name=payload.get("font_name"),
        font_size=payload.get("font_size"),
        word_wrap=payload.get("word_wrap"),
    )


def save_editor_preferences(asset_dir: Path, prefs: EditorPreferences) -> None:
    path = prefs_path_for_asset_dir(asset_dir)
    cleaned = sanitize_editor_preferences(
        font_name=prefs.font_name,
        font_size=prefs.font_size,
        word_wrap=prefs.word_wrap,
    )
    payload = {
        "font_name": cleaned.font_name,
        "font_size": cleaned.font_size,
        "word_wrap": cleaned.word_wrap,
    }

    tmp_path = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception:
        _remove_if_exists(tmp_path)


def sanitize_editor_preferences(
    *,
    font_name: object,
    font_size: object,
    word_wrap: object,
) -> EditorPreferences:
    cleaned_name = _sanitize_font_name(font_name)
    cleaned_size = _sanitize_font_size(font_size)
    cleaned_wrap = word_wrap if isinstance(word_wrap, bool) else DEFAULT_WORD_WRAP
    return EditorPreferences(font_name=cleaned_name, font_size=cleaned_size, word_wrap=cleaned_wrap)


def _sanitize_font_name(value: object) -> str:
    if not isinstance(value, str):
        return DEFAULT_FONT_NAME
    cleaned = value.strip()
    return cleaned if cleaned in CURATED_FONT_NAMES else DEFAULT_FONT_NAME


def _sanitize_font_size(value: object) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_FONT_SIZE
    return min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, parsed))


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
