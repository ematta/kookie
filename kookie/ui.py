from __future__ import annotations

from typing import Any


def run_kivy_ui(runtime) -> None:
    try:
        from kivy.app import App
        from kivy.clock import Clock
        from kivy.graphics import Color, RoundedRectangle
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.textinput import TextInput
    except Exception as exc:  # pragma: no cover - depends on local GUI deps
        raise RuntimeError("Kivy is required to run the graphical application") from exc

    class KookieApp(App):
        def build(self):
            root = BoxLayout(orientation="vertical", spacing=12, padding=16)

            self.text_input = TextInput(
                text=runtime.text,
                multiline=True,
                font_size=18,
                foreground_color=(0.1, 0.1, 0.1, 1),
                background_color=(0, 0, 0, 0),
                cursor_color=(0.2, 0.45, 0.9, 1),
            )
            with self.text_input.canvas.before:
                Color(0.96, 0.97, 0.98, 1)
                self._text_bg = RoundedRectangle(radius=[16, 16, 16, 16])
            self.text_input.bind(pos=self._refresh_text_bg, size=self._refresh_text_bg)
            root.add_widget(self.text_input)

            controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=56, spacing=12)
            play_btn = Button(text="Play")
            stop_btn = Button(text="Stop")
            play_btn.bind(on_press=lambda *_: self._on_play())
            stop_btn.bind(on_press=lambda *_: self._on_stop())
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

            runtime.clipboard_monitor.start(Clock.schedule_interval)
            Clock.schedule_interval(self._sync_ui, 0.1)
            self._sync_now()
            return root

        def on_stop(self):
            runtime.clipboard_monitor.stop()
            runtime.stop()

        def _on_play(self) -> None:
            runtime.set_text(self.text_input.text)
            runtime.play()
            self._sync_now()

        def _on_stop(self) -> None:
            runtime.stop()
            self._sync_now()

        def _sync_ui(self, *_: Any) -> None:
            runtime.poll_clipboard_once()
            self._sync_now()

        def _sync_now(self) -> None:
            if self.text_input.text != runtime.text:
                self.text_input.text = runtime.text
            items = runtime.status_bar_items
            self.voice_status.text = items[0]
            self.backend_status.text = items[1]
            self.activity_status.text = items[2]

        def _refresh_text_bg(self, *_: Any) -> None:
            self._text_bg.pos = self.text_input.pos
            self._text_bg.size = self.text_input.size

    KookieApp().run()
