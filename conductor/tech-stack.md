# Tech Stack

## Programming Language
- **Python 3.12:** The core logic, text processing, and UI are built with Python 3.12, using  for modern dependency management and environment control.

## User Interface (UI)
- **Kivy:** A cross-platform framework used to create the macOS desktop interface, providing high performance and customizability for the editor and controls.

## Speech Synthesis (Backend)
- **Kokoro-ONNX:** A high-quality, local-first text-to-speech model.
- **ONNXRuntime:** Used to execute the Kokoro model locally, ensuring low-latency synthesis and absolute privacy.

## Audio Handling
- **Sounddevice:** Provides simple access to system audio for real-time playback of synthesized speech.
- **NumPy:** Handles audio data buffers and manipulation efficiently.

## Document Processing
- **PyMuPDF (fitz):** Used for robust text extraction from PDF files, allowing users to import documents for synthesis.

## Packaging & Deployment
- **PyInstaller:** Packages the Python application into a standalone macOS executable (`.app`).
- **macOS Notarization:** Custom shell scripts handle code signing, notarization with Apple, and DMG creation for secure distribution.

## Development & Quality Assurance
- **Testing:** `pytest` for unit, integration, and performance testing, with `hypothesis` for property-based testing and `pytest-cov` for tracking code coverage.
- **Linting & Formatting:** `ruff` is used for ultra-fast code linting and style enforcement.
- **Type Checking:** `mypy` provides static type checking to ensure code robustness.
