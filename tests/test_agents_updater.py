from datetime import datetime, timezone
from pathlib import Path

from kookie.agents_updater import AUTO_END, AUTO_START, generate_auto_block, refresh_agents_file


def _write_pyproject(path: Path) -> None:
    path.write_text(
        """
[project]
name = "demo"
version = "1.2.3"
requires-python = ">=3.12"
dependencies = [
  "alpha>=1",
  "beta>=2",
]

[project.scripts]
demo = "demo.cli:main"
demo-admin = "demo.admin:main"
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_generate_auto_block_includes_project_snapshot(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    _write_pyproject(pyproject_path)
    (tmp_path / "kookie").mkdir()
    (tmp_path / "tests").mkdir()

    block = generate_auto_block(
        pyproject_path=pyproject_path,
        repo_root=tmp_path,
        generated_at=datetime(2026, 2, 17, 15, 30, tzinfo=timezone.utc),
    )

    assert AUTO_START in block
    assert AUTO_END in block
    assert "- Last updated (UTC): `2026-02-17T15:30:00Z`" in block
    assert "- Project: `demo`" in block
    assert "- Version: `1.2.3`" in block
    assert "- Python: `>=3.12`" in block
    assert "- `alpha>=1`" in block
    assert "- `beta>=2`" in block
    assert "- `uv run demo` -> `demo.cli:main`" in block
    assert "- `uv run demo-admin` -> `demo.admin:main`" in block
    assert "- `kookie/`" in block
    assert "- `tests/`" in block


def test_refresh_agents_file_replaces_auto_block_only(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    _write_pyproject(pyproject_path)
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        """
# AGENTS

Manual intro.

<!-- BEGIN AUTO -->
old auto content
<!-- END AUTO -->

Manual outro.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    refresh_agents_file(
        agents_path=agents_path,
        pyproject_path=pyproject_path,
        repo_root=tmp_path,
        generated_at=datetime(2026, 2, 17, 15, 30, tzinfo=timezone.utc),
    )

    updated = agents_path.read_text(encoding="utf-8")

    assert "Manual intro." in updated
    assert "Manual outro." in updated
    assert "old auto content" not in updated
    assert updated.count(AUTO_START) == 1
    assert updated.count(AUTO_END) == 1


def test_refresh_agents_file_creates_new_file_with_template(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    _write_pyproject(pyproject_path)
    agents_path = tmp_path / "AGENTS.md"

    refresh_agents_file(
        agents_path=agents_path,
        pyproject_path=pyproject_path,
        repo_root=tmp_path,
        generated_at=datetime(2026, 2, 17, 15, 30, tzinfo=timezone.utc),
    )

    created = agents_path.read_text(encoding="utf-8")

    assert created.startswith("# AGENTS")
    assert "This file self-updates via `python -m kookie.agents_updater`." in created
    assert AUTO_START in created
    assert AUTO_END in created
    assert "- Project: `demo`" in created
