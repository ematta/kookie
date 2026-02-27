# Initial Concept
Local-first macOS desktop text-to-speech app using Kivy and Kokoro.

# Product Guide

## Vision
Kookie is a privacy-first, local-first macOS desktop application designed to provide high-quality text-to-speech (TTS) synthesis without any cloud dependencies. By leveraging the Kokoro-ONNX model, it ensures that all processing happens on the user's machine, guaranteeing absolute privacy and offline availability.

## Target Audience
- **Privacy-conscious users:** Individuals who prioritize local data processing and want to avoid sending text or audio to external servers.
- **Content creators:** Users needing a quick and reliable way to generate voiceovers or listen to long-form text locally.
- **MacOS Users:** Desktop users who want a native-feeling tool that integrates seamlessly with their existing workflows.

## Core Goals
- **Local-first & Offline-ready:** Kookie's primary mission is to function entirely offline, with all models and voices stored locally.
- **Low-latency Performance:** Ensuring that text synthesis and playback feel instantaneous and responsive.
- **Ease of Use:** Providing a simple, intuitive interface for importing text (via PDF or direct input) and managing high-quality audio output.

## Key Features
- **TTS Synthesis:** High-quality local voice generation using the Kokoro model.
- **PDF Import:** Direct text extraction from PDF files for immediate playback.
- **Audio Export:** Options to save synthesized speech as high-quality MP3 and WAV files.
- **Editor Customization:** User-selectable fonts, sizes, and word wrap preferences that persist across sessions.

## Future Scope
- **OCR Capabilities:** Support for reading from scanned PDFs and images, expanding the utility for diverse input sources.
- **Multilingual Support:** Broadening the language base beyond English and Spanish.
- **Advanced Audio Controls:** More granular control over synthesis parameters and output formatting.
