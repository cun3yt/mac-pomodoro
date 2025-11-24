import tkinter as tk
from tkinter import ttk, colorchooser
import time
import subprocess
import threading
import json
import os

CONFIG_FILE = os.path.expanduser("~/.pomodoro_config.json")

class FlatButton(tk.Label):
    """A Label that acts like a button to ensure colors work on macOS"""
    def __init__(self, parent, text, command, bg, fg, font=("Helvetica", 14), **kwargs):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font, 
                         padx=20, pady=10, cursor="pointinghand", **kwargs)
        self.command = command
        self.default_bg = bg
        self.default_fg = fg # <--- Store the original text color securely
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)

    def on_click(self, event):
        # Visual Flash effect
        self.config(bg="white", fg="black")
        # FIX: Restore to self.default_fg instead of reading the current (black) color
        self.after(100, lambda: self.config(bg=self.default_bg, fg=self.default_fg))
        if self.command:
            self.command()

    def on_hover(self, event):
        pass 

    def on_leave(self, event):
        self.config(bg=self.default_bg)

    def set_color(self, color):
        self.default_bg = color
        self.config(bg=color)

class PomodoroApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Pomodoro")
        # CHANGED: Increased height from 450 to 500 to fit all buttons
        self.geometry("350x500") 
        self.resizable(False, False)

        # Default Configuration
        self.config_data = {
            "focus_min": 25,
            "rest_min": 5,
            "focus_color": "#FF443B",  # Mac Red
            "rest_color": "#8E8E93",   # Mac Grey
        }
        self.load_config()

        # State
        self.mode = "Focus" 
        self.running = False
        self.time_left = self.config_data["focus_min"] * 60
        self.timer_id = None

        # Main Container 
        self.container = tk.Frame(self, bg="#1C1C1E") 
        self.container.pack(fill="both", expand=True)

        # --- Front Face (Timer) ---
        self.front_frame = tk.Frame(self.container, bg="#1C1C1E")
        
        self.lbl_mode = tk.Label(self.front_frame, text=self.mode, font=("Helvetica", 24, "bold"), bg="#1C1C1E", fg="white")
        self.lbl_mode.pack(pady=(40, 10))

        self.canvas_timer = tk.Canvas(self.front_frame, width=200, height=200, bg="#1C1C1E", highlightthickness=0)
        self.canvas_timer.pack(pady=10)
        
        # Draw initial circle
        self.draw_timer_circle(360, self.config_data["focus_color"])
        
        self.lbl_time = tk.Label(self.front_frame, text=self.format_time(self.time_left), font=("Helvetica", 40, "bold"), bg="#1C1C1E", fg="white")
        self.lbl_time.place(in_=self.canvas_timer, relx=0.5, rely=0.5, anchor="center")

        # Start/Stop Button
        self.btn_action = FlatButton(self.front_frame, text="Start Focus", command=self.toggle_timer, 
                                     bg="#333333", fg="white")
        self.btn_action.pack(pady=(20, 5))

        # Switch Mode Button
        self.btn_switch = FlatButton(self.front_frame, text="Switch to Rest", command=self.switch_mode,
                                     bg="#1C1C1E", fg="#666666", font=("Helvetica", 12))
        self.btn_switch.pack(pady=5)

        self.btn_settings = FlatButton(self.front_frame, text="⚙ Settings", command=self.flip_to_back,
                                       bg="#1C1C1E", fg="#999999", font=("Helvetica", 12))
        self.btn_settings.pack(side="bottom", pady=20)

        # --- Back Face (Settings) ---
        self.back_frame = tk.Frame(self.container, bg="#2C2C2E")
        
        tk.Label(self.back_frame, text="Configuration", font=("Helvetica", 18, "bold"), bg="#2C2C2E", fg="white").pack(pady=(30, 20))

        # Inputs
        self.entries = {}
        self.color_btns = {}
        
        opts = [("Focus (min)", "focus_min"), ("Rest (min)", "rest_min")]
        for label, key in opts:
            row = tk.Frame(self.back_frame, bg="#2C2C2E")
            row.pack(fill="x", padx=40, pady=5)
            tk.Label(row, text=label, bg="#2C2C2E", fg="white", width=15, anchor="w").pack(side="left")
            e = tk.Entry(row, width=5, justify="center")
            e.insert(0, str(self.config_data[key]))
            e.pack(side="right")
            self.entries[key] = e

        # Color Pickers
        colors = [("Focus Color", "focus_color"), ("Rest Color", "rest_color")]
        for label, key in colors:
            row = tk.Frame(self.back_frame, bg="#2C2C2E")
            row.pack(fill="x", padx=40, pady=5)
            tk.Label(row, text=label, bg="#2C2C2E", fg="white", width=15, anchor="w").pack(side="left")
            
            btn = FlatButton(row, text=" ■ ", command=lambda k=key: self.pick_color(k),
                             bg=self.config_data[key], fg=self.config_data[key], font=("Helvetica", 12))
            btn.pack(side="right")
            self.color_btns[key] = btn

        self.btn_save = FlatButton(self.back_frame, text="Save & Flip Back", command=self.save_and_flip,
                                   bg="#0A84FF", fg="white")
        self.btn_save.pack(side="bottom", pady=30)

        # Initialize View
        self.current_frame = self.front_frame
        self.front_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def draw_timer_circle(self, angle, color):
        self.canvas_timer.delete("all")
        # Background track
        self.canvas_timer.create_oval(10, 10, 190, 190, outline="#333333", width=10)
        # Active arc
        if angle > 0:
            self.canvas_timer.create_arc(10, 10, 190, 190, start=90, extent=angle, outline=color, style="arc", width=10)

    def pick_color(self, key):
        color = colorchooser.askcolor(title=f"Choose {key}")[1]
        if color:
            self.config_data[key] = color
            self.color_btns[key].set_color(color)
            self.color_btns[key].config(fg=color)

    def switch_mode(self):
        """Manually switches between Focus and Rest"""
        self.stop_timer()
        
        if self.mode == "Focus":
            self.mode = "Rest"
            self.time_left = self.config_data["rest_min"] * 60
        else:
            self.mode = "Focus"
            self.time_left = self.config_data["focus_min"] * 60
            
        self.update_ui()
        self.lbl_mode.config(text=self.mode)
        self.update_switch_btn()

    def update_switch_btn(self):
        next_mode = "Rest" if self.mode == "Focus" else "Focus"
        self.btn_switch.config(text=f"Switch to {next_mode}")

    def toggle_timer(self):
        if self.running:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        self.running = True
        self.btn_action.config(text="Stop")
        self.btn_action.set_color("#FF3B30") # Red
        self.count_down()

    def stop_timer(self):
        self.running = False
        self.btn_action.config(text=f"Start {self.mode}")
        self.btn_action.set_color("#333333") # Dark Grey
        if self.timer_id:
            self.after_cancel(self.timer_id)

    def count_down(self):
        if self.running and self.time_left > 0:
            self.time_left -= 1
            self.update_ui()
            self.timer_id = self.after(1000, self.count_down)
        elif self.time_left <= 0:
            self.running = False
            self.finish_cycle()

    def update_ui(self):
        self.lbl_time.config(text=self.format_time(self.time_left))
        
        total_time = (self.config_data["focus_min"] if self.mode == "Focus" else self.config_data["rest_min"]) * 60
        if total_time == 0: total_time = 1
        pct = self.time_left / total_time
        angle = pct * 360
        
        color = self.config_data["focus_color"] if self.mode == "Focus" else self.config_data["rest_color"]
        self.draw_timer_circle(angle, color)

    def finish_cycle(self):
        threading.Thread(target=self.play_alarm).start()
        
        if self.mode == "Focus":
            self.mode = "Rest"
            self.time_left = self.config_data["rest_min"] * 60
        else:
            self.mode = "Focus"
            self.time_left = self.config_data["focus_min"] * 60
        
        self.stop_timer() 
        self.update_ui()
        self.lbl_mode.config(text=self.mode)
        self.update_switch_btn()

    def play_alarm(self):
        sound_path = "/System/Library/Sounds/Glass.aiff"
        if os.path.exists(sound_path):
            subprocess.run(["afplay", sound_path])
        else:
            self.bell()

    def format_time(self, seconds):
        return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

    def flip_to_back(self):
        self.stop_timer()
        self.animate_flip(self.front_frame, self.back_frame)

    def save_and_flip(self):
        try:
            self.config_data["focus_min"] = int(self.entries["focus_min"].get())
            self.config_data["rest_min"] = int(self.entries["rest_min"].get())
            self.save_config()
            
            if self.mode == "Focus":
                self.time_left = self.config_data["focus_min"] * 60
            else:
                self.time_left = self.config_data["rest_min"] * 60
            self.update_ui()
            
            self.animate_flip(self.back_frame, self.front_frame)
        except ValueError:
            pass 

    def animate_flip(self, frame_out, frame_in):
        step = 0.1
        width = 1.0
        for i in range(10):
            width -= step
            if width < 0: width = 0
            frame_out.place(relwidth=width, relx=(1-width)/2)
            self.update_idletasks()
            time.sleep(0.015)
        frame_out.place_forget()
        
        width = 0.0
        frame_in.place(relwidth=width, relx=0.5, rely=0, relheight=1)
        for i in range(11):
            frame_in.place(relwidth=width, relx=(1-width)/2)
            width += step
            self.update_idletasks()
            time.sleep(0.015)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    self.config_data.update(saved)
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config_data, f)

if __name__ == "__main__":
    app = PomodoroApp()
    app.mainloop()