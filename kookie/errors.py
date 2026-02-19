from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.error import URLError


class ErrorCategory(Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    AUDIO_DEVICE = "audio_device"
    BACKEND = "backend"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class ErrorCode(Enum):
    NETWORK_UNAVAILABLE = "NET-001"
    FILE_NOT_FOUND = "FS-001"
    FILE_WRITE_FAILED = "FS-002"
    AUDIO_DEVICE_ERROR = "AUD-001"
    BACKEND_FAILURE = "BCK-001"
    INVALID_INPUT = "VAL-001"
    UNKNOWN = "UNK-001"


@dataclass(slots=True)
class KookieError(Exception):
    code: ErrorCode
    category: ErrorCategory
    message: str
    hint: str | None = None
    detail: str | None = None

    def __str__(self) -> str:
        return self.message


def classify_exception(exc: Exception) -> KookieError:
    if isinstance(exc, KookieError):
        return exc

    if isinstance(exc, URLError):
        return KookieError(
            code=ErrorCode.NETWORK_UNAVAILABLE,
            category=ErrorCategory.NETWORK,
            message=f"Network error: {exc.reason}",
            hint="Check your internet connection and try again.",
            detail=str(exc),
        )

    if isinstance(exc, FileNotFoundError):
        return KookieError(
            code=ErrorCode.FILE_NOT_FOUND,
            category=ErrorCategory.FILESYSTEM,
            message=str(exc) or "File not found.",
            hint="Verify the file path and permissions.",
            detail=str(exc),
        )

    if isinstance(exc, PermissionError):
        return KookieError(
            code=ErrorCode.FILE_WRITE_FAILED,
            category=ErrorCategory.FILESYSTEM,
            message=str(exc) or "Permission denied while accessing files.",
            hint="Grant write permission to the selected path and retry.",
            detail=str(exc),
        )

    if isinstance(exc, ValueError):
        return KookieError(
            code=ErrorCode.INVALID_INPUT,
            category=ErrorCategory.VALIDATION,
            message=str(exc) or "Invalid input.",
            hint="Adjust the input and try again.",
            detail=str(exc),
        )

    lowered = str(exc).lower()
    if "audio" in lowered or "device" in lowered:
        return KookieError(
            code=ErrorCode.AUDIO_DEVICE_ERROR,
            category=ErrorCategory.AUDIO_DEVICE,
            message=str(exc) or "Audio device error.",
            hint="Check output device availability and sample rate settings.",
            detail=str(exc),
        )

    return KookieError(
        code=ErrorCode.UNKNOWN,
        category=ErrorCategory.UNKNOWN,
        message=str(exc) or "Unexpected error.",
        hint="Try the operation again. If it keeps failing, collect logs and file an issue.",
        detail=str(exc),
    )


def to_user_message(error: KookieError) -> str:
    if error.hint:
        return f"{error.message} ({error.code.value}) Hint: {error.hint}"
    return f"{error.message} ({error.code.value})"
