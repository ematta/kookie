# Contributing to Kookie

## Development workflow

1. Create a feature branch from `main`.
2. Add unit tests before implementation changes.
3. Run local checks:
   - `make test`
   - `make lint`
   - `make typecheck`
4. Open a pull request with a concise summary and test evidence.

## Pull request guidelines

- Keep PRs focused on one concern.
- Document behavior changes in `README.md` or `docs/`.
- Include screenshots for visible UI changes.
- For packaging changes, include build/test notes.

## Testing policy

- Use `@pytest.mark.unit` by default.
- Use `@pytest.mark.integration` for cross-module workflows.
- Use `@pytest.mark.perf` for regression guard tests.
