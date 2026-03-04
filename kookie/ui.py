from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .controller import PlaybackState
from .editor_prefs import (
    CURATED_FONT_NAMES,
    EDITOR_FONT_SIZES,
    EditorPreferences,
    load_editor_preferences,
    sanitize_editor_preferences,
    save_editor_preferences,
)

TEXT_FOREGROUND_COLOR = (0.10, 0.12, 0.15, 1.0)
TEXT_BACKGROUND_COLOR = (0.96, 0.97, 0.98, 1.0)
TEXT_SELECTION_COLOR = (0.70, 0.82, 0.98, 0.70)
TEXT_CURSOR_COLOR = (0.17, 0.40, 0.85, 1.0)
SAVE_SPINNER_FRAMES = ("|", "/", "-", "\\")
LOAD_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
APP_BACKGROUND_COLOR = (0.08, 0.09, 0.12, 1.0)
TOOLBAR_BACKGROUND_COLOR = (0.13, 0.15, 0.20, 1.0)
CONTROL_SURFACE_COLOR = (0.22, 0.25, 0.32, 1.0)
PRIMARY_BUTTON_COLOR = (0.24, 0.56, 0.82, 1.0)
SUCCESS_BUTTON_COLOR = (0.20, 0.60, 0.42, 1.0)
DANGER_BUTTON_COLOR = (0.78, 0.28, 0.28, 1.0)
CONTROL_TEXT_COLOR = (0.96, 0.98, 1.0, 1.0)
STATUS_TEXT_COLOR = (0.78, 0.82, 0.90, 1.0)
CONTROL_FONT_SIZE = 20
STATUS_FONT_SIZE = 17
URL_INPUT_FONT_SIZE = 18
STATUS_VOICE_MAX_CHARS = 24
STATUS_BACKEND_MAX_CHARS = 28
STATUS_ACTIVITY_MAX_CHARS = 72
APP_ICON_FILENAME = "kookie.png"
STATUS_HEADER_HEIGHT = 44
STATUS_ACTIVITY_ROW_MIN_HEIGHT = 44
STATUS_PROGRESS_ROW_MIN_HEIGHT = 44
STATUS_RECENT_ROW_MIN_HEIGHT = 44
STATUS_BAR_ROW_SPACING = 8
STATUS_BAR_PADDING = (16, 12, 16, 12)
STATUS_BAR_VERTICAL_PADDING = STATUS_BAR_PADDING[1] + STATUS_BAR_PADDING[3]
STATUS_BAR_HEIGHT = (
    STATUS_HEADER_HEIGHT
    + STATUS_ACTIVITY_ROW_MIN_HEIGHT
    + STATUS_PROGRESS_ROW_MIN_HEIGHT
    + STATUS_RECENT_ROW_MIN_HEIGHT
    + (STATUS_BAR_ROW_SPACING * 3)
    + STATUS_BAR_VERTICAL_PADDING
)
NATIVE_OPEN_FILE_TYPES = (("PDF files", "*.pdf"), ("All files", "*.*"))
NATIVE_SAVE_FILE_TYPES = (("MP3 files", "*.mp3"), ("All files", "*.*"))


def _rgba_to_css(color: tuple[float, float, float, float]) -> str:
    r, g, b, a = color
    return f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, {a:.2f})"


def _text_input_config(initial_text: str, *, prefs: EditorPreferences) -> dict[str, object]:
    return {
        "text": initial_text,
        "readonly": False,
        "font_family": prefs.font_name,
        "font_size": prefs.font_size,
        "word_wrap": prefs.word_wrap,
        "accept_tab": True,
        "foreground_color": TEXT_FOREGROUND_COLOR,
        "background_color": TEXT_BACKGROUND_COLOR,
        "selection_color": TEXT_SELECTION_COLOR,
        "cursor_color": TEXT_CURSOR_COLOR,
        "padding": [16, 16, 16, 16],
    }


def _scroll_view_config(word_wrap: bool) -> dict[str, object]:
    return {
        "word_wrap": word_wrap,
        "vertical_scrollbar": True,
        "horizontal_scrollbar": not word_wrap,
    }


def _save_spinner_text(*, is_saving: bool, tick: int) -> str:
    if not is_saving:
        return ""

    frame = SAVE_SPINNER_FRAMES[tick % len(SAVE_SPINNER_FRAMES)]
    return f"Saving MP3 {frame}"


