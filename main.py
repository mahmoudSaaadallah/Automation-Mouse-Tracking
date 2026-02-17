import tkinter as tk
from tkinter import messagebox
import sys

try:
    from pynput import mouse
    from pynput.mouse import Button, Controller
except ImportError:
    print("\nError: This application requires a graphical display (X Server).")
    print("It cannot run in a headless environment like standard GitHub Codespaces.")
    print("Please run this script on your local machine.\n")
    sys.exit(1)

import time
import threading

class MouseMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("مسجل حركة الماوس - Mouse Macro")
        self.root.geometry("300x250")
        self.root.resizable(False, False)

        # متغيرات لتخزين البيانات
        self.recorded_events = []  # القائمة التي ستحفظ الحركات
        self.is_recording = False
        self.is_playing = False
        self.start_time = 0
        self.mouse_controller = Controller()
        self.listener = None

        # --- واجهة المستخدم ---
        self.status_label = tk.Label(root, text="جاهز", fg="blue", font=("Arial", 14))
        self.status_label.pack(pady=20)

        self.btn_record = tk.Button(root, text="بدء التسجيل", command=self.start_recording, bg="#4CAF50", fg="white", width=20)
        self.btn_record.pack(pady=5)

        self.btn_stop = tk.Button(root, text="إيقاف التسجيل", command=self.stop_recording, bg="#f44336", fg="white", width=20, state=tk.DISABLED)
        self.btn_stop.pack(pady=5)

        self.btn_play = tk.Button(root, text="تشغيل (Replay)", command=self.start_replay_thread, bg="#2196F3", fg="white", width=20, state=tk.DISABLED)
        self.btn_play.pack(pady=5)

        self.lbl_info = tk.Label(root, text="ملاحظة: زر الإيقاف سيتم تسجيل ضغطته أيضاً", font=("Arial", 8), fg="gray")
        self.lbl_info.pack(pady=10)

    # --- منطق التسجيل ---
    def start_recording(self):
        self.recorded_events = []  # تفريغ القائمة القديمة
        self.is_recording = True
        self.start_time = time.time()
        
        # تحديث الأزرار
        self.status_label.config(text="جاري التسجيل...", fg="red")
        self.btn_record.config(state=tk.DISABLED)
        self.btn_play.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        # بدء الاستماع للماوس في خيط منفصل (Thread) حتى لا يتجمد البرنامج
        self.listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll)
        self.listener.start()

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.listener:
                self.listener.stop()
            
            self.status_label.config(text="تم الحفظ!", fg="green")
            self.btn_record.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_play.config(state=tk.NORMAL)

    # دوال التقاط الأحداث (Events)
    def on_move(self, x, y):
        if self.is_recording:
            elapsed_time = time.time() - self.start_time
            self.recorded_events.append({
                'action': 'move',
                'x': x,
                'y': y,
                'time': elapsed_time
            })

    def on_click(self, x, y, button, pressed):
        if self.is_recording:
            elapsed_time = time.time() - self.start_time
            self.recorded_events.append({
                'action': 'click',
                'x': x,
                'y': y,
                'button': button,
                'pressed': pressed,
                'time': elapsed_time
            })

    def on_scroll(self, x, y, dx, dy):
        if self.is_recording:
            elapsed_time = time.time() - self.start_time
            self.recorded_events.append({
                'action': 'scroll',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy,
                'time': elapsed_time
            })

    # --- منطق إعادة التشغيل (Replay) ---
    def start_replay_thread(self):
        # تشغيل في خيط منفصل لعدم تجميد الواجهة
        threading.Thread(target=self.play_recording).start()

    def play_recording(self):
        if not self.recorded_events:
            return

        self.is_playing = True
        self.status_label.config(text="جاري التشغيل...", fg="blue")
        self.btn_record.config(state=tk.DISABLED)
        self.btn_play.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)

        start_replay_time = time.time()

        for event in self.recorded_events:
            # حساب الوقت الذي يجب انتظاره للوصول لنفس توقيت الحدث الأصلي
            current_time = time.time() - start_replay_time
            wait_time = event['time'] - current_time
            
            if wait_time > 0:
                time.sleep(wait_time)

            # تنفيذ الحركة
            if event['action'] == 'move':
                self.mouse_controller.position = (event['x'], event['y'])
            
            elif event['action'] == 'click':
                self.mouse_controller.position = (event['x'], event['y'])
                if event['pressed']:
                    self.mouse_controller.press(event['button'])
                else:
                    self.mouse_controller.release(event['button'])
            
            elif event['action'] == 'scroll':
                self.mouse_controller.position = (event['x'], event['y'])
                self.mouse_controller.scroll(event['dx'], event['dy'])

        self.is_playing = False
        self.status_label.config(text="انتهى التشغيل", fg="green")
        self.btn_record.config(state=tk.NORMAL)
        self.btn_play.config(state=tk.NORMAL)

# تشغيل التطبيق
if __name__ == "__main__":
    root = tk.Tk()
    app = MouseMacroApp(root)
    root.mainloop()
