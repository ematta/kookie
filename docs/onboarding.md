# Developer Onboarding

## Prerequisites

- Chrome 116 or newer
- Node.js 22 or newer
- npm

## First Run

```bash
npm --prefix extension install
npm --prefix extension run vendor
npm --prefix extension test
```

Then load the extension:

1. Open `chrome://extensions`.
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select the repo's `extension/` directory.

## Useful Commands

- `make install`: install extension dependencies.
- `make vendor`: copy the ONNX Runtime browser bundle into `extension/vendor/`.
- `make test`: run Node unit tests.
- `make package`: create `dist/kookie-extension.zip`.
- `make check`: run vendor copy and tests.

## Manual Smoke Test

1. Open any readable web page.
2. Select a paragraph.
3. Right-click and choose `Read with Kookie`.
4. Confirm first-run assets download.
5. Confirm audio starts, then use the popup to pause, resume, stop, and adjust rate/volume.
