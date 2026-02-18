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

## Input behavior

- Playback always uses the current contents of the text area.
- You can type directly in the text area.
- Paste directly into the text area with `Cmd+V`.
- Use `Save MP3` to export synthesized speech to `~/Downloads/kookie-<timestamp>.mp3`.

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

## Packaging

```bash
scripts/build_app.sh
scripts/sign_app.sh dist/Kookie.app "Developer ID Application: Your Name"
scripts/notarize_app.sh dist/Kookie.app "AC_PASSWORD"
```

## Tests

```bash
pytest
```

If dependencies are unavailable in the current environment, install the dev extras first.
