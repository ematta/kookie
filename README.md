# Kookie

Kookie is a local-first Chrome extension that reads selected, pasted, or page text aloud with browser-side Kokoro ONNX inference.

The repository is now extension-only. The retired desktop app and native packaging paths have been removed.

## Requirements

- Chrome 116 or newer
- Node.js 22 or newer
- npm

## Build And Test

```bash
npm --prefix extension install
npm --prefix extension run vendor
npm --prefix extension test
```

`npm run vendor` copies the small browser ONNX Runtime bundle from `node_modules` into `extension/vendor/` so Chrome can load it from the extension package.

## Run Locally

1. Open `chrome://extensions`.
2. Enable `Developer mode`.
3. Select `Load unpacked`.
4. Choose this repo's `extension/` directory.
5. Pin Kookie from Chrome's extension menu if you want quick access.

## Use Kookie

- Open the Kookie popup and paste or type text.
- Select text on a page, open the context menu, and choose `Read with Kookie`.
- Use `Use Page Text` in the popup to import the current selection or readable page text.
- Press `Play`, `Pause`, `Resume`, or `Stop`.
- Adjust voice, rate, and volume from the popup. Settings persist in `chrome.storage.local`.

On first use, Kookie downloads the Kokoro ONNX model and the `af_sarah` voice from Hugging Face. Large asset bytes are stored in extension-owned IndexedDB; only metadata is stored in Chrome storage.

## Package For Manual Distribution

```bash
npm --prefix extension run package
```

The package command writes a loadable zip to `dist/kookie-extension.zip`. It excludes `node_modules` and test files.

## Project Layout

- `extension/manifest.json`: Chrome Manifest V3 declaration.
- `extension/src/serviceWorker.js`: message routing, context menu, settings, asset orchestration, offscreen lifecycle.
- `extension/src/offscreen.js`: hidden playback host for ONNX inference and Web Audio.
- `extension/src/kokoroBackend.js`: Kokoro ONNX wrapper.
- `extension/src/assetManager.js`: asset download, checksum validation, IndexedDB byte storage.
- `extension/src/playbackController.js`: playback state machine.
- `extension/src/popup.*`: reader popup UI.
- `extension/test/`: Node unit tests.

## Known Limits

- The current browser Kokoro path uses a small in-repo tokenizer map to avoid adding a phonemizer dependency. Validate speech quality manually after changes.
- Document import and audio file export are not part of the extension-only app.
