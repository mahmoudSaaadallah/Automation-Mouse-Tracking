import json
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from pynput import keyboard, mouse


class MouseRecorderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mouse Recorder")
        self.root.geometry("420x250")
        self.root.resizable(False, False)

        self.is_recording = False
        self.events = []
        self.record_start_time = None
        self.last_move_time = 0.0
        self.min_move_interval = 0.01  # 10ms

        self.mouse_listener = None
        self.keyboard_listener = None
        self.mouse_controller = mouse.Controller()
        self.recording_file = Path(__file__).with_name("last_recording.json")

        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._load_last_recording()
        self._set_recording_ui(False)
        self._start_keyboard_listener()

    def _build_ui(self) -> None:
        wrapper = tk.Frame(self.root, padx=18, pady=18)
        wrapper.pack(fill="both", expand=True)

        title = tk.Label(
            wrapper,
            text="Mouse Track + Replay",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(pady=(0, 14))

        self.start_btn = tk.Button(
            wrapper,
            text="Start Recording",
            width=26,
            command=self.start_recording,
            font=("Segoe UI", 10),
        )
        self.start_btn.pack(pady=4)

        self.stop_btn = tk.Button(
            wrapper,
            text="Stop Recording (Esc)",
            width=26,
            command=self.stop_recording,
            font=("Segoe UI", 10),
        )
        self.stop_btn.pack(pady=4)

        self.replay_btn = tk.Button(
            wrapper,
            text="Replay Last Recording",
            width=26,
            command=self.replay_last_recording,
            font=("Segoe UI", 10),
        )
        self.replay_btn.pack(pady=4)

        status_label = tk.Label(
            wrapper,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            fg="#1e4d91",
        )
        status_label.pack(pady=(14, 4))

        hint = tk.Label(
            wrapper,
            text="Press Esc any time to stop recording",
            font=("Segoe UI", 9),
            fg="#666666",
        )
        hint.pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _set_recording_ui(self, recording: bool) -> None:
        if recording:
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.replay_btn.config(state="disabled")
        else:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.replay_btn.config(state="normal")

    def _timestamp(self) -> float:
        return time.perf_counter() - self.record_start_time

    def _start_keyboard_listener(self) -> None:
        def on_press(key):
            if key == keyboard.Key.esc and self.is_recording:
                self.root.after(0, self.stop_recording)

        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

    def start_recording(self) -> None:
        if self.is_recording:
            return

        self.events = []
        self.record_start_time = time.perf_counter()
        self.last_move_time = 0.0
        self.is_recording = True
        self.status_var.set("Recording... move/click/scroll then press Esc")
        self._set_recording_ui(True)

        def on_move(x, y):
            if not self.is_recording:
                return
            t = self._timestamp()
            if (t - self.last_move_time) < self.min_move_interval:
                return
            self.last_move_time = t
            self.events.append(
                {
                    "type": "move",
                    "time": t,
                    "x": int(x),
                    "y": int(y),
                }
            )

        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return
            self.events.append(
                {
                    "type": "click",
                    "time": self._timestamp(),
                    "x": int(x),
                    "y": int(y),
                    "button": button.name,
                    "pressed": bool(pressed),
                }
            )

        def on_scroll(x, y, dx, dy):
            if not self.is_recording:
                return
            self.events.append(
                {
                    "type": "scroll",
                    "time": self._timestamp(),
                    "x": int(x),
                    "y": int(y),
                    "dx": int(dx),
                    "dy": int(dy),
                }
            )

        self.mouse_listener = mouse.Listener(
            on_move=on_move,
            on_click=on_click,
            on_scroll=on_scroll,
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()

    def stop_recording(self) -> None:
        if not self.is_recording:
            return

        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

        if self.events:
            self._save_last_recording()

        self._set_recording_ui(False)
        self.status_var.set(f"Stopped. Captured {len(self.events)} events")

    def replay_last_recording(self) -> None:
        if self.is_recording:
            messagebox.showwarning("Recording", "Stop recording first.")
            return
        if not self.events:
            messagebox.showinfo("No Data", "No recorded data to replay.")
            return

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.replay_btn.config(state="disabled")
        self.status_var.set("Replaying...")

        def run_replay():
            replay_start = time.perf_counter()
            for event in self.events:
                target_time = event["time"]
                while True:
                    elapsed = time.perf_counter() - replay_start
                    remaining = target_time - elapsed
                    if remaining <= 0:
                        break
                    time.sleep(min(remaining, 0.002))

                etype = event["type"]
                if etype == "move":
                    self.mouse_controller.position = (event["x"], event["y"])
                elif etype == "click":
                    self.mouse_controller.position = (event["x"], event["y"])
                    btn = getattr(mouse.Button, event["button"], None)
                    if btn:
                        if event["pressed"]:
                            self.mouse_controller.press(btn)
                        else:
                            self.mouse_controller.release(btn)
                elif etype == "scroll":
                    self.mouse_controller.position = (event["x"], event["y"])
                    self.mouse_controller.scroll(event["dx"], event["dy"])

            self.root.after(0, self._on_replay_done)

        threading.Thread(target=run_replay, daemon=True).start()

    def _on_replay_done(self) -> None:
        self._set_recording_ui(False)
        self.status_var.set("Replay finished")

    def _save_last_recording(self) -> None:
        try:
            self.recording_file.write_text(
                json.dumps(self.events, ensure_ascii=True, separators=(",", ":")),
                encoding="utf-8",
            )
        except OSError as exc:
            self.root.after(
                0,
                lambda: messagebox.showwarning(
                    "Save Failed",
                    f"Could not save recording:\n{exc}",
                ),
            )

    def _load_last_recording(self) -> None:
        if not self.recording_file.exists():
            return
        try:
            raw = self.recording_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                self.events = data
                self.status_var.set(f"Ready (loaded {len(self.events)} saved events)")
        except (OSError, json.JSONDecodeError):
            # Ignore damaged file and continue with empty recording.
            self.events = []

    def on_close(self) -> None:
        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = MouseRecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
