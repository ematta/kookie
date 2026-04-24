# User Guide

## Install For Local Use

1. Open `chrome://extensions`.
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select the `extension/` folder from this repo.

## First Use

Open the Kookie popup and click `Assets` or press `Play` with text entered. Kookie downloads the Kokoro ONNX model and `af_sarah` voice on first use. This can take time depending on network speed.

## Read Text

- Paste or type text in the popup, then press `Play`.
- Select text on a page, right-click, then choose `Read with Kookie`.
- In the popup, click `Use Page Text` to import selected text or the page's main readable text.

## Playback Controls

- `Play`: starts reading the popup text.
- `Pause`: pauses after the current audio operation reaches a pause point.
- `Resume`: continues playback.
- `Stop`: stops the current read.
- `Rate`: clamps from `0.5x` to `2.0x`.
- `Volume`: clamps from `0%` to `100%`.

## Data And Privacy

- Text is processed locally in the extension.
- Model and voice assets are downloaded from Hugging Face.
- Large assets are stored in extension-owned IndexedDB.
- Settings and asset metadata are stored in `chrome.storage.local`.
