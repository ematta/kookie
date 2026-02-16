#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$ROOT_DIR/.pyinstaller}"
export KIVY_HOME="${KIVY_HOME:-$ROOT_DIR/.kivy}"

mkdir -p "$UV_CACHE_DIR" "$PYINSTALLER_CONFIG_DIR" "$KIVY_HOME/logs"

uv run pyinstaller packaging/kookie.spec --noconfirm --clean
