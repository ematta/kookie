from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sign_script_clears_quarantine_and_verifies_bundle() -> None:
    script = (ROOT / "scripts" / "sign_app.sh").read_text(encoding="utf-8")

    assert "xattr -dr com.apple.quarantine" in script
    assert "codesign --verify --deep --strict" in script


def test_notarize_script_validates_staple_and_gatekeeper() -> None:
    script = (ROOT / "scripts" / "notarize_app.sh").read_text(encoding="utf-8")

    assert "xcrun notarytool submit" in script
    assert "xcrun stapler staple" in script
    assert "xcrun stapler validate" in script
    assert "spctl --assess --type execute" in script


def test_release_workflow_supports_sign_and_notarize() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "Prepare signing keychain" in workflow
    assert "scripts/sign_app.sh dist/Kookie.app" in workflow
    assert "scripts/notarize_app.sh dist/Kookie.app" in workflow
    assert "MACOS_CERTIFICATE_P12: ${{ secrets.MACOS_CERTIFICATE_P12 }}" in workflow
    assert "MACOS_CERTIFICATE_PASSWORD: ${{ secrets.MACOS_CERTIFICATE_PASSWORD }}" in workflow
    assert "MACOS_SIGNING_IDENTITY: ${{ secrets.MACOS_SIGNING_IDENTITY }}" in workflow
    assert "APPLE_ID: ${{ secrets.APPLE_ID }}" in workflow
    assert "APPLE_APP_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}" in workflow
    assert "APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}" in workflow
    assert "if: ${{ env.MACOS_CERTIFICATE_P12 != ''" in workflow
    assert "if: ${{ env.APPLE_ID != ''" in workflow
    assert "if: ${{ secrets." not in workflow
