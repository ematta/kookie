from __future__ import annotations

from pathlib import Path

from kookie.logging_utils import configure_logging, make_crash_hook


def test_configure_logging_creates_log_file(tmp_path: Path) -> None:
    log_path = tmp_path / "kookie.log"
    logger = configure_logging(log_path=log_path)

    logger.info("hello")

    assert log_path.exists()
    assert "hello" in log_path.read_text(encoding="utf-8")


def test_make_crash_hook_writes_crash_report(tmp_path: Path) -> None:
    crash_dir = tmp_path / "crash"
    hook = make_crash_hook(crash_dir=crash_dir)

    hook(RuntimeError, RuntimeError("boom"), None)

    files = list(crash_dir.glob("crash-*.log"))
    assert len(files) == 1
    assert "boom" in files[0].read_text(encoding="utf-8")
