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
TEXT_BACKGROUND_COLOR = (0.94, 0.95, 0.97, 1.0)
TEXT_SELECTION_COLOR = (0.70, 0.82, 0.98, 0.70)
TEXT_CURSOR_COLOR = (0.17, 0.40, 0.85, 1.0)
SAVE_SPINNER_FRAMES = ("|", "/", "-", "\\")
LOAD_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
APP_BACKGROUND_COLOR = (0.07, 0.10, 0.15, 1.0)
TOOLBAR_BACKGROUND_COLOR = (0.14, 0.18, 0.25, 1.0)
CONTROL_SURFACE_COLOR = (0.21, 0.26, 0.34, 1.0)
PRIMARY_BUTTON_COLOR = (0.19, 0.52, 0.75, 1.0)
SUCCESS_BUTTON_COLOR = (0.22, 0.56, 0.39, 1.0)
DANGER_BUTTON_COLOR = (0.70, 0.30, 0.29, 1.0)
CONTROL_TEXT_COLOR = (0.96, 0.98, 1.0, 1.0)
STATUS_TEXT_COLOR = (0.90, 0.93, 0.98, 1.0)
STATUS_VOICE_MAX_CHARS = 24
STATUS_BACKEND_MAX_CHARS = 28
STATUS_ACTIVITY_MAX_CHARS = 72
APP_ICON_FILENAME = "kookie.png"
STATUS_HEADER_HEIGHT = 30
STATUS_ACTIVITY_ROW_MIN_HEIGHT = 30
STATUS_PROGRESS_ROW_MIN_HEIGHT = 30
STATUS_RECENT_ROW_MIN_HEIGHT = 30
STATUS_BAR_ROW_SPACING = 4
STATUS_BAR_PADDING = (10, 8, 10, 8)
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


def _text_input_config(initial_text: str, *, prefs: EditorPreferences) -> dict[str, object]:
    return {
        "text": initial_text,
        "multiline": True,
        "readonly": False,
        "disabled": False,
        "input_type": "text",
        "font_name": prefs.font_name,
        "font_size": prefs.font_size,
        "do_wrap": prefs.word_wrap,
        "write_tab": True,
        "background_normal": "",
        "background_active": "",
        "background_disabled_normal": "",
        "foreground_color": TEXT_FOREGROUND_COLOR,
        "background_color": TEXT_BACKGROUND_COLOR,
        "selection_color": TEXT_SELECTION_COLOR,
        "cursor_color": TEXT_CURSOR_COLOR,
        "padding": [14, 14, 14, 14],
    }


def _scroll_view_config(word_wrap: bool) -> dict[str, object]:
    return {
        "scroll_type": ["bars", "content"],
        "bar_width": 12,
        "bar_pos_y": "right",
        "scroll_wheel_distance": "12sp",
        "smooth_scroll_end": 10,
        "do_scroll_y": True,
        "do_scroll_x": not word_wrap,
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
        "halign": "left",
        "valign": "middle",
        "shorten": True,
        "shorten_from": "center",
        "max_lines": 1,
        "color": STATUS_TEXT_COLOR,
    }


def _label_text_size_for_width(width: float) -> tuple[float, None]:
    return (max(0.0, width), None)


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


def _control_style(*, background_color: tuple[float, float, float, float]) -> dict[str, object]:
    return {
        "background_normal": "",
        "background_down": "",
        "background_disabled_normal": "",
        "background_disabled_down": "",
        "background_color": background_color,
        "color": CONTROL_TEXT_COLOR,
    }


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


