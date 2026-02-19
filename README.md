# Kookie

Local-first macOS desktop text-to-speech app using Kivy and Kokoro.

## Run (development)

```bash
python main.py
```

## Preload voice

```bash
scripts/preload_voice.sh
```

This pre-load step checks for `voices.bin` in `KOOKIE_ASSET_DIR` (or the default assets path) and downloads it if missing.

### Preload 404 troubleshooting

If preload fails with:

`Voice preload failed: failed to download voices: HTTP Error 404: Not Found`

the default voice URL is likely stale. Override the model and voice URLs before running preload:

```bash
export KOOKIE_MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
export KOOKIE_VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
scripts/preload_voice.sh
```

## Status bar

The UI includes a status bar with three fields:

- `Voice: ...` (first field, availability of `voices.bin`)
- `Backend: ...` (active backend mode)
- `State: ...` (runtime playback/activity state)
- `Progress: ...` and `Recent: ...` rows for playback/export context

## Input behavior

- Playback always uses the current contents of the text area.
- You can type directly in the text area.
- Paste directly into the text area with `Cmd+V`.
- The editor starts at `20 pt` text with word wrap enabled.
- Use the font picker and size picker above the editor to customize readability.
- Use the `Word Wrap` toggle to switch between wrapped and horizontal-scroll editing.
- The editor shows a right-side scrollbar for long text.
- Font, size, and wrap preferences persist across app launches in `~/Library/Application Support/Kookie/editor_prefs.json`.
- Use `Load PDF` to import text from a `.pdf` file into the editor.
- Loading a PDF replaces existing text in the editor.
- Use `Save MP3` to export synthesized speech to `~/Downloads/kookie-<timestamp>.mp3`.
- PDF import currently supports text-based PDFs only (no OCR for scanned/image-only pages).
- Playback supports pause/resume, seek requests, volume control, and speed presets (`0.5x`, `1.0x`, `1.5x`, `2.0x`).
- Use keyboard shortcuts:
  - `Cmd/Ctrl+O`: load PDF
  - `Cmd/Ctrl+P`: play
  - `Cmd/Ctrl+S`: save MP3
  - `Cmd/Ctrl+Z`: undo
  - `Cmd/Ctrl+Shift+Z`: redo

MP3 export shells out to `ffmpeg`; install it if you want to use `Save MP3`.

## Environment configuration

- `KOOKIE_BACKEND_MODE`: `auto` (default), `mock`, `real`
- `KOOKIE_ASSET_DIR`: directory for `kokoro-v0_19.onnx` and `voices.bin`
- `KOOKIE_MODEL_URL`: override default model download URL
- `KOOKIE_VOICES_URL`: override default voices download URL
- `KOOKIE_MODEL_SHA256`: optional checksum for model file
- `KOOKIE_VOICES_SHA256`: optional checksum for voices file
- `KOOKIE_DEFAULT_VOICE`: default `af_sarah`
- `KOOKIE_SAMPLE_RATE`: default `24000`
- `KOOKIE_DOWNLOAD_TIMEOUT`: default `30`
- `KOOKIE_CONFIG_FILE`: optional TOML config file path
- `KOOKIE_LANGUAGE`: `en` or `es`
- `KOOKIE_THEME`: `system`, `light`, `dark`
- `KOOKIE_HIGH_CONTRAST`: accessibility high-contrast mode toggle
- `KOOKIE_TELEMETRY_ENABLED`: local opt-in telemetry (`false` by default)
- `KOOKIE_UPDATE_CHECK_ENABLED`: check-only update prompt toggle
- `KOOKIE_UPDATE_REPO`: GitHub repo used by update checks (default `ematta/kookie`)
- `KOOKIE_HEALTH_CHECK_ENABLED`: enables local `/health` and `/metrics` endpoint
- `KOOKIE_HEALTH_CHECK_HOST` / `KOOKIE_HEALTH_CHECK_PORT`: health endpoint bind config
- `KOOKIE_REQUIRE_ASSET_CHECKSUMS`: enforce checksum presence before trusting assets
- `KOOKIE_ASSET_AUTO_UPDATE`: auto-refresh assets when tracked versions change

## Packaging

```bash
scripts/build_app.sh
scripts/sign_app.sh dist/Kookie.app "Developer ID Application: Your Name"
xcrun notarytool store-credentials KOOKIE_NOTARY --apple-id "<APPLE_ID>" --team-id "<TEAM_ID>" --password "<APP_SPECIFIC_PASSWORD>"
scripts/notarize_app.sh dist/Kookie.app KOOKIE_NOTARY
scripts/create_dmg.sh dist/Kookie.app
```

## Tests

```bash
uv run pytest -q
```

If dependencies are unavailable in the current environment, install the dev extras first.
