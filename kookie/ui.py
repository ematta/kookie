from __future__ import annotations

from pathlib import Path
from typing import Any

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
        "do_scroll_y": True,
        "do_scroll_x": not word_wrap,
    }


def _save_spinner_text(*, is_saving: bool, tick: int) -> str:
    if not is_saving:
        return ""

    frame = SAVE_SPINNER_FRAMES[tick % len(SAVE_SPINNER_FRAMES)]
    return f"Saving MP3 {frame}"


def run_kivy_ui(runtime) -> None:
    try:
        from kivy.app import App
        from kivy.clock import Clock
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.spinner import Spinner
        from kivy.uix.textinput import TextInput
        from kivy.uix.togglebutton import ToggleButton
    except Exception as exc:  # pragma: no cover - depends on local GUI deps
        raise RuntimeError("Kivy is required to run the graphical application") from exc

    class KookieApp(App):
        def build(self):
            root = BoxLayout(orientation="vertical", spacing=12, padding=16)

            self.editor_prefs = load_editor_preferences(runtime.config.asset_dir)

            editor_controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=8)
            self.font_picker = Spinner(
                text=self.editor_prefs.font_name,
                values=list(CURATED_FONT_NAMES),
                size_hint=(None, 1),
                width=210,
            )
            self.font_size_picker = Spinner(
                text=str(self.editor_prefs.font_size),
                values=[str(size) for size in EDITOR_FONT_SIZES],
                size_hint=(None, 1),
                width=110,
            )
            self.word_wrap_toggle = ToggleButton(
                text=self._wrap_label(self.editor_prefs.word_wrap),
                state="down" if self.editor_prefs.word_wrap else "normal",
                size_hint=(None, 1),
                width=160,
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

            controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=56, spacing=12)
            load_btn = Button(text="Load PDF")
            self.play_btn = Button(text="Play")
            stop_btn = Button(text="Stop")
            self.save_btn = Button(text="Save MP3")
            self.save_spinner = Label(text="", halign="left", valign="middle", size_hint=(None, 1), width=140)
            load_btn.bind(on_press=lambda *_: self._on_load_pdf())
            self.play_btn.bind(on_press=lambda *_: self._on_play())
            stop_btn.bind(on_press=lambda *_: self._on_stop())
            self.save_btn.bind(on_press=lambda *_: self._on_save())
            controls.add_widget(load_btn)
            controls.add_widget(self.play_btn)
            controls.add_widget(stop_btn)
            controls.add_widget(self.save_btn)
            controls.add_widget(self.save_spinner)
            root.add_widget(controls)
            self._save_spinner_tick = 0

            status_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=36, spacing=12, padding=[8, 4])
            self.voice_status = Label(text="", halign="left", valign="middle")
            self.backend_status = Label(text="", halign="left", valign="middle")
            self.activity_status = Label(text="", halign="left", valign="middle")
            status_bar.add_widget(self.voice_status)
            status_bar.add_widget(self.backend_status)
            status_bar.add_widget(self.activity_status)
            root.add_widget(status_bar)

            Clock.schedule_interval(self._sync_ui, 0.1)
            self._sync_now()
            Clock.schedule_once(lambda *_: self._sync_text_input_size(), 0)
            Clock.schedule_once(lambda *_: setattr(self.text_input, "focus", True), 0)
            return root

        def on_stop(self):
            runtime.stop()

        def _on_load_pdf(self) -> None:
            chooser = FileChooserListView(
                path=str(Path.home()),
                filters=["*.pdf"],
                multiselect=False,
            )

            actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=52, spacing=8)
            cancel_btn = Button(text="Cancel")
            load_btn = Button(text="Load")
            actions.add_widget(cancel_btn)
            actions.add_widget(load_btn)

            container = BoxLayout(orientation="vertical", spacing=8, padding=8)
            container.add_widget(chooser)
            container.add_widget(actions)

            popup = Popup(
                title="Load PDF",
                content=container,
                size_hint=(0.9, 0.9),
                auto_dismiss=False,
            )
            cancel_btn.bind(on_press=lambda *_: popup.dismiss())
            load_btn.bind(on_press=lambda *_: self._confirm_pdf_selection(popup, chooser))
            popup.open()

        def _confirm_pdf_selection(self, popup: Any, chooser: Any) -> None:
            selection = list(getattr(chooser, "selection", []))
            if not selection:
                runtime.status_message = "Select a PDF file to load."
                self._sync_now()
                return

            selected_path = Path(selection[0])
            loaded_text = runtime.load_pdf(selected_path)
            if loaded_text is not None:
                self.text_input.text = loaded_text
                self._sync_text_input_size()
                popup.dismiss()
            self._sync_now()

        def _on_play(self) -> None:
            runtime.set_text(self.text_input.text)
            runtime.play()
            self._sync_now()

        def _on_stop(self) -> None:
            runtime.stop()
            self._sync_now()

        def _on_save(self) -> None:
            runtime.set_text(self.text_input.text)
            runtime.start_mp3_save()
            self._sync_now()

        def _sync_ui(self, *_: Any) -> None:
            self._sync_now()

        def _sync_now(self) -> None:
            runtime.poll_mp3_save()
            is_saving = runtime.is_saving_mp3
            self.save_btn.disabled = is_saving
            self.play_btn.disabled = is_saving
            self.save_spinner.text = _save_spinner_text(is_saving=is_saving, tick=self._save_spinner_tick)
            if is_saving:
                self._save_spinner_tick += 1
            else:
                self._save_spinner_tick = 0

            items = runtime.status_bar_items
            self.voice_status.text = items[0]
            self.backend_status.text = items[1]
            self.activity_status.text = items[2]

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
            return "Word Wrap: On" if word_wrap else "Word Wrap: Off"

    KookieApp().run()