def _load_spinner_text(*, is_loading: bool, tick: int) -> str:
    if not is_loading:
        return ""

    frame = LOAD_SPINNER_FRAMES[tick % len(LOAD_SPINNER_FRAMES)]
    return f"Loading PDF {frame}"


def _shorten_middle(text: str, *, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]

    head_count = (max_chars - 3) // 2
    tail_count = max_chars - 3 - head_count
    return f"{text[:head_count]}...{text[-tail_count:]}"


def _status_display_items(items: list[str]) -> tuple[str, str, str]:
    voice = items[0] if items else ""
    backend = items[1] if len(items) > 1 else ""
    activity = items[2] if len(items) > 2 else ""
    return (
        _shorten_middle(voice, max_chars=STATUS_VOICE_MAX_CHARS),
        _shorten_middle(backend, max_chars=STATUS_BACKEND_MAX_CHARS),
        _shorten_middle(activity, max_chars=STATUS_ACTIVITY_MAX_CHARS),
    )


def _status_label_config() -> dict[str, object]:
    return {
        "alignment": "left",
        "vertical_alignment": "center",
        "elide": True,
        "elide_mode": "middle",
        "max_lines": 1,
        "color": STATUS_TEXT_COLOR,
        "font_size": STATUS_FONT_SIZE,
    }


def _runtime_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[arg-type]
    return Path(__file__).resolve().parents[1]


def _app_icon_path(*, runtime_base: Path | None = None) -> str | None:
    base = runtime_base if runtime_base is not None else _runtime_base_path()
    icon_path = base / APP_ICON_FILENAME
    if icon_path.exists():
        return str(icon_path)
    return None


def _control_style(*, background_color: tuple[float, float, float, float]) -> str:
    bg = _rgba_to_css(background_color)
    fg = _rgba_to_css(CONTROL_TEXT_COLOR)
    return (
        f"background-color: {bg}; color: {fg}; font-size: {CONTROL_FONT_SIZE}px; "
        "border: none; border-radius: 4px; padding: 6px 10px;"
    )


def _resolve_native_dialog_bindings() -> tuple[Callable[[], Any], Callable[..., str], Callable[..., str]]:
    try:
        from tkinter import Tk
        from tkinter.filedialog import askopenfilename, asksaveasfilename
    except Exception as exc:  # pragma: no cover - depends on local GUI deps
        raise RuntimeError("Native file dialogs are unavailable in this Python environment.") from exc

    return Tk, askopenfilename, asksaveasfilename


