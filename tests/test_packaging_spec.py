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
        "collect_data_files",
        "collect_dynamic_libs",
        "collect_submodules",
        "pymupdf",
        "ffmpeg",
        "scipy.special.cython_special",
        "sklearn.utils._typedefs",
    ]

    for token in required_tokens:
        assert token in contents


def test_pyinstaller_spec_supports_optional_dynamic_import_packages() -> None:
    spec_path = ROOT / "packaging" / "kookie.spec"
    contents = spec_path.read_text(encoding="utf-8")

    assert "optional_hidden_imports" in contents
    assert "optional_package_submodules" in contents
    assert 'optional_package_binaries("pymupdf")' in contents
    assert '"fitz"' in contents


def test_pyinstaller_spec_supports_optional_system_ffmpeg_binary() -> None:
    spec_path = ROOT / "packaging" / "kookie.spec"
    contents = spec_path.read_text(encoding="utf-8")

    assert "optional_system_binary" in contents
    assert 'optional_system_binary("ffmpeg")' in contents


def test_pyinstaller_spec_does_not_depend_on___file__() -> None:
    spec_path = ROOT / "packaging" / "kookie.spec"
    contents = spec_path.read_text(encoding="utf-8")

    assert "__file__" not in contents
    assert "SPECPATH" in contents


def test_pyinstaller_spec_supports_optional_model_assets() -> None:
    spec_path = ROOT / "packaging" / "kookie.spec"
    contents = spec_path.read_text(encoding="utf-8")

    assert "exists()" in contents
    assert "Skipping missing asset during packaging" in contents


def test_pyinstaller_spec_uses_project_png_icon_for_app_bundle() -> None:
    spec_path = ROOT / "packaging" / "kookie.spec"
    contents = spec_path.read_text(encoding="utf-8")

    assert 'app_icon_rel = "kookie.png"' in contents
    assert 'optional_data(app_icon_rel, ".")' in contents
    assert "icon=str(project_root / app_icon_rel)" in contents


def test_entitlements_include_required_hardened_runtime_exceptions() -> None:
    entitlements_path = ROOT / "packaging" / "entitlements.plist"
    with entitlements_path.open("rb") as fh:
        data = plistlib.load(fh)

    assert data["com.apple.security.cs.allow-jit"] is True
    assert data["com.apple.security.cs.allow-unsigned-executable-memory"] is True
    assert data["com.apple.security.cs.disable-library-validation"] is True
