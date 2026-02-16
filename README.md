# Kookie

Local-first macOS desktop text-to-speech app using Kivy and Kokoro.

## Run (development)

```bash
python main.py
```

## Environment configuration

- `KOOKIE_BACKEND_MODE`: `auto` (default), `mock`, `real`
- `KOOKIE_ASSET_DIR`: directory for `kokoro-v0_19.onnx` and `voices.bin`
- `KOOKIE_MODEL_URL`: override default model download URL
- `KOOKIE_VOICES_URL`: override default voices download URL
- `KOOKIE_MODEL_SHA256`: optional checksum for model file
- `KOOKIE_VOICES_SHA256`: optional checksum for voices file
- `KOOKIE_DEFAULT_VOICE`: default `af_sarah`
- `KOOKIE_SAMPLE_RATE`: default `24000`
- `KOOKIE_CLIPBOARD_POLL_INTERVAL`: default `0.5`
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
