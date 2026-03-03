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


def test_classify_exception_maps_permission_errors() -> None:
    error = classify_exception(PermissionError("access denied"))

    assert error.category is ErrorCategory.FILESYSTEM
    assert error.code is ErrorCode.FILE_WRITE_FAILED


def test_classify_exception_maps_value_errors() -> None:
    error = classify_exception(ValueError("bad input"))

    assert error.category is ErrorCategory.VALIDATION
    assert error.code is ErrorCode.INVALID_INPUT


def test_classify_exception_maps_audio_keyword_heuristic() -> None:
    error = classify_exception(RuntimeError("audio device not found"))

    assert error.category is ErrorCategory.AUDIO_DEVICE
    assert error.code is ErrorCode.AUDIO_DEVICE_ERROR


def test_classify_exception_maps_generic_fallback() -> None:
    error = classify_exception(RuntimeError("something unexpected happened"))

    assert error.category is ErrorCategory.UNKNOWN
    assert error.code is ErrorCode.UNKNOWN


def test_classify_exception_passthrough_kookie_error() -> None:
    original = KookieError(
        code=ErrorCode.BACKEND_FAILURE,
        category=ErrorCategory.BACKEND,
        message="backend crashed",
    )

    assert classify_exception(original) is original


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
