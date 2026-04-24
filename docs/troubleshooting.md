# Troubleshooting

## Extension Does Not Load

- Confirm `npm --prefix extension run vendor` has created `extension/vendor/onnxruntime-web/ort.wasm.bundle.min.mjs`.
- Open `chrome://extensions`, enable Developer mode, and select the `extension/` directory, not the repo root.
- Check the extension service worker console from `chrome://extensions`.

## Assets Do Not Download

- Confirm network access to `https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/`.
- Click `Assets` in the popup to retry.
- In Chrome DevTools, inspect extension storage and IndexedDB for `kookie-assets`.

## No Audio Plays

- Confirm Chrome can play audio from other tabs.
- Click inside the popup and press `Play` after entering text so Chrome sees a user gesture.
- Check the offscreen document logs from the extension inspection tools.

## Page Text Import Is Empty

- Some Chrome pages and restricted URLs do not allow extension script injection.
- Try selecting text manually and using the context menu.
- Confirm the active tab is a normal `http` or `https` page.

## Speech Sounds Wrong

The current implementation intentionally avoids a larger phonemizer dependency and uses a compact tokenizer map. If speech quality regresses, validate the tokenizer and Kokoro tensor inputs before changing playback code.
