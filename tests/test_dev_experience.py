from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_makefile_includes_common_commands() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "test:" in makefile
    assert "lint:" in makefile
    assert "typecheck:" in makefile


def test_precommit_configuration_exists() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "ruff" in config
    assert "mypy" in config


def test_vscode_configs_exist() -> None:
    settings = (ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
    launch = (ROOT / ".vscode" / "launch.json").read_text(encoding="utf-8")
    assert "python.testing.pytestEnabled" in settings
    assert "Kookie (main.py)" in launch


def test_docs_bundle_exists() -> None:
    required = [
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs" / "onboarding.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "troubleshooting.md",
        ROOT / "docs" / "user-guide.md",
    ]
    for path in required:
        assert path.exists(), f"missing required doc: {path}"
