# Contributing to Kookie

## Development Workflow

1. Create a feature branch from `main`.
2. Add or update unit tests before implementation changes.
3. Run local checks:
   - `make vendor`
   - `make test`
4. For UI changes, load `extension/` unpacked in Chrome and manually exercise the popup and context menu.
5. Open a pull request with a concise summary and test evidence.

## Testing Policy

- Use Node's built-in test runner.
- Keep Chrome APIs behind small seams and use hand-written fakes in unit tests.
- Add integration/manual verification notes for behavior that requires Chrome extension runtime APIs.

## Dependency Policy

- Keep runtime dependencies narrow.
- `onnxruntime-web` is intentionally allowed for browser-side Kokoro inference.
- Avoid UI frameworks unless a specific feature justifies the added weight.
