from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# When Python resolves 'conftest' to this file (due to sys.path ordering with
# nested conftest files), re-export _AudioPlayer so that
# `from conftest import _AudioPlayer` in test modules continues to work.
_root_spec = importlib.util.spec_from_file_location(
    "_root_conftest", Path(__file__).parent.parent / "conftest.py"
)
assert _root_spec is not None and _root_spec.loader is not None
_root_mod = importlib.util.module_from_spec(_root_spec)
_root_spec.loader.exec_module(_root_mod)  # type: ignore[union-attr]
_AudioPlayer = _root_mod._AudioPlayer

pytestmark = pytest.mark.perf
