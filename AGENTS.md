# AGENTS

This file self-updates via `python -m kookie.agents_updater`.
Only edit content outside the auto-generated section markers.

## Working Agreement
- Start with unit tests before implementation changes.
- Prefer simple, local dependencies and efficient implementations.
- Keep sections concise and actionable.

<!-- BEGIN AUTO -->
## Auto-Generated Snapshot
- Last updated (UTC): `2026-02-17T20:10:41Z`
- Project: `kookie`
- Version: `0.1.0`
- Python: `>=3.12,<3.13`

### Console Scripts
- `uv run kookie` -> `kookie.__main__:main`
- `uv run kookie-preload-voice` -> `kookie.preload:main`
- `uv run kookie-update-agents` -> `kookie.agents_updater:main`

### Dependencies
- `kivy>=2.3.0`
- `kokoro-onnx>=0.4.0`
- `numpy>=2.0.0`
- `onnxruntime>=1.18.0`
- `pyinstaller>=6.19.0`
- `sounddevice>=0.4.7`

### Top-Level Directories
- `assets/`
- `kookie/`
- `libs/`
- `packaging/`
- `scripts/`
- `tests/`
<!-- END AUTO -->
