from __future__ import annotations

from urllib.error import URLError

from kookie.errors import ErrorCategory, ErrorCode, KookieError, classify_exception, to_user_message


def test_classify_exception_maps_network_errors() -> None:
    error = classify_exception(URLError("offline"))

    assert error.category is ErrorCategory.NETWORK
    assert error.code is ErrorCode.NETWORK_UNAVAILABLE


def test_classify_exception_maps_filesystem_errors() -> None:
    error = classify_exception(FileNotFoundError("missing file"))

    assert error.category is ErrorCategory.FILESYSTEM
    assert error.code is ErrorCode.FILE_NOT_FOUND


def test_to_user_message_includes_actionable_hint() -> None:
    message = to_user_message(
        KookieError(
            code=ErrorCode.AUDIO_DEVICE_ERROR,
            category=ErrorCategory.AUDIO_DEVICE,
            message="device unavailable",
            hint="Check output device selection.",
        )
    )

    assert "device unavailable" in message
    assert "Check output device selection." in message
