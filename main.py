import json
import math
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from pynput import keyboard, mouse


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


if sys.platform == "win32":
    ULONG_PTR_TYPE = getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)
    LRESULT_TYPE = getattr(wintypes, "LRESULT", ctypes.c_ssize_t)
    WPARAM_TYPE = getattr(wintypes, "WPARAM", ctypes.c_size_t)
    LPARAM_TYPE = getattr(wintypes, "LPARAM", ctypes.c_ssize_t)
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x01000
    WHEEL_DELTA = 120

    class WindowsWheelHook:
        WH_MOUSE_LL = 14
        WM_MOUSEWHEEL = 0x020A
        WM_MOUSEHWHEEL = 0x020E
        WM_QUIT = 0x0012
        HC_ACTION = 0

        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("pt", wintypes.POINT),
                ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR_TYPE),
            ]

        LowLevelMouseProc = ctypes.WINFUNCTYPE(
            LRESULT_TYPE,
            ctypes.c_int,
            WPARAM_TYPE,
            LPARAM_TYPE,
        )

        def __init__(self, on_scroll_callback):
            self.on_scroll_callback = on_scroll_callback
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32
            self._hook = None
            self._proc = None
            self._thread = None
            self._thread_id = None
            self._started = threading.Event()

        def _low_level_proc(self, n_code, w_param, l_param):
            if n_code == self.HC_ACTION and w_param in (self.WM_MOUSEWHEEL, self.WM_MOUSEHWHEEL):
                info = ctypes.cast(l_param, ctypes.POINTER(self.MSLLHOOKSTRUCT)).contents
                delta = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
                step = delta / 120.0
                if w_param == self.WM_MOUSEWHEEL:
                    self.on_scroll_callback(int(info.pt.x), int(info.pt.y), 0.0, float(step))
                else:
                    self.on_scroll_callback(int(info.pt.x), int(info.pt.y), float(step), 0.0)

            return self.user32.CallNextHookEx(self._hook, n_code, w_param, l_param)

        def _run(self):
            self._thread_id = self.kernel32.GetCurrentThreadId()
            self._proc = self.LowLevelMouseProc(self._low_level_proc)
            module = self.kernel32.GetModuleHandleW(None)
            self._hook = self.user32.SetWindowsHookExW(
                self.WH_MOUSE_LL,
                self._proc,
                module,
                0,
            )
            self._started.set()
            if not self._hook:
                return

            msg = wintypes.MSG()
            while self.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))

            self.user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

        def start(self):
            if self._thread and self._thread.is_alive():
                return
            self._started.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self._started.wait(timeout=1.0)

        def stop(self):
            if not self._thread:
                return
            if self._thread_id:
                self.user32.PostThreadMessageW(self._thread_id, self.WM_QUIT, 0, 0)
            self._thread.join(timeout=1.0)
            self._thread = None
            self._thread_id = None


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
        self.min_move_interval = 0.003  # 3ms for better path accuracy
        self.last_recorded_pos = None

        self.mouse_listener = None
        self.keyboard_listener = None
        self.mouse_controller = mouse.Controller()
        self.wheel_hook = None
        self.last_scroll_time = 0.0
        self.last_scroll_signature = None
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

    def _event_type_counts(self):
        counts = {"move": 0, "click": 0, "scroll": 0}
        for event in self.events:
            event_type = event.get("type")
            if event_type in counts:
                counts[event_type] += 1
        return counts

    def _append_move_event(
        self,
        x: int,
        y: int,
        timestamp: float,
        force: bool = False,
    ) -> None:
        if not force and (timestamp - self.last_move_time) < self.min_move_interval:
            return

        pos = (int(x), int(y))
        if not force and self.last_recorded_pos == pos:
            return

        self.last_move_time = timestamp
        self.last_recorded_pos = pos
        self.events.append(
            {
                "type": "move",
                "time": timestamp,
                "x": pos[0],
                "y": pos[1],
            }
        )

    def _append_scroll_event(self, x: int, y: int, dx: float, dy: float) -> None:
        if not self.is_recording:
            return

        t = self._timestamp()
        sig = (int(x), int(y), round(float(dx), 4), round(float(dy), 4))
        if self.last_scroll_signature == sig and (t - self.last_scroll_time) < 0.003:
            return

        self.last_scroll_time = t
        self.last_scroll_signature = sig
        self.events.append(
            {
                "type": "scroll",
                "time": t,
                "x": int(x),
                "y": int(y),
                "dx": float(dx),
                "dy": float(dy),
            }
        )

    def _emit_scroll(self, step_x: int, step_y: int) -> None:
        if step_x == 0 and step_y == 0:
            return

        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            if step_y != 0:
                user32.mouse_event(
                    MOUSEEVENTF_WHEEL,
                    0,
                    0,
                    int(step_y * WHEEL_DELTA),
                    0,
                )
            if step_x != 0:
                user32.mouse_event(
                    MOUSEEVENTF_HWHEEL,
                    0,
                    0,
                    int(step_x * WHEEL_DELTA),
                    0,
                )
            return

        self.mouse_controller.scroll(step_x, step_y)

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
        self.last_recorded_pos = None
        self.last_scroll_time = 0.0
        self.last_scroll_signature = None
        self.is_recording = True
        self.status_var.set("Recording... move/click/scroll then press Esc")
        self._set_recording_ui(True)

        start_x, start_y = self.mouse_controller.position
        self._append_move_event(start_x, start_y, 0.0, force=True)

        def on_move(x, y):
            if not self.is_recording:
                return
            self._append_move_event(x, y, self._timestamp())

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
            self._append_scroll_event(x, y, dx, dy)

        self.mouse_listener = mouse.Listener(
            on_move=on_move,
            on_click=on_click,
            on_scroll=on_scroll,
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
        if sys.platform == "win32":
            self.wheel_hook = WindowsWheelHook(on_scroll)
            self.wheel_hook.start()

    def stop_recording(self) -> None:
        if not self.is_recording:
            return

        end_x, end_y = self.mouse_controller.position
        self._append_move_event(end_x, end_y, self._timestamp(), force=True)

        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.wheel_hook:
            self.wheel_hook.stop()
            self.wheel_hook = None

        if self.events:
            self._save_last_recording()

        self._set_recording_ui(False)
        counts = self._event_type_counts()
        self.status_var.set(
            "Stopped. "
            f"Total {len(self.events)} | "
            f"Move {counts['move']} | "
            f"Click {counts['click']} | "
            f"Scroll {counts['scroll']}"
        )

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
            replay_events = sorted(self.events, key=lambda item: float(item.get("time", 0.0)))
            replay_start = time.perf_counter()
            scroll_x_remainder = 0.0
            scroll_y_remainder = 0.0
            replay_scroll_events = 0
            for event in replay_events:
                target_time = float(event.get("time", 0.0))
                while True:
                    elapsed = time.perf_counter() - replay_start
                    remaining = target_time - elapsed
                    if remaining <= 0:
                        break
                    time.sleep(min(remaining, 0.002))

                etype = event.get("type")
                if etype == "move":
                    self.mouse_controller.position = (int(event["x"]), int(event["y"]))
                elif etype == "click":
                    self.mouse_controller.position = (int(event["x"]), int(event["y"]))
                    btn = getattr(mouse.Button, event["button"], None)
                    if btn:
                        if event["pressed"]:
                            self.mouse_controller.press(btn)
                        else:
                            self.mouse_controller.release(btn)
                elif etype == "scroll":
                    replay_scroll_events += 1
                    self.mouse_controller.position = (int(event["x"]), int(event["y"]))
                    scroll_x_remainder += float(event.get("dx", 0.0))
                    scroll_y_remainder += float(event.get("dy", 0.0))
                    scroll_x = math.trunc(scroll_x_remainder)
                    scroll_y = math.trunc(scroll_y_remainder)
                    if scroll_x != 0 or scroll_y != 0:
                        self._emit_scroll(scroll_x, scroll_y)
                        scroll_x_remainder -= scroll_x
                        scroll_y_remainder -= scroll_y

            # Flush residual fractional scroll at end so tiny touchpad deltas
            # still produce a final visible scroll step.
            final_x = int(round(scroll_x_remainder))
            final_y = int(round(scroll_y_remainder))
            if final_x != 0 or final_y != 0:
                self._emit_scroll(final_x, final_y)

            if replay_events:
                last = replay_events[-1]
                if "x" in last and "y" in last:
                    self.mouse_controller.position = (int(last["x"]), int(last["y"]))

            self.root.after(0, lambda: self._on_replay_done(replay_scroll_events))

        threading.Thread(target=run_replay, daemon=True).start()

    def _on_replay_done(self, replay_scroll_events: int = 0) -> None:
        self._set_recording_ui(False)
        self.status_var.set(f"Replay finished | Scroll events replayed: {replay_scroll_events}")

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
        if self.wheel_hook:
            self.wheel_hook.stop()
            self.wheel_hook = None
        self.root.destroy()


def main() -> None:
    enable_windows_dpi_awareness()
    root = tk.Tk()
    app = MouseRecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
