from __future__ import annotations

import pytest

_NON_UNIT_MARKERS = {"integration", "e2e", "perf"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        marker_names = {marker.name for marker in item.iter_markers()}
        if marker_names.isdisjoint(_NON_UNIT_MARKERS):
            item.add_marker(pytest.mark.unit)
