#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <APP_PATH> <SIGNING_IDENTITY>"
  exit 1
fi

APP_PATH="$1"
SIGNING_IDENTITY="$2"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTITLEMENTS="$ROOT_DIR/packaging/entitlements.plist"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found: $APP_PATH"
  exit 1
fi

# Remove quarantine metadata to avoid Gatekeeper warnings on locally-distributed builds.
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true

if [[ -d "$APP_PATH/Contents/Frameworks" ]]; then
  find "$APP_PATH/Contents/Frameworks" -type f \( -name "*.dylib" -o -perm -111 \) -print0 | while IFS= read -r -d '' file; do
    codesign --force --timestamp --sign "$SIGNING_IDENTITY" "$file"
  done
fi

codesign \
  --force \
  --timestamp \
  --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$SIGNING_IDENTITY" \
  "$APP_PATH"

codesign --verify --deep --strict --verbose=4 "$APP_PATH"
