from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType


def configure_logging(*, log_path: Path, name: str = "kookie") -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    existing_file_handler = any(
        isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", "") == str(log_path)
        for handler in logger.handlers
    )
    if not existing_file_handler:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)

    return logger


def make_crash_hook(*, crash_dir: Path) -> Callable[[type[BaseException], BaseException, TracebackType | None], None]:
    crash_dir.mkdir(parents=True, exist_ok=True)

    def _hook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        report_path = crash_dir / f"crash-{stamp}.log"
        with report_path.open("w", encoding="utf-8") as fh:
            fh.write("Unhandled exception\n\n")
            fh.write("".join(traceback.format_exception(exc_type, exc, tb)))

    return _hook