def run_kivy_ui(runtime, startup_prompt: dict[str, object] | None = None) -> str | None:
    try:
        from kivy.app import App
        from kivy.clock import Clock
        from kivy.core.window import Window
        from kivy.graphics import Color, Rectangle
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.slider import Slider
        from kivy.uix.spinner import Spinner
        from kivy.uix.textinput import TextInput
        from kivy.uix.togglebutton import ToggleButton
    except Exception as exc:  # pragma: no cover - depends on local GUI deps
        raise RuntimeError("Kivy is required to run the graphical application") from exc

    from .i18n import get_translator

    class KookieApp(App):
        def __init__(self, **kwargs: Any):
            super().__init__(**kwargs)
            self.startup_action: str | None = None
            icon_path = _app_icon_path()
            if icon_path is not None:
                self.icon = icon_path

        def build(self):
            if startup_prompt is not None:
                prompt_message = str(startup_prompt.get("message", "")).strip()
                if prompt_message:
                    runtime.status_message = prompt_message

            self._ = get_translator(getattr(runtime.config, "language", "en"))
            selected_theme = getattr(runtime.config, "theme", "system")
            dark_mode = selected_theme == "dark" or (selected_theme == "system" and detect_system_dark_mode())
            if getattr(runtime.config, "high_contrast", False):
                Window.clearcolor = (0.0, 0.0, 0.0, 1.0)
            elif dark_mode:
                Window.clearcolor = APP_BACKGROUND_COLOR
            else:
                Window.clearcolor = (0.95, 0.96, 0.98, 1.0)
            root = BoxLayout(orientation="vertical", spacing=12, padding=[18, 14, 18, 14])

            self.editor_prefs = load_editor_preferences(runtime.config.asset_dir)

            editor_controls = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=50,
                spacing=8,
                padding=[8, 6, 8, 6],
            )
            self._paint_background(editor_controls, TOOLBAR_BACKGROUND_COLOR, Color=Color, Rectangle=Rectangle)
            self.font_picker = Spinner(
                text=self.editor_prefs.font_name,
                values=list(CURATED_FONT_NAMES),
                size_hint=(None, 1),
                width=210,
                **_control_style(background_color=CONTROL_SURFACE_COLOR),
            )
            self.font_size_picker = Spinner(
                text=str(self.editor_prefs.font_size),
                values=[str(size) for size in EDITOR_FONT_SIZES],
                size_hint=(None, 1),
                width=110,
                **_control_style(background_color=CONTROL_SURFACE_COLOR),
            )
            self.word_wrap_toggle = ToggleButton(
                text=self._wrap_label(self.editor_prefs.word_wrap),
                state="down" if self.editor_prefs.word_wrap else "normal",
                size_hint=(None, 1),
                width=160,
                **_control_style(background_color=PRIMARY_BUTTON_COLOR),
            )
            editor_controls.add_widget(self.font_picker)
            editor_controls.add_widget(self.font_size_picker)
            editor_controls.add_widget(self.word_wrap_toggle)
            root.add_widget(editor_controls)

            self.editor_scroll = ScrollView(**_scroll_view_config(word_wrap=self.editor_prefs.word_wrap))
            self.text_input = TextInput(
                **_text_input_config(
                    initial_text=runtime.text,
                    prefs=self.editor_prefs,
                )
            )
            self.text_input.size_hint_y = None
            self.text_input.bind(text=lambda _, value: runtime.set_text(value))
            self.text_input.bind(minimum_height=lambda *_: self._sync_text_input_size())
            self.editor_scroll.bind(height=lambda *_: self._sync_text_input_size())
            self.editor_scroll.bind(width=lambda *_: self._sync_text_input_size())
            try:
                self.text_input.bind(minimum_width=lambda *_: self._sync_text_input_size())
            except Exception:
                pass
            self.editor_scroll.add_widget(self.text_input)
            root.add_widget(self.editor_scroll)

            self.font_picker.bind(text=lambda _, value: self._on_font_change(value))
            self.font_size_picker.bind(text=lambda _, value: self._on_font_size_change(value))
            self.word_wrap_toggle.bind(state=lambda _, value: self._on_word_wrap_change(value))

            controls = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=58,
                spacing=10,
                padding=[8, 7, 8, 7],
            )
            self._paint_background(controls, TOOLBAR_BACKGROUND_COLOR, Color=Color, Rectangle=Rectangle)
            self.load_btn = Button(text=self._("Load PDF"), **_control_style(background_color=CONTROL_SURFACE_COLOR))
            self.play_btn = Button(text=self._("Play"), **_control_style(background_color=PRIMARY_BUTTON_COLOR))
            self.pause_btn = Button(text="Pause", **_control_style(background_color=CONTROL_SURFACE_COLOR))
            stop_btn = Button(text=self._("Stop"), **_control_style(background_color=DANGER_BUTTON_COLOR))
            self.save_btn = Button(text=self._("Save MP3"), **_control_style(background_color=SUCCESS_BUTTON_COLOR))
            self.voice_picker = Spinner(
                text=runtime.selected_voice,
                values=runtime.available_voices(),
                size_hint=(None, 1),
                width=120,
                **_control_style(background_color=CONTROL_SURFACE_COLOR),
            )
            self.speed_picker = Spinner(
                text="1.0x",
                values=["0.5x", "1.0x", "1.5x", "2.0x"],
                size_hint=(None, 1),
                width=90,
                **_control_style(background_color=CONTROL_SURFACE_COLOR),
            )
            self.volume_slider = Slider(min=0.0, max=1.0, value=1.0, size_hint=(None, 1), width=120)
            self.save_spinner = Label(text="", size_hint=(None, 1), width=140, **_status_label_config())
            self._bind_label_text_size(self.save_spinner)
            self.load_btn.bind(on_press=lambda *_: self._on_load_pdf())
            self.play_btn.bind(on_press=lambda *_: self._on_play())
            self.pause_btn.bind(on_press=lambda *_: self._on_pause())
            stop_btn.bind(on_press=lambda *_: self._on_stop())
            self.save_btn.bind(on_press=lambda *_: self._on_save())
            self.voice_picker.bind(text=lambda _, value: self._on_voice_change(value))
            self.speed_picker.bind(text=lambda _, value: self._on_speed_change(value))
            self.volume_slider.bind(value=lambda _, value: self._on_volume_change(value))
            controls.add_widget(self.load_btn)
            controls.add_widget(self.play_btn)
            controls.add_widget(self.pause_btn)
            controls.add_widget(stop_btn)
            controls.add_widget(self.save_btn)
            controls.add_widget(self.voice_picker)
            controls.add_widget(self.speed_picker)
            controls.add_widget(self.volume_slider)
            controls.add_widget(self.save_spinner)
            root.add_widget(controls)
            self._save_spinner_tick = 0
            self._load_spinner_tick = 0
            self._recent_files: list[str] = []

            status_bar = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=STATUS_BAR_HEIGHT,
                spacing=STATUS_BAR_ROW_SPACING,
                padding=list(STATUS_BAR_PADDING),
            )
            self._paint_background(status_bar, TOOLBAR_BACKGROUND_COLOR, Color=Color, Rectangle=Rectangle)
            status_header = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=STATUS_HEADER_HEIGHT,
                spacing=10,
            )
            self.voice_status = Label(text="", size_hint_x=0.42, **_status_label_config())
            self.backend_status = Label(text="", size_hint_x=0.58, **_status_label_config())
            self.activity_status = Label(
                text="",
                size_hint_y=None,
                height=STATUS_ACTIVITY_ROW_MIN_HEIGHT,
                **_status_label_config(),
            )
            self.progress_status = Label(
                text="",
                size_hint_y=None,
                height=STATUS_PROGRESS_ROW_MIN_HEIGHT,
                **_status_label_config(),
            )
            self.recent_status = Label(
                text="",
                size_hint_y=None,
                height=STATUS_RECENT_ROW_MIN_HEIGHT,
                **_status_label_config(),
            )
            self._bind_label_text_size(self.voice_status)
            self._bind_label_text_size(self.backend_status)
            self._bind_label_text_size(self.activity_status)
            self._bind_label_text_size(self.progress_status)
            self._bind_label_text_size(self.recent_status)
            status_header.add_widget(self.voice_status)
            status_header.add_widget(self.backend_status)
            status_bar.add_widget(status_header)
            status_bar.add_widget(self.activity_status)
            status_bar.add_widget(self.progress_status)
            status_bar.add_widget(self.recent_status)
            root.add_widget(status_bar)

            Clock.schedule_interval(self._sync_ui, 0.1)
            self._sync_now()
            Clock.schedule_once(lambda *_: self._sync_text_input_size(), 0)
            Clock.schedule_once(lambda *_: setattr(self.text_input, "focus", True), 0)
            Window.bind(on_key_down=self._on_key_down)
            return root

        def on_stop(self):
            runtime.stop()
            if startup_prompt is not None and self.startup_action is None:
                self.startup_action = "continue_mock"

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

        def _on_play(self) -> None:
            runtime.set_text(self.text_input.text)
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
            runtime.set_text(self.text_input.text)
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

        def _on_key_down(self, _window, _key, _scancode, codepoint, modifiers) -> bool:
            modifier_set = {value.lower() for value in (modifiers or [])}
            is_primary_shortcut = "meta" in modifier_set or "ctrl" in modifier_set
            if not is_primary_shortcut:
                return False

            key_text = (codepoint or "").lower()
            if key_text == "p":
                self._on_play()
                return True
            if key_text == "s":
                self._on_save()
                return True
            if key_text == "o":
                self._on_load_pdf()
                return True
            if key_text == "z":
                if "shift" in modifier_set:
                    self._try_redo()
                else:
                    self._try_undo()
                return True
            if startup_prompt is not None and key_text == "r":
                self.startup_action = "retry"
                self.stop()
                return True
            if startup_prompt is not None and key_text == "q":
                self.startup_action = "quit"
                self.stop()
                return True
            return False

        def _try_undo(self) -> None:
            undo = getattr(self.text_input, "do_undo", None)
            if callable(undo):
                undo()

        def _try_redo(self) -> None:
            redo = getattr(self.text_input, "do_redo", None)
            if callable(redo):
                redo()

        def _sync_ui(self, *_: Any) -> None:
            self._sync_now()

        def _sync_now(self) -> None:
            runtime.poll_mp3_save()
            
            loaded_text, pdf_path = runtime.poll_pdf_load()
            if loaded_text is not None and pdf_path is not None:
                self._recent_files = _update_recent_files(self._recent_files, str(pdf_path))
                self.text_input.text = loaded_text
                self._sync_text_input_size()

            is_saving = runtime.is_saving_mp3
            is_loading = runtime.is_loading_pdf
            
            self.save_btn.disabled = is_saving or is_loading
            self.play_btn.disabled = is_saving or is_loading
            self.load_btn.disabled = is_saving or is_loading
            
            self.pause_btn.text = "Resume" if runtime.controller.state is PlaybackState.PAUSED else "Pause"
            
            if is_saving:
                self.save_spinner.text = _save_spinner_text(is_saving=is_saving, tick=self._save_spinner_tick)
                self._save_spinner_tick += 1
            elif is_loading:
                self.save_spinner.text = _load_spinner_text(is_loading=is_loading, tick=self._load_spinner_tick)
                self._load_spinner_tick += 1
            else:
                self.save_spinner.text = ""
                self._save_spinner_tick = 0
                self._load_spinner_tick = 0

            voice_text, backend_text, activity_text = _status_display_items(runtime.status_bar_items)
            self.voice_status.text = voice_text
            self.backend_status.text = backend_text
            self.activity_status.text = activity_text
            progress = runtime.playback_progress
            self.progress_status.text = (
                f"Progress: {progress['played_samples']} / {progress['synthesized_samples']} samples"
            )
            if runtime.status_message.startswith("Saved MP3:"):
                self._recent_files = _update_recent_files(
                    self._recent_files,
                    runtime.status_message.replace("Saved MP3:", "").strip(),
                )
            recent_tail = ", ".join(Path(item).name for item in self._recent_files[:3])
            self.recent_status.text = f"Recent: {recent_tail}" if recent_tail else "Recent: (none)"

        def _on_font_change(self, selected_font: str) -> None:
            self._set_editor_preferences(font_name=selected_font)

        def _on_font_size_change(self, selected_size: str) -> None:
            self._set_editor_preferences(font_size=selected_size)

        def _on_word_wrap_change(self, state: str) -> None:
            self._set_editor_preferences(word_wrap=state == "down")

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
            try:
                self.text_input.font_name = self.editor_prefs.font_name
            except Exception:
                self.editor_prefs = sanitize_editor_preferences(
                    font_name="Roboto",
                    font_size=self.editor_prefs.font_size,
                    word_wrap=self.editor_prefs.word_wrap,
                )
                self.text_input.font_name = self.editor_prefs.font_name
            self.text_input.font_size = self.editor_prefs.font_size
            self.text_input.do_wrap = self.editor_prefs.word_wrap

            for key, value in _scroll_view_config(self.editor_prefs.word_wrap).items():
                setattr(self.editor_scroll, key, value)

            if self.font_picker.text != self.editor_prefs.font_name:
                self.font_picker.text = self.editor_prefs.font_name

            size_text = str(self.editor_prefs.font_size)
            if self.font_size_picker.text != size_text:
                self.font_size_picker.text = size_text

            target_state = "down" if self.editor_prefs.word_wrap else "normal"
            if self.word_wrap_toggle.state != target_state:
                self.word_wrap_toggle.state = target_state
            self.word_wrap_toggle.text = self._wrap_label(self.editor_prefs.word_wrap)
            if self.word_wrap_toggle.state == "down":
                self.word_wrap_toggle.background_color = PRIMARY_BUTTON_COLOR
            else:
                self.word_wrap_toggle.background_color = CONTROL_SURFACE_COLOR
            self._sync_text_input_size()

        def _sync_text_input_size(self, *_: Any) -> None:
            scroll_height = getattr(self.editor_scroll, "height", 0)
            scroll_width = getattr(self.editor_scroll, "width", 0)
            minimum_height = getattr(self.text_input, "minimum_height", 0)
            self.text_input.height = max(scroll_height, minimum_height)

            if self.editor_prefs.word_wrap:
                self.text_input.size_hint_x = 1
                return

            self.text_input.size_hint_x = None
            minimum_width = getattr(self.text_input, "minimum_width", 0)
            self.text_input.width = max(scroll_width, minimum_width)

        @staticmethod
        def _wrap_label(word_wrap: bool) -> str:
            return "Wrap: On" if word_wrap else "Wrap: Off"

        @staticmethod
        def _paint_background(
            widget: Any,
            color: tuple[float, float, float, float],
            *,
            Color: Any,
            Rectangle: Any,
        ) -> None:
            with widget.canvas.before:
                Color(*color)
                background_rect = Rectangle(pos=widget.pos, size=widget.size)

            def _sync_background(instance, *_):
                background_rect.pos = instance.pos
                background_rect.size = instance.size

            widget.bind(pos=_sync_background, size=_sync_background)

        @staticmethod
        def _bind_label_text_size(label: Any) -> None:
            def _sync_text_size(instance, *_):
                instance.text_size = _label_text_size_for_width(instance.width)

            label.bind(size=_sync_text_size)
            _sync_text_size(label)

    app = KookieApp()
    app.run()
    return app.startup_action
