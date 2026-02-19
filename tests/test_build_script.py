from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_script_sets_local_cache_paths() -> None:
    script = (ROOT / "scripts" / "build_app.sh").read_text(encoding="utf-8")

    assert "UV_CACHE_DIR" in script
    assert "PYINSTALLER_CONFIG_DIR" in script
    assert "KIVY_HOME" in script
    assert "mkdir -p" in script
