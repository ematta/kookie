"""Helpers for generating and refreshing AGENTS.md."""

from __future__ import annotations

import argparse
import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path

AUTO_START = "<!-- BEGIN AUTO -->"
AUTO_END = "<!-- END AUTO -->"

_AUTO_BLOCK_RE = re.compile(
    rf"{re.escape(AUTO_START)}.*?{re.escape(AUTO_END)}",
    flags=re.DOTALL,
)
_EXCLUDED_TOP_LEVEL_DIRS = {"build", "dist", "__pycache__"}

_TEMPLATE = """# AGENTS

This file self-updates via `python -m kookie.agents_updater`.
Only edit content outside the auto-generated section markers.

## Working Agreement
- Start with unit tests before implementation changes.
- Prefer simple, local dependencies and efficient implementations.
- Keep sections concise and actionable.

{auto_block}
"""


def _normalize_timestamp(generated_at: datetime | None) -> str:
    stamp = generated_at or datetime.now(UTC)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    else:
        stamp = stamp.astimezone(UTC)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_project(pyproject_path: Path) -> dict:
    contents = pyproject_path.read_text(encoding="utf-8")
    parsed = tomllib.loads(contents)
    return parsed.get("project", {})


def _discover_top_level_dirs(repo_root: Path) -> list[str]:
    directories: list[str] = []
    for path in sorted(repo_root.iterdir(), key=lambda entry: entry.name.lower()):
        if not path.is_dir():
            continue
        if path.name.startswith("."):
            continue
        if path.name in _EXCLUDED_TOP_LEVEL_DIRS:
            continue
        directories.append(f"{path.name}/")
    return directories


def generate_auto_block(
    *, pyproject_path: Path, repo_root: Path, generated_at: datetime | None = None
) -> str:
    project = _read_project(pyproject_path)

    name = project.get("name", "unknown")
    version = project.get("version", "unknown")
    requires_python = project.get("requires-python", "unspecified")
    dependencies = sorted(project.get("dependencies") or [])
    scripts = project.get("scripts") or {}

    lines = [
        AUTO_START,
        "## Auto-Generated Snapshot",
        f"- Last updated (UTC): `{_normalize_timestamp(generated_at)}`",
        f"- Project: `{name}`",
        f"- Version: `{version}`",
        f"- Python: `{requires_python}`",
    ]

    if scripts:
        lines.extend(["", "### Console Scripts"])
        for script_name, target in sorted(scripts.items()):
            lines.append(f"- `uv run {script_name}` -> `{target}`")

    if dependencies:
        lines.extend(["", "### Dependencies"])
        for dependency in dependencies:
            lines.append(f"- `{dependency}`")

    top_level_dirs = _discover_top_level_dirs(repo_root)
    if top_level_dirs:
        lines.extend(["", "### Top-Level Directories"])
        for directory in top_level_dirs:
            lines.append(f"- `{directory}`")

    lines.append(AUTO_END)
    return "\n".join(lines)


def refresh_agents_file(
    *,
    agents_path: Path,
    pyproject_path: Path,
    repo_root: Path,
    generated_at: datetime | None = None,
) -> str:
    auto_block = generate_auto_block(
        pyproject_path=pyproject_path,
        repo_root=repo_root,
        generated_at=generated_at,
    )

    if agents_path.exists():
        current = agents_path.read_text(encoding="utf-8")
        if AUTO_START in current and AUTO_END in current:
            updated = _AUTO_BLOCK_RE.sub(auto_block, current, count=1)
        else:
            updated = f"{current.rstrip()}\n\n{auto_block}\n"
    else:
        updated = _TEMPLATE.format(auto_block=auto_block)

    agents_path.write_text(updated, encoding="utf-8")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh AGENTS.md auto-generated section")
    parser.add_argument(
        "--agents-path",
        default="AGENTS.md",
        help="Path to the AGENTS file to create/update.",
    )
    parser.add_argument(
        "--pyproject-path",
        default="pyproject.toml",
        help="Path to pyproject.toml.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used for top-level directory snapshot.",
    )
    args = parser.parse_args()

    agents_path = Path(args.agents_path)
    pyproject_path = Path(args.pyproject_path)
    repo_root = Path(args.repo_root)

    refresh_agents_file(
        agents_path=agents_path,
        pyproject_path=pyproject_path,
        repo_root=repo_root,
    )
    print(f"Updated {agents_path}")


if __name__ == "__main__":
    main()