def _apple_script_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _allowed_file_types(filetypes: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    extensions: list[str] = []
    for _label, pattern in filetypes:
        for raw_glob in pattern.split(";"):
            glob = raw_glob.strip()
            if not glob.startswith("*."):
                continue
            extension = glob[2:].strip().lower()
            if not extension or extension == "*":
                continue
            if extension not in extensions:
                extensions.append(extension)
    return tuple(extensions)


def _build_macos_dialog_script(
    *,
    mode: str,
    title: str,
    initial_dir: Path,
    filetypes: tuple[tuple[str, str], ...],
    initial_file: str | None = None,
) -> str:
    script_lines = [
        f"set _defaultLocation to POSIX file {_apple_script_string(str(initial_dir))}",
    ]
    if mode == "open":
        open_line = (
            f"set _pickedFile to choose file with prompt {_apple_script_string(title)} "
            "default location _defaultLocation"
        )
        allowed_types = _allowed_file_types(filetypes)
        if allowed_types:
            types_literal = ", ".join(_apple_script_string(value) for value in allowed_types)
            open_line += f" of type {{{types_literal}}}"
        script_lines.append(open_line)
    else:
        save_line = (
            f"set _pickedFile to choose file name with prompt {_apple_script_string(title)} "
            "default location _defaultLocation"
        )
        if initial_file:
            save_line += f" default name {_apple_script_string(initial_file)}"
        script_lines.append(save_line)
    script_lines.append("POSIX path of _pickedFile")
    return "\n".join(script_lines)


def _dialog_selection_to_path(selection: str | Path | None) -> Path | None:
    if selection is None:
        return None

    if isinstance(selection, Path):
        selected = selection
    elif isinstance(selection, str):
        stripped = selection.strip()
        if not stripped:
            return None
        selected = Path(stripped)
    else:
        return None

    return selected.expanduser()


def _native_file_dialog(
    *,
    mode: str,
    title: str,
    initial_dir: Path,
    filetypes: tuple[tuple[str, str], ...],
    initial_file: str | None = None,
    default_extension: str | None = None,
    tk_factory: Callable[[], Any] | None = None,
    askopenfilename: Callable[..., str] | None = None,
    asksaveasfilename: Callable[..., str] | None = None,
    platform_name: str | None = None,
    osascript_runner: Callable[..., Any] | None = None,
) -> Path | None:
    if mode not in {"open", "save"}:
        raise ValueError("mode must be 'open' or 'save'")

    selected_platform = platform_name or sys.platform
    if selected_platform == "darwin":
        run = osascript_runner or subprocess.run
        script = _build_macos_dialog_script(
            mode=mode,
            title=title,
            initial_dir=initial_dir,
            filetypes=filetypes,
            initial_file=initial_file,
        )
        try:
            completed = run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr_lower = (exc.stderr or "").lower()
            if "(-128)" in stderr_lower or "cancel" in stderr_lower:
                return None
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise RuntimeError(f"Native file dialog failed: {detail}") from exc

        return _dialog_selection_to_path(getattr(completed, "stdout", None))

    if tk_factory is None or askopenfilename is None or asksaveasfilename is None:
        default_factory, default_open, default_save = _resolve_native_dialog_bindings()
        if tk_factory is None:
            tk_factory = default_factory
        if askopenfilename is None:
            askopenfilename = default_open
        if asksaveasfilename is None:
            asksaveasfilename = default_save

    root = tk_factory()
    try:
        if hasattr(root, "withdraw"):
            root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass

        dialog_kwargs: dict[str, object] = {
            "title": title,
            "initialdir": str(initial_dir),
            "filetypes": filetypes,
            "parent": root,
        }
        if mode == "open":
            selection = askopenfilename(**dialog_kwargs)
        else:
            if initial_file is not None:
                dialog_kwargs["initialfile"] = initial_file
            if default_extension is not None:
                dialog_kwargs["defaultextension"] = default_extension
            selection = asksaveasfilename(**dialog_kwargs)
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    return _dialog_selection_to_path(selection)


def _default_dialog_dir(*, home_dir: Path | None = None) -> Path:
    selected_home = home_dir or Path.home()
    downloads_dir = selected_home / "Downloads"
    if downloads_dir.exists() and downloads_dir.is_dir():
        return downloads_dir
    return selected_home


def _default_mp3_filename(*, now: datetime | None = None) -> str:
    selected_now = now or datetime.now()
    return f"kookie-{selected_now.strftime('%Y%m%d-%H%M%S')}.mp3"


def _update_recent_files(items: list[str], path: str, *, max_items: int = 8) -> list[str]:
    cleaned_path = path.strip()
    if not cleaned_path:
        return list(items)
    next_items = [cleaned_path]
    for item in items:
        if item == cleaned_path:
            continue
        next_items.append(item)
        if len(next_items) >= max_items:
            break
    return next_items


def detect_system_dark_mode(
    *,
    platform_name: str | None = None,
    runner: Callable[..., Any] | None = None,
) -> bool:
    selected_platform = platform_name or sys.platform
    if selected_platform != "darwin":
        return False

    selected_runner = runner or subprocess.run
    script = 'tell application "System Events" to tell appearance preferences to return dark mode'
    try:
        completed = selected_runner(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return False
    return str(getattr(completed, "stdout", "")).strip().lower() == "true"


def _prompt_pdf_path(
    *,
    dialog: Callable[..., Path | None] = _native_file_dialog,
    home_dir: Path | None = None,
) -> Path | None:
    return dialog(
        mode="open",
        title="Load PDF",
        initial_dir=home_dir or Path.home(),
        filetypes=NATIVE_OPEN_FILE_TYPES,
    )


def _prompt_mp3_output_path(
    *,
    dialog: Callable[..., Path | None] = _native_file_dialog,
    home_dir: Path | None = None,
    now: datetime | None = None,
) -> Path | None:
    selected_output = dialog(
        mode="save",
        title="Save MP3",
        initial_dir=_default_dialog_dir(home_dir=home_dir),
        filetypes=NATIVE_SAVE_FILE_TYPES,
        initial_file=_default_mp3_filename(now=now),
        default_extension=".mp3",
    )
    if selected_output is None:
        return None

    if selected_output.suffix.lower() != ".mp3":
        return selected_output.with_suffix(".mp3")
    return selected_output


def run_pyqt_ui(runtime, startup_prompt: dict[str, object] | None = None) -> str | None:
    try:
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut
        from PyQt6.QtWidgets import (
            QApplication,
            QComboBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QPushButton,
            QSlider,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except Exception as exc:  # pragma: no cover - depends on local GUI deps
        raise RuntimeError("PyQt6 is required to run the graphical application") from exc

    from .i18n import get_translator

    def _button_stylesheet(bg_color: tuple[float, float, float, float]) -> str:
        bg = _rgba_to_css(bg_color)
        fg = _rgba_to_css(CONTROL_TEXT_COLOR)
        return (
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"font-size: {CONTROL_FONT_SIZE}px; border: none; border-radius: 4px; padding: 6px 10px; }}"
            f"QPushButton:disabled {{ opacity: 0.5; }}"
        )

    def _combobox_stylesheet(bg_color: tuple[float, float, float, float]) -> str:
        bg = _rgba_to_css(bg_color)
        fg = _rgba_to_css(CONTROL_TEXT_COLOR)
        return (
            f"QComboBox {{ background-color: {bg}; color: {fg}; "
            f"font-size: {CONTROL_FONT_SIZE}px; border: none; border-radius: 4px; padding: 6px 10px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background-color: {bg}; color: {fg}; "
            f"selection-background-color: {_rgba_to_css(PRIMARY_BUTTON_COLOR)}; }}"
        )

    app = QApplication.instance() or QApplication(sys.argv)

    class KookieWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.startup_action: str | None = None
            self._ = get_translator(getattr(runtime.config, "language", "en"))
            self._save_spinner_tick = 0
            self._load_spinner_tick = 0
            self._recent_files: list[str] = []

            self.editor_prefs = load_editor_preferences(runtime.config.asset_dir)

            self.setMinimumSize(1280, 820)
            if self.width() < 1280 or self.height() < 820:
                self.resize(1280, 820)
            self.setWindowTitle("Kookie")
            icon_path = _app_icon_path()
            if icon_path is not None:
                self.setWindowIcon(QIcon(icon_path))

            selected_theme = getattr(runtime.config, "theme", "system")
            dark_mode = selected_theme == "dark" or (
                selected_theme == "system" and detect_system_dark_mode()
            )
            if getattr(runtime.config, "high_contrast", False):
                bg_color = (0.0, 0.0, 0.0, 1.0)
            elif dark_mode:
                bg_color = APP_BACKGROUND_COLOR
            else:
                bg_color = (0.94, 0.95, 0.97, 1.0)

            central = QWidget()
            self.setCentralWidget(central)
            central.setStyleSheet(
                f"QWidget#central {{ background-color: {_rgba_to_css(bg_color)}; }}"
            )
            central.setObjectName("central")

            main_layout = QVBoxLayout(central)
            main_layout.setSpacing(14)
            main_layout.setContentsMargins(20, 16, 20, 16)

            # --- Editor Controls Toolbar ---
            editor_controls = QWidget()
            editor_controls.setFixedHeight(90)
            editor_controls.setStyleSheet(
                f"background-color: {_rgba_to_css(TOOLBAR_BACKGROUND_COLOR)};"
            )
            ec_layout = QHBoxLayout(editor_controls)
            ec_layout.setSpacing(12)
            ec_layout.setContentsMargins(14, 12, 14, 12)

            self.font_picker = QComboBox()
            self.font_picker.addItems(list(CURATED_FONT_NAMES))
            self.font_picker.setCurrentText(self.editor_prefs.font_name)
            self.font_picker.setFixedWidth(280)
            self.font_picker.setStyleSheet(_combobox_stylesheet(CONTROL_SURFACE_COLOR))

            self.font_size_picker = QComboBox()
            self.font_size_picker.addItems([str(size) for size in EDITOR_FONT_SIZES])
            self.font_size_picker.setCurrentText(str(self.editor_prefs.font_size))
            self.font_size_picker.setFixedWidth(140)
            self.font_size_picker.setStyleSheet(_combobox_stylesheet(CONTROL_SURFACE_COLOR))

            self.word_wrap_toggle = QPushButton(self._wrap_label(self.editor_prefs.word_wrap))
            self.word_wrap_toggle.setCheckable(True)
            self.word_wrap_toggle.setChecked(self.editor_prefs.word_wrap)
            self.word_wrap_toggle.setFixedWidth(220)
            self._update_wrap_toggle_style()

            ec_layout.addWidget(self.font_picker)
            ec_layout.addWidget(self.font_size_picker)
            ec_layout.addWidget(self.word_wrap_toggle)
            ec_layout.addStretch()
            main_layout.addWidget(editor_controls)

            # --- URL Input Bar ---
            url_bar = QWidget()
            url_bar.setFixedHeight(82)
            url_bar.setStyleSheet(
                f"background-color: {_rgba_to_css(TOOLBAR_BACKGROUND_COLOR)};"
            )
            url_layout = QHBoxLayout(url_bar)
            url_layout.setSpacing(12)
            url_layout.setContentsMargins(14, 12, 14, 12)

            self.url_input = QLineEdit()
            self.url_input.setPlaceholderText("Enter a URL to load webpage text...")
            self.url_input.setStyleSheet(
                f"background-color: {_rgba_to_css(TEXT_BACKGROUND_COLOR)}; "
                f"color: {_rgba_to_css(TEXT_FOREGROUND_COLOR)}; "
                f"font-size: {URL_INPUT_FONT_SIZE}px; "
                f"border: none; padding: 10px 12px;"
            )

            self.url_load_btn = QPushButton("Load URL")
            self.url_load_btn.setFixedWidth(180)
            self.url_load_btn.setStyleSheet(_button_stylesheet(PRIMARY_BUTTON_COLOR))
            self.url_load_btn.clicked.connect(self._on_load_url)

            url_layout.addWidget(self.url_input, 1)
            url_layout.addWidget(self.url_load_btn)
            main_layout.addWidget(url_bar)

            # --- Main Text Editor ---
            self.text_editor = QTextEdit()
            self.text_editor.setPlainText(runtime.text)
            self._apply_editor_text_style()
            self.text_editor.setTabChangesFocus(False)
            self.text_editor.textChanged.connect(
                lambda: runtime.set_text(self.text_editor.toPlainText())
            )
            main_layout.addWidget(self.text_editor, 1)

            # --- Editor preference change signals ---
            self.font_picker.currentTextChanged.connect(self._on_font_change)
            self.font_size_picker.currentTextChanged.connect(self._on_font_size_change)
            self.word_wrap_toggle.toggled.connect(self._on_word_wrap_change)

            # --- Playback Controls Toolbar ---
            controls = QWidget()
            controls.setFixedHeight(94)
            controls.setStyleSheet(
                f"background-color: {_rgba_to_css(TOOLBAR_BACKGROUND_COLOR)};"
            )
            ctrl_layout = QHBoxLayout(controls)
            ctrl_layout.setSpacing(14)
            ctrl_layout.setContentsMargins(14, 12, 14, 12)

            self.load_btn = QPushButton(self._("Load PDF"))
            self.load_btn.setStyleSheet(_button_stylesheet(CONTROL_SURFACE_COLOR))
            self.play_btn = QPushButton(self._("Play"))
            self.play_btn.setStyleSheet(_button_stylesheet(PRIMARY_BUTTON_COLOR))
            self.pause_btn = QPushButton("Pause")
            self.pause_btn.setStyleSheet(_button_stylesheet(CONTROL_SURFACE_COLOR))
            self.stop_btn = QPushButton(self._("Stop"))
            self.stop_btn.setStyleSheet(_button_stylesheet(DANGER_BUTTON_COLOR))
            self.save_btn = QPushButton(self._("Save MP3"))
            self.save_btn.setStyleSheet(_button_stylesheet(SUCCESS_BUTTON_COLOR))

            self.voice_picker = QComboBox()
            self.voice_picker.addItems(runtime.available_voices())
            self.voice_picker.setCurrentText(runtime.selected_voice)
            self.voice_picker.setFixedWidth(220)
            self.voice_picker.setStyleSheet(_combobox_stylesheet(CONTROL_SURFACE_COLOR))

            self.speed_picker = QComboBox()
            self.speed_picker.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
            self.speed_picker.setCurrentText("1.0x")
            self.speed_picker.setFixedWidth(140)
            self.speed_picker.setStyleSheet(_combobox_stylesheet(CONTROL_SURFACE_COLOR))

            self.volume_slider = QSlider(Qt.Orientation.Horizontal)
            self.volume_slider.setRange(0, 100)
            self.volume_slider.setValue(100)
            self.volume_slider.setFixedWidth(160)

            self.save_spinner = QLabel("")
            self.save_spinner.setFixedWidth(220)
            self.save_spinner.setStyleSheet(
                f"color: {_rgba_to_css(STATUS_TEXT_COLOR)}; font-size: {STATUS_FONT_SIZE}px;"
            )

            self.load_btn.clicked.connect(self._on_load_pdf)
            self.play_btn.clicked.connect(self._on_play)
            self.pause_btn.clicked.connect(self._on_pause)
            self.stop_btn.clicked.connect(self._on_stop)
            self.save_btn.clicked.connect(self._on_save)
            self.voice_picker.currentTextChanged.connect(self._on_voice_change)
            self.speed_picker.currentTextChanged.connect(self._on_speed_change)
            self.volume_slider.valueChanged.connect(
                lambda v: self._on_volume_change(v / 100.0)
            )

            ctrl_layout.addWidget(self.load_btn)
            ctrl_layout.addWidget(self.play_btn)
            ctrl_layout.addWidget(self.pause_btn)
            ctrl_layout.addWidget(self.stop_btn)
            ctrl_layout.addWidget(self.save_btn)
            ctrl_layout.addWidget(self.voice_picker)
            ctrl_layout.addWidget(self.speed_picker)
            ctrl_layout.addWidget(self.volume_slider)
            ctrl_layout.addWidget(self.save_spinner)
            main_layout.addWidget(controls)

            # --- Status Bar ---
            status_bar = QWidget()
            status_bar.setFixedHeight(STATUS_BAR_HEIGHT)
            status_bar.setStyleSheet(
                f"background-color: {_rgba_to_css(TOOLBAR_BACKGROUND_COLOR)};"
            )
            sb_layout = QVBoxLayout(status_bar)
            sb_layout.setSpacing(STATUS_BAR_ROW_SPACING)
            sb_layout.setContentsMargins(*STATUS_BAR_PADDING)

            status_label_style = (
                f"color: {_rgba_to_css(STATUS_TEXT_COLOR)}; font-size: {STATUS_FONT_SIZE}px;"
            )

            status_header = QWidget()
            status_header.setFixedHeight(STATUS_HEADER_HEIGHT)
            sh_layout = QHBoxLayout(status_header)
            sh_layout.setSpacing(16)
            sh_layout.setContentsMargins(0, 0, 0, 0)

            self.voice_status = QLabel("")
            self.voice_status.setStyleSheet(status_label_style)
            self.voice_status.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.backend_status = QLabel("")
            self.backend_status.setStyleSheet(status_label_style)
            self.backend_status.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

            self.activity_status = QLabel("")
            self.activity_status.setFixedHeight(STATUS_ACTIVITY_ROW_MIN_HEIGHT)
            self.activity_status.setStyleSheet(status_label_style)
            self.activity_status.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

            self.progress_status = QLabel("")
            self.progress_status.setFixedHeight(STATUS_PROGRESS_ROW_MIN_HEIGHT)
            self.progress_status.setStyleSheet(status_label_style)
            self.progress_status.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

            self.recent_status = QLabel("")
            self.recent_status.setFixedHeight(STATUS_RECENT_ROW_MIN_HEIGHT)
            self.recent_status.setStyleSheet(status_label_style)
            self.recent_status.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

            sh_layout.addWidget(self.voice_status, 42)
            sh_layout.addWidget(self.backend_status, 58)
            sb_layout.addWidget(status_header)
            sb_layout.addWidget(self.activity_status)
            sb_layout.addWidget(self.progress_status)
            sb_layout.addWidget(self.recent_status)
            main_layout.addWidget(status_bar)

            # --- Keyboard Shortcuts ---
            QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self._on_play)
            QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._on_save)
            QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._on_load_pdf)
            QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._try_undo)
            QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self._try_redo)
            if startup_prompt is not None:
                QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._on_retry)
                QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._on_quit)

            # --- Startup prompt ---
            if startup_prompt is not None:
                prompt_message = str(startup_prompt.get("message", "")).strip()
                if prompt_message:
                    runtime.status_message = prompt_message

            # --- Sync timer ---
            self._sync_timer = QTimer(self)
            self._sync_timer.timeout.connect(self._sync_now)
            self._sync_timer.start(100)

            self._sync_now()
            self.text_editor.setFocus()

        def closeEvent(self, event: Any) -> None:
            runtime.stop()
            if startup_prompt is not None and self.startup_action is None:
                self.startup_action = "continue_mock"
            event.accept()

        def _on_load_pdf(self) -> None:
            try:
                selected_path = _prompt_pdf_path()
            except RuntimeError as exc:
                runtime.status_message = str(exc)
                self._sync_now()
                return

            if selected_path is None:
                runtime.status_message = "Load cancelled."
                self._sync_now()
                return

            runtime.start_pdf_load(selected_path)
            self._sync_now()

        def _on_load_url(self) -> None:
            url = self.url_input.text().strip()
            if not url:
                runtime.status_message = "Enter a URL in the address bar."
                self._sync_now()
                return

            runtime.start_webpage_load(url)
            self._sync_now()

        def _on_play(self) -> None:
            runtime.set_text(self.text_editor.toPlainText())
            runtime.play()
            self._sync_now()

        def _on_pause(self) -> None:
            if runtime.controller.state is PlaybackState.PAUSED:
                runtime.resume()
            else:
                runtime.pause()
            self._sync_now()

        def _on_stop(self) -> None:
            runtime.stop()
            self._sync_now()

        def _on_save(self) -> None:
            runtime.set_text(self.text_editor.toPlainText())
            if not runtime.text:
                runtime.status_message = "Enter text in the text area."
                self._sync_now()
                return

            try:
                output_path = _prompt_mp3_output_path()
            except RuntimeError as exc:
                runtime.status_message = str(exc)
                self._sync_now()
                return

            if output_path is None:
                runtime.status_message = "Save cancelled."
                self._sync_now()
                return

            runtime.start_mp3_save(output_path=output_path)
            self._sync_now()

        def _on_voice_change(self, selected_voice: str) -> None:
            runtime.set_voice(selected_voice)
            self._sync_now()

        def _on_speed_change(self, selected_speed: str) -> None:
            try:
                speed = float(selected_speed.lower().replace("x", "").strip())
            except ValueError:
                speed = 1.0
            runtime.set_playback_speed(speed)
            self._sync_now()

        def _on_volume_change(self, selected_volume: float) -> None:
            runtime.set_volume(selected_volume)

        def _on_retry(self) -> None:
            self.startup_action = "retry"
            self.close()

        def _on_quit(self) -> None:
            self.startup_action = "quit"
            self.close()

        def _try_undo(self) -> None:
            self.text_editor.undo()

        def _try_redo(self) -> None:
            self.text_editor.redo()

        def _sync_now(self) -> None:
            runtime.poll_mp3_save()

            loaded_text, pdf_path = runtime.poll_pdf_load()
            if loaded_text is not None and pdf_path is not None:
                self._recent_files = _update_recent_files(self._recent_files, str(pdf_path))
                self.text_editor.setPlainText(loaded_text)

            webpage_text, webpage_url = runtime.poll_webpage_load()
            if webpage_text is not None and webpage_url is not None:
                self.text_editor.setPlainText(webpage_text)

            is_saving = runtime.is_saving_mp3
            is_loading = runtime.is_loading_pdf or runtime.is_loading_webpage

            self.save_btn.setEnabled(not (is_saving or is_loading))
            self.play_btn.setEnabled(not (is_saving or is_loading))
            self.load_btn.setEnabled(not (is_saving or is_loading))
            self.url_load_btn.setEnabled(not (is_saving or is_loading))

            self.pause_btn.setText(
                "Resume" if runtime.controller.state is PlaybackState.PAUSED else "Pause"
            )

            if is_saving:
                self.save_spinner.setText(
                    _save_spinner_text(is_saving=is_saving, tick=self._save_spinner_tick)
                )
                self._save_spinner_tick += 1
            elif is_loading:
                self.save_spinner.setText(
                    _load_spinner_text(is_loading=is_loading, tick=self._load_spinner_tick)
                )
                self._load_spinner_tick += 1
            else:
                self.save_spinner.setText("")
                self._save_spinner_tick = 0
                self._load_spinner_tick = 0

            voice_text, backend_text, activity_text = _status_display_items(
                runtime.status_bar_items
            )
            self.voice_status.setText(voice_text)
            self.backend_status.setText(backend_text)
            self.activity_status.setText(activity_text)
            progress = runtime.playback_progress
            self.progress_status.setText(
                f"Progress: {progress['played_samples']} / {progress['synthesized_samples']} samples"
            )
            if runtime.status_message.startswith("Saved MP3:"):
                self._recent_files = _update_recent_files(
                    self._recent_files,
                    runtime.status_message.replace("Saved MP3:", "").strip(),
                )
            recent_tail = ", ".join(
                Path(item).name for item in self._recent_files[:3]
            )
            self.recent_status.setText(
                f"Recent: {recent_tail}" if recent_tail else "Recent: (none)"
            )

        def _on_font_change(self, selected_font: str) -> None:
            self._set_editor_preferences(font_name=selected_font)

        def _on_font_size_change(self, selected_size: str) -> None:
            self._set_editor_preferences(font_size=selected_size)

        def _on_word_wrap_change(self, checked: bool) -> None:
            self._set_editor_preferences(word_wrap=checked)

        def _set_editor_preferences(
            self,
            *,
            font_name: object | None = None,
            font_size: object | None = None,
            word_wrap: object | None = None,
        ) -> None:
            next_prefs = sanitize_editor_preferences(
                font_name=self.editor_prefs.font_name if font_name is None else font_name,
                font_size=self.editor_prefs.font_size if font_size is None else font_size,
                word_wrap=self.editor_prefs.word_wrap if word_wrap is None else word_wrap,
            )
            if next_prefs == self.editor_prefs:
                return

            self.editor_prefs = next_prefs
            self._apply_editor_preferences()
            save_editor_preferences(runtime.config.asset_dir, self.editor_prefs)

        def _apply_editor_preferences(self) -> None:
            self._apply_editor_text_style()

            if self.font_picker.currentText() != self.editor_prefs.font_name:
                self.font_picker.setCurrentText(self.editor_prefs.font_name)

            size_text = str(self.editor_prefs.font_size)
            if self.font_size_picker.currentText() != size_text:
                self.font_size_picker.setCurrentText(size_text)

            if self.word_wrap_toggle.isChecked() != self.editor_prefs.word_wrap:
                self.word_wrap_toggle.setChecked(self.editor_prefs.word_wrap)
            self.word_wrap_toggle.setText(self._wrap_label(self.editor_prefs.word_wrap))
            self._update_wrap_toggle_style()

        def _apply_editor_text_style(self) -> None:
            font = QFont(self.editor_prefs.font_name, self.editor_prefs.font_size)
            self.text_editor.setFont(font)

            if self.editor_prefs.word_wrap:
                self.text_editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
                self.text_editor.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
            else:
                self.text_editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
                self.text_editor.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )

            self.text_editor.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self.text_editor.setStyleSheet(
                f"QTextEdit {{ "
                f"background-color: {_rgba_to_css(TEXT_BACKGROUND_COLOR)}; "
                f"color: {_rgba_to_css(TEXT_FOREGROUND_COLOR)}; "
                f"selection-background-color: {_rgba_to_css(TEXT_SELECTION_COLOR)}; "
                f"padding: 16px; border: none; "
                f"}}"
            )

        def _update_wrap_toggle_style(self) -> None:
            if self.word_wrap_toggle.isChecked():
                self.word_wrap_toggle.setStyleSheet(_button_stylesheet(PRIMARY_BUTTON_COLOR))
            else:
                self.word_wrap_toggle.setStyleSheet(_button_stylesheet(CONTROL_SURFACE_COLOR))

        @staticmethod
        def _wrap_label(word_wrap: bool) -> str:
            return "Wrap: On" if word_wrap else "Wrap: Off"

    window = KookieWindow()
    window.show()
    app.exec()
    return window.startup_action
