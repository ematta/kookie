from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_exists_with_cross_platform_matrix() -> None:
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    contents = workflow.read_text(encoding="utf-8")

    assert "runs-on: ${{ matrix.os }}" in contents
    assert "macos-latest" in contents
    assert "ubuntu-latest" in contents
    assert "windows-latest" in contents
    assert "uv run pytest -q" in contents


def test_release_workflow_exists() -> None:
    workflow = ROOT / ".github" / "workflows" / "release.yml"
    contents = workflow.read_text(encoding="utf-8")

    assert "workflow_dispatch" in contents
    assert "build_app.sh" in contents


def test_dependabot_config_exists() -> None:
    path = ROOT / ".github" / "dependabot.yml"
    contents = path.read_text(encoding="utf-8")

    assert "package-ecosystem: \"uv\"" in contents
    assert "package-ecosystem: \"github-actions\"" in contents


def test_dmg_script_exists() -> None:
    script = ROOT / "scripts" / "create_dmg.sh"
    contents = script.read_text(encoding="utf-8")

    assert "hdiutil create" in contents
    assert "Kookie.app" in contents
