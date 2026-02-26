# Improvements to be made

This document provides a prioritized list of architectural and code-level improvements for the Kookie project. It is written as a set of actionable tasks for an LLM or a senior developer to execute.

---

## 1. UI Refactoring: Decouple Kivy Logic from Business Logic
**Issue:** `kookie/ui.py` is a 650-line "god file" containing the entire application layout, event handling, and Kivy lifecycle.
**Goal:** Improve maintainability and testability by separating concerns.

### Tasks:
- [ ] **Extract `KookieApp` class**: Move the `KookieApp` class and all its helper methods from `run_kivy_ui` into a new file `kookie/ui_app.py`.
- [ ] **Implement KV Language**: Move the UI layout definitions (currently in `build()`) into a Kivy `.kv` file or a multi-line string in `kookie/ui_layout.py` to separate the "view" from the "controller".
- [ ] **Create Theme Constants**: Move hardcoded colors and dimensions (e.g., `APP_BACKGROUND_COLOR`, `STATUS_BAR_HEIGHT`) from `kookie/ui.py` to a dedicated `kookie/theme.py`.
- [ ] **Mock UI for Testing**: Create a `tests/test_ui_logic.py` that uses a headless Kivy environment or mocks Kivy components to test `KookieApp` methods (like `_on_load_pdf`, `_on_play`) without launching a window.

---

## 2. Concurrency: Migrate `PlaybackController` to `asyncio`
**Issue:** Current manual thread management with `ThreadPoolExecutor` and `threading.Event` is prone to race conditions and hard to debug.
**Goal:** Use modern Python concurrency patterns for smoother audio-synthesis coordination.

### Tasks:
- [ ] **Refactor `PlaybackController`**: Rewrite the core logic in `kookie/controller.py` to use `asyncio`.
    - Use `asyncio.Queue` for audio chunks.
    - Use `asyncio.create_task` for synthesis and playback loops.
- [ ] **Integrate `asyncio` with Kivy**: Use `kivy.support.install_twisted_reactor` or `asyncio.run()` in a way that respects Kivy's main loop.
- [ ] **Simplify Stop/Pause Logic**: Replace manual `threading.Event` checks with `asyncio.Event` or task cancellation.

---

## 3. Performance: Audio Synthesis Caching
**Issue:** Every playback request re-synthesizes the entire text, even if it hasn't changed.
**Goal:** Reduce CPU usage and provide instant playback for repeated content.

### Tasks:
- [ ] **Create `AudioCache`**: Implement a simple disk-based cache in `kookie/cache.py` that stores synthesized audio chunks (indexed by hash of text + voice + speed).
- [ ] **Intercept Synthesis**: Update `PlaybackController._run_synthesis` to check the cache before calling the backend.
- [ ] **Implement Cache Eviction**: Add a simple size-based or age-based eviction policy to prevent the cache from growing indefinitely.

---

## 4. PDF Processing: Enhanced Extraction and OCR
**Issue:** Basic text extraction often loses structure (headings, lists) and fails on scanned PDFs.
**Goal:** Improve the quality of the "source material" for TTS.

### Tasks:
- [ ] **Integrate `docling`**: Add `docling` to `pyproject.toml` and implement structured text extraction in `kookie/pdf_import.py`.
- [ ] **Add OCR Fallback**: Detect when a PDF contains only images and offer (or automatically trigger) OCR using Tesseract or a similar library.
- [ ] **Progress Reporting**: Update `AppRuntime.load_pdf` to be a generator or accept a callback to report progress for multi-page/complex PDFs.

---

## 5. Testing: Infrastructure and Coverage
**Issue:** `kookie/ui.py` and `kookie/__main__.py` are excluded from coverage. Integration tests for "PDF -> Play -> Export" are missing.
**Goal:** Reach 90%+ coverage with meaningful functional tests.

### Tasks:
- [ ] **Add Integration Tests**: Create `tests/integration/test_full_workflow.py` that simulates loading a real PDF, starting playback, and verifying the exported MP3 (using `mock` backend).
- [ ] **Property-Based Testing**: Use `hypothesis` in `tests/test_text_processing.py` to verify that `normalize_text` and `split_sentences` handle arbitrary Unicode input without crashing.
- [ ] **Mock Audio Device**: Enhance `tests/test_audio.py` to verify that `AudioPlayer` correctly interacts with `sounddevice` without requiring a physical sound card.

---

## 6. Developer Experience: CI/CD and Tooling
**Issue:** Project relies on manual scripts for building and testing.
**Goal:** Automate everything.

### Tasks:
- [ ] **GitHub Actions**: Create `.github/workflows/ci.yml` to run `ruff`, `mypy`, and `pytest` on every push.
- [ ] **Automated DMG Build**: Add a GitHub Action to run `scripts/build_app.sh` and `scripts/create_dmg.sh` for tagged releases.
- [ ] **Pre-commit Hooks**: Update `.pre-commit-config.yaml` to include `ruff` and `mypy`.

---

## 7. Configuration & State Management
**Issue:** `AppRuntime` handles too many responsibilities.
**Goal:** Decouple state from logic.

### Tasks:
- [ ] **Refactor `AppRuntime`**: Move configuration validation and defaults to `kookie/config.py` using `pydantic`.
- [ ] **Event-Driven State**: Implement a simple observer pattern or use Kivy's `EventDispatcher` so the UI updates automatically when `AppRuntime` state changes, instead of polling in `_sync_now`.
