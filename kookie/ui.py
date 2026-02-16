from __future__ import annotations

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


def _next_text_value(
    current_text: str,
    clipboard_text: str | None,
    is_focused: bool,
    auto_clipboard_sync: bool,
) -> str:
    if not auto_clipboard_sync or clipboard_text is None or is_focused:
        return current_text
    return clipboard_text


def run_kivy_ui(runtime) -> None:
    try:
        from kivy.app import App
        from kivy.clock import Clock
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
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
            paste_btn = Button(text="Paste")
            play_btn = Button(text="Play")
            stop_btn = Button(text="Stop")
            paste_btn.bind(on_press=lambda *_: self._on_paste())
            play_btn.bind(on_press=lambda *_: self._on_play())
            stop_btn.bind(on_press=lambda *_: self._on_stop())
            controls.add_widget(paste_btn)
            controls.add_widget(play_btn)
            controls.add_widget(stop_btn)
            root.add_widget(controls)

            status_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=36, spacing=12, padding=[8, 4])
            self.voice_status = Label(text="", halign="left", valign="middle")
            self.backend_status = Label(text="", halign="left", valign="middle")
            self.activity_status = Label(text="", halign="left", valign="middle")
            status_bar.add_widget(self.voice_status)
            status_bar.add_widget(self.backend_status)
            status_bar.add_widget(self.activity_status)
            root.add_widget(status_bar)

            if runtime.config.auto_clipboard_sync:
                runtime.clipboard_monitor.start(Clock.schedule_interval)
            Clock.schedule_interval(self._sync_ui, 0.1)
            self._sync_now()
            Clock.schedule_once(lambda *_: setattr(self.text_input, "focus", True), 0)
            return root

        def on_stop(self):
            runtime.clipboard_monitor.stop()
            runtime.stop()

        def _on_play(self) -> None:
            runtime.set_text(self.text_input.text)
            runtime.play()
            self._sync_now()

        def _on_paste(self) -> None:
            pasted = _read_clipboard_text()
            if pasted:
                self.text_input.text = pasted
                runtime.set_text(self.text_input.text)
            self._sync_now()

        def _on_stop(self) -> None:
            runtime.stop()
            self._sync_now()

        def _sync_ui(self, *_: Any) -> None:
            clipboard_text = runtime.poll_clipboard_once() if runtime.config.auto_clipboard_sync else None
            next_text = _next_text_value(
                self.text_input.text,
                clipboard_text,
                self.text_input.focus,
                runtime.config.auto_clipboard_sync,
            )
            if next_text != self.text_input.text:
                self.text_input.text = next_text
            self._sync_now()

        def _sync_now(self) -> None:
            items = runtime.status_bar_items
            self.voice_status.text = items[0]
            self.backend_status.text = items[1]
            self.activity_status.text = items[2]

    KookieApp().run()


def _read_clipboard_text() -> str:
    try:
        from kivy.core.clipboard import Clipboard  # type: ignore

        value = Clipboard.paste()
        return value if isinstance(value, str) else ""
    except Exception:
        return ""
