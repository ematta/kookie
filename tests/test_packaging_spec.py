from pathlib import Path
import plistlib


ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_spec_contains_required_assets_and_hooks() -> None:
    spec_path = ROOT / "packaging" / "kookie.spec"
    contents = spec_path.read_text(encoding="utf-8")

    required_tokens = [
        "libs/libespeak-ng.dylib",
        "libs/espeak-ng-data",
        "assets/kokoro-v0_19.onnx",
        "assets/voices.bin",
        "scipy.special.cython_special",
        "sklearn.utils._typedefs",
    ]

    for token in required_tokens:
        assert token in contents


def test_entitlements_include_required_hardened_runtime_exceptions() -> None:
    entitlements_path = ROOT / "packaging" / "entitlements.plist"
    with entitlements_path.open("rb") as fh:
        data = plistlib.load(fh)

    assert data["com.apple.security.cs.allow-jit"] is True
    assert data["com.apple.security.cs.allow-unsigned-executable-memory"] is True
    assert data["com.apple.security.cs.disable-library-validation"] is True
