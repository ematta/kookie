from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_defines_expected_pytest_markers() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    options = data["tool"]["pytest"]["ini_options"]
    markers = options["markers"]

    assert any(marker.startswith("unit:") for marker in markers)
    assert any(marker.startswith("integration:") for marker in markers)
    assert any(marker.startswith("e2e:") for marker in markers)
    assert any(marker.startswith("perf:") for marker in markers)


def test_pyproject_defines_coverage_thresholds() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    report = data["tool"]["coverage"]["report"]
    run = data["tool"]["coverage"]["run"]

    assert report["fail_under"] >= 80
    assert "kookie" in run["source"]


def test_pyproject_omits_gui_entrypoints_from_coverage() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    run = data["tool"]["coverage"]["run"]
    omit = run["omit"]

    assert "kookie/ui.py" in omit
    assert "kookie/__main__.py" in omit
