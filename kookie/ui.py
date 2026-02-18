from __future__ import annotations

from pathlib import Path
from typing import Any

TEXT_FOREGROUND_COLOR = (0.10, 0.12, 0.15, 1.0)
TEXT_BACKGROUND_COLOR = (0.94, 0.95, 0.97, 1.0)
TEXT_SELECTION_COLOR = (0.70, 0.82, 0.98, 0.70)
TEXT_CURSOR_COLOR = (0.17, 0.40, 0.85, 1.0)


def _text_input_config(initial_text: str) -> dict[str, object]:
    return {
        "text": initial_text,
        "multiline": True,
        "readonly": False,
        "disabled": False,
        "input_type": "text",
        "background_normal": "",
        "background_active": "",
        "background_disabled_normal": "",
        "font_size": 18,
        "foreground_color": TEXT_FOREGROUND_COLOR,
        "background_color": TEXT_BACKGROUND_COLOR,
        "selection_color": TEXT_SELECTION_COLOR,
        "cursor_color": TEXT_CURSOR_COLOR,
        "padding": [14, 14, 14, 14],
    }


def run_kivy_ui(runtime) -> None:
    try:
        from kivy.app import App
        from kivy.clock import Clock
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.filechooser import FileChooserListView
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from kivy.uix.textinput import TextInput
    except Exception as exc:  # pragma: no cover - depends on local GUI deps
        raise RuntimeError("Kivy is required to run the graphical application") from exc

    class KookieApp(App):
        def build(self):
            root = BoxLayout(orientation="vertical", spacing=12, padding=16)

            self.text_input = TextInput(**_text_input_config(initial_text=runtime.text))
            self.text_input.bind(text=lambda _, value: runtime.set_text(value))
            root.add_widget(self.text_input)

            controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=56, spacing=12)
            load_btn = Button(text="Load PDF")
            play_btn = Button(text="Play")
            stop_btn = Button(text="Stop")
            save_btn = Button(text="Save MP3")
            load_btn.bind(on_press=lambda *_: self._on_load_pdf())
            play_btn.bind(on_press=lambda *_: self._on_play())
            stop_btn.bind(on_press=lambda *_: self._on_stop())
            save_btn.bind(on_press=lambda *_: self._on_save())
            controls.add_widget(load_btn)
            controls.add_widget(play_btn)
            controls.add_widget(stop_btn)
            controls.add_widget(save_btn)
            root.add_widget(controls)

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
            runtime.save_mp3()
            self._sync_now()

        def _sync_ui(self, *_: Any) -> None:
            self._sync_now()

        def _sync_now(self) -> None:
            items = runtime.status_bar_items
            self.voice_status.text = items[0]
            self.backend_status.text = items[1]
            self.activity_status.text = items[2]

    KookieApp().run()
