# Troubleshooting

## MP3 export fails

- Symptom: `ffmpeg is required to save MP3 files`
- Fix: install `ffmpeg` and verify it is on `PATH`.

## Assets fail to download

- Symptom: network-related startup errors (`NET-001`).
- Fix: verify connectivity and override model URLs if needed.

## No audio output

- Symptom: playback starts but no sound.
- Fix: check device output and sample-rate compatibility.

## PDF import has no text

- Symptom: `No extractable text found in PDF`.
- Fix: enable OCR fallback or use a text-based PDF.

## macOS says app cannot be verified

- Symptom: `Apple could not verify "Kookie" is free of malware...`.
- Cause: unsigned or unstapled app bundle distributed with quarantine metadata.
- Fix: for local testing, clear quarantine metadata:

```bash
xattr -dr com.apple.quarantine /path/to/Kookie.app
```

- Release fix: sign and notarize before distribution:
  - `scripts/sign_app.sh dist/Kookie.app "Developer ID Application: ..."`
  - `scripts/notarize_app.sh dist/Kookie.app <NOTARY_KEYCHAIN_PROFILE>`
