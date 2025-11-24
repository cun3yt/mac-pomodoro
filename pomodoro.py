import rumps
import time
import subprocess
import json
import os
import sys
import socket
import select

# NOTE: Tkinter is imported lazily in PomodoroClient to avoid RunLoop conflicts with Rumps

CONFIG_FILE = os.path.expanduser("~/.pomodoro_config.json")
SOCKET_PORT = 54545
SOCKET_HOST = '127.0.0.1'

# --- SHARED UTILS ---

def format_time(seconds):
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

# --- TKINTER GUI (CLIENT) ---

class PomodoroClient:
    def __init__(self):
        # Lazy import Tkinter here
        import tkinter as tk
        from tkinter import colorchooser
        
        self.tk = tk
        self.colorchooser = colorchooser
        
        self.root = tk.Tk()
        self.root.title("Pomodoro")
        self.root.withdraw() # Hide initially to prevent jump
        self.root.geometry("350x500")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # State
        self.state = {
            "mode": "Focus", 
            "time_left": 1500, 
            "running": False,
            "config": {
                "focus_min": 25, "rest_min": 5,
                "focus_color": "#FF443B", "rest_color": "#8E8E93",
                "notifications": True,
                "startup": False,
                "window_position": None
            }
        }
        
        self.first_state_received = False
        self.start_in_settings = "--settings" in sys.argv
        self.view_mode = "timer" # "timer" or "settings"
        
        self.sock = None
        self.connect_to_server()
        
        # --- GUI Setup ---
        self.container = tk.Frame(self.root, bg="#1C1C1E") 
        self.container.pack(fill="both", expand=True)
        
        self.front_frame = tk.Frame(self.container, bg="#1C1C1E")
        self.lbl_mode = tk.Label(self.front_frame, text="...", font=("Helvetica", 24, "bold"), bg="#1C1C1E", fg="white")
        self.lbl_mode.pack(pady=(40, 10))

        self.canvas_timer = tk.Canvas(self.front_frame, width=200, height=200, bg="#1C1C1E", highlightthickness=0)
        self.canvas_timer.pack(pady=10)
        
        self.lbl_time = tk.Label(self.front_frame, text="00:00", font=("Helvetica", 40, "bold"), bg="#1C1C1E", fg="white")
        self.lbl_time.place(in_=self.canvas_timer, relx=0.5, rely=0.5, anchor="center")

        self.btn_action = self.create_flat_button(self.front_frame, text="Start", command=self.send_toggle, bg="#333333", fg="white")
        self.btn_action.pack(pady=(20, 5))

        self.btn_switch = self.create_flat_button(self.front_frame, text="Switch Mode", command=self.send_switch, bg="#1C1C1E", fg="#666666", font=("Helvetica", 12))
        self.btn_switch.pack(pady=5)

        self.btn_settings = self.create_flat_button(self.front_frame, text="⚙ Settings", command=self.flip_to_back, bg="#1C1C1E", fg="#999999", font=("Helvetica", 12))
        self.btn_settings.pack(side="bottom", pady=20)

        # Back Face
        self.back_frame = tk.Frame(self.container, bg="#2C2C2E")
        tk.Label(self.back_frame, text="Configuration", font=("Helvetica", 18, "bold"), bg="#2C2C2E", fg="white").pack(pady=(30, 20))

        self.entries = {}
        self.color_btns = {}
        
        opts = [("Focus (min)", "focus_min"), ("Rest (min)", "rest_min")]
        for label, key in opts:
            row = tk.Frame(self.back_frame, bg="#2C2C2E")
            row.pack(fill="x", padx=40, pady=5)
            tk.Label(row, text=label, bg="#2C2C2E", fg="white", width=15, anchor="w").pack(side="left")
            e = tk.Entry(row, width=5, justify="center")
            e.pack(side="right")
            self.entries[key] = e

        colors = [("Focus Color", "focus_color"), ("Rest Color", "rest_color")]
        for label, key in colors:
            row = tk.Frame(self.back_frame, bg="#2C2C2E")
            row.pack(fill="x", padx=40, pady=5)
            tk.Label(row, text=label, bg="#2C2C2E", fg="white", width=15, anchor="w").pack(side="left")
            btn = self.create_flat_button(row, text=" ■ ", command=lambda k=key: self.pick_color(k), bg="black", fg="white", font=("Helvetica", 12))
            btn.pack(side="right")
            self.color_btns[key] = btn

        # Notifications Toggle
        row_notif = tk.Frame(self.back_frame, bg="#2C2C2E")
        row_notif.pack(fill="x", padx=40, pady=5)
        tk.Label(row_notif, text="Notifications", bg="#2C2C2E", fg="white", width=15, anchor="w").pack(side="left")
        self.btn_notif = self.create_flat_button(row_notif, text="ON", command=self.toggle_notifications, bg="#333333", fg="white", font=("Helvetica", 12))
        self.btn_notif.pack(side="right")

        # Startup Toggle
        row_start = tk.Frame(self.back_frame, bg="#2C2C2E")
        row_start.pack(fill="x", padx=40, pady=5)
        tk.Label(row_start, text="Launch at Login", bg="#2C2C2E", fg="white", width=15, anchor="w").pack(side="left")
        self.btn_startup = self.create_flat_button(row_start, text="OFF", command=self.toggle_startup, bg="#333333", fg="white", font=("Helvetica", 12))
        self.btn_startup.pack(side="right")

        self.btn_save = self.create_flat_button(self.back_frame, text="Save & Flip Back", command=self.save_and_flip, bg="#0A84FF", fg="white")
        self.btn_save.pack(side="bottom", pady=30)

        self.front_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Start listener loop
        self.root.after(100, self.listen_for_updates)
        
        # Force focus
        self.root.lift()
        self.root.attributes('-topmost',True)
        self.root.after_idle(self.root.attributes,'-topmost',False)

    def create_flat_button(self, parent, text, command, bg, fg, font=("Helvetica", 14)):
        lbl = self.tk.Label(parent, text=text, bg=bg, fg=fg, font=font, padx=20, pady=10, cursor="pointinghand")
        lbl.bind("<Button-1>", lambda e: self.on_btn_click(lbl, bg, fg, command))
        lbl.bind("<Leave>", lambda e: lbl.config(bg=bg))
        
        # Monkey patch set_color
        def set_color(c):
            lbl.config(bg=c)
            # Update closure defaults? No, better to store it on the object
            lbl.default_bg = c
        lbl.set_color = set_color
        lbl.default_bg = bg
        lbl.default_fg = fg
        
        return lbl

    def on_btn_click(self, btn, default_bg, default_fg, command):
        btn.config(bg="white", fg="black")
        btn.after(100, lambda: btn.config(bg=getattr(btn, 'default_bg', default_bg), fg=default_fg))
        if command: command()

    def mainloop(self):
        self.root.mainloop()

    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((SOCKET_HOST, SOCKET_PORT))
            self.send_command({"type": "GET_STATE"})
        except Exception as e:
            print(f"Connection failed: {e}")
            self.root.destroy()

    def listen_for_updates(self):
        if not self.sock: return
        
        ready = select.select([self.sock], [], [], 0)
        if ready[0]:
            try:
                data = self.sock.recv(4096)
                if not data: 
                    self.root.destroy() # Server closed
                    return
                
                # Handle multiple JSON objects in buffer
                parts = data.decode().split('\n')
                for part in parts:
                    if not part: continue
                    try:
                        msg = json.loads(part)
                        self.process_message(msg)
                    except: pass
            except Exception as e:
                print(e)
        
        self.root.after(100, self.listen_for_updates)

    def send_command(self, cmd):
        if self.sock:
            try:
                msg = json.dumps(cmd) + "\n"
                self.sock.sendall(msg.encode())
            except: pass

    def process_message(self, msg):
        if msg.get("type") == "STATE_UPDATE":
            # If in settings view, ignore config updates from server to avoid overwriting user input
            new_state = msg["data"]
            if self.view_mode == "settings":
                # Only update runtime state, preserve local config being edited
                self.state["mode"] = new_state["mode"]
                self.state["time_left"] = new_state["time_left"]
                self.state["running"] = new_state["running"]
                # Do NOT update self.state["config"]
            else:
                self.state = new_state
            
            self.update_ui()
        elif msg.get("type") == "SHOW_SETTINGS":
            if self.front_frame.winfo_ismapped():
                self.flip_to_back()
            self.root.lift()

    def update_ui(self):
        # Apply window position on first load
        if not self.first_state_received:
            self.first_state_received = True
            
            # Position
            pos = self.state["config"].get("window_position")
            if pos:
                self.root.geometry(pos)
            else:
                # Default to right side
                ws = self.root.winfo_screenwidth()
                x = ws - 350 - 50
                self.root.geometry(f"350x500+{x}+50")
            
            self.root.deiconify()
            
            # Check if we need to flip immediately
            if self.start_in_settings:
                self.flip_to_back()

        self.lbl_mode.config(text=self.state["mode"])
        self.lbl_time.config(text=format_time(self.state["time_left"]))
        
        # Button Text and Logic
        config = self.state["config"]
        max_time = (config["focus_min"] if self.state["mode"] == "Focus" else config["rest_min"]) * 60
        
        if self.state["running"]:
            self.btn_action.config(text="Pause")
            self.btn_action.set_color("#FF3B30") # Red for Pause (User accepted existing Red)
        else:
            if self.state["time_left"] == max_time:
                self.btn_action.config(text=f"Start {self.state['mode']}")
            else:
                self.btn_action.config(text=f"Continue {self.state['mode']}")
            self.btn_action.set_color("#333333") # Dark Grey

        next_mode = "Rest" if self.state["mode"] == "Focus" else "Focus"
        self.btn_switch.config(text=f"Switch to {next_mode}")

        # Arc
        total_time = max_time
        if total_time == 0: total_time = 1
        pct = self.state["time_left"] / total_time
        angle = pct * 360
        color = config["focus_color"] if self.state["mode"] == "Focus" else config["rest_color"]
        
        self.canvas_timer.delete("all")
        self.canvas_timer.create_oval(10, 10, 190, 190, outline="#333333", width=10)
        if angle > 0:
            self.canvas_timer.create_arc(10, 10, 190, 190, start=90, extent=angle, outline=color, style="arc", width=10)

        # Update settings inputs if this is the first load (empty)
        if not self.entries["focus_min"].get():
            self.entries["focus_min"].insert(0, str(config["focus_min"]))
            self.entries["rest_min"].insert(0, str(config["rest_min"]))
            self.color_btns["focus_color"].set_color(config["focus_color"])
            self.color_btns["rest_color"].set_color(config["rest_color"])
            
        # Update Notification Toggle
        notif_on = config.get("notifications", True)
        self.btn_notif.config(text="ON" if notif_on else "OFF")
        self.btn_notif.set_color("#333333" if notif_on else "#1C1C1E")
        self.btn_notif.default_fg = "white" if notif_on else "#666666"
        self.btn_notif.config(fg=self.btn_notif.default_fg)

        # Update Startup Toggle
        startup_on = config.get("startup", False)
        self.btn_startup.config(text="ON" if startup_on else "OFF")
        self.btn_startup.set_color("#333333" if startup_on else "#1C1C1E")
        self.btn_startup.default_fg = "white" if startup_on else "#666666"
        self.btn_startup.config(fg=self.btn_startup.default_fg)

    # Actions
    def send_toggle(self): self.send_command({"type": "TOGGLE"})
    def send_switch(self): self.send_command({"type": "SWITCH"})
    
    def toggle_notifications(self):
        current = self.state["config"].get("notifications", True)
        self.state["config"]["notifications"] = not current
        self.update_ui()

    def toggle_startup(self):
        current = self.state["config"].get("startup", False)
        self.state["config"]["startup"] = not current
        self.update_ui()
        
    def save_and_flip(self):
        try:
            new_config = self.state["config"].copy()
            new_config["focus_min"] = int(self.entries["focus_min"].get())
            new_config["rest_min"] = int(self.entries["rest_min"].get())
            # Color, notifications, startup are already in self.state["config"] via optimistic updates
            
            self.send_command({"type": "UPDATE_CONFIG", "data": new_config})
            self.animate_flip(self.back_frame, self.front_frame)
            self.view_mode = "timer" # Set back to timer mode
        except ValueError: pass

    def pick_color(self, key):
        color = self.colorchooser.askcolor(title=f"Choose {key}")[1]
        if color:
            self.state["config"][key] = color # Optimistic update
            self.color_btns[key].set_color(color)

    def flip_to_back(self):
        self.view_mode = "settings"
        self.animate_flip(self.front_frame, self.back_frame)

    def animate_flip(self, frame_out, frame_in):
        step = 0.2
        width = 1.0
        for i in range(5):
            width -= step
            if width < 0: width = 0
            frame_out.place(relwidth=width, relx=(1-width)/2)
            self.root.update_idletasks()
            time.sleep(0.02)
        frame_out.place_forget()
        width = 0.0
        frame_in.place(relwidth=width, relx=0.5, rely=0, relheight=1)
        for i in range(6):
            frame_in.place(relwidth=width, relx=(1-width)/2)
            width += step
            self.root.update_idletasks()
            time.sleep(0.02)

    def on_close(self):
        # Save position
        try:
            geo = self.root.geometry()
            if self.sock:
                # Send config update with new position
                cfg = self.state["config"].copy()
                cfg["window_position"] = geo
                msg = json.dumps({"type": "UPDATE_CONFIG", "data": cfg}) + "\n"
                self.sock.sendall(msg.encode())
                time.sleep(0.05) # Give it a moment to flush
                self.sock.close()
        except: pass
        self.root.destroy()

# --- RUMPS APP (SERVER) ---

class PomodoroServer(rumps.App):
    def __init__(self):
        super(PomodoroServer, self).__init__("🍅 25:00")
        
        self.config_data = {
            "focus_min": 25, "rest_min": 5,
            "focus_color": "#FF443B", "rest_color": "#8E8E93",
            "notifications": True,
            "startup": False,
            "window_position": None
        }
        self.load_config()

        self.mode = "Focus"
        self.time_left = self.config_data["focus_min"] * 60
        self.running = False
        self.timer = rumps.Timer(self.on_tick, 1)
        
        # Explicit Menu Items for Dynamic Labels
        self.start_button = rumps.MenuItem("Start Focus", callback=self.toggle_timer)
        self.switch_button = rumps.MenuItem("Switch to Rest", callback=self.switch_mode)
        
        self.menu = [self.start_button, self.switch_button, None, "Show Timer", "Preferences", "Quit"]
        
        # Server Setup
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((SOCKET_HOST, SOCKET_PORT))
        self.server_sock.listen(1)
        self.server_sock.setblocking(False)
        self.client_sock = None
        
        # Timer for Socket Loop (Fake Async)
        self.socket_timer = rumps.Timer(self.socket_loop, 0.1)
        self.socket_timer.start()

        self.update_title()
        self.update_menu_labels()

    def socket_loop(self, _):
        # Accept connections
        if not self.client_sock:
            try:
                client, addr = self.server_sock.accept()
                self.client_sock = client
                self.client_sock.setblocking(False)
                self.push_state() # Send initial state
            except BlockingIOError: pass
        
        # Read Data
        if self.client_sock:
            try:
                data = self.client_sock.recv(4096)
                if not data:
                    self.client_sock = None
                    return
                
                parts = data.decode().split('\n')
                for part in parts:
                    if not part: continue
                    try:
                        cmd = json.loads(part)
                        self.handle_command(cmd)
                    except: pass
            except BlockingIOError: pass
            except Exception: 
                self.client_sock = None

    def handle_command(self, cmd):
        c_type = cmd.get("type")
        if c_type == "GET_STATE":
            self.push_state()
        elif c_type == "TOGGLE":
            self.toggle_timer(None)
        elif c_type == "SWITCH":
            self.switch_mode(None)
        elif c_type == "UPDATE_CONFIG":
            new_data = cmd["data"]
            # Check if times changed
            time_changed = False
            if new_data.get("focus_min") != self.config_data["focus_min"] or \
               new_data.get("rest_min") != self.config_data["rest_min"]:
                time_changed = True
            
            # Check if startup changed
            if new_data.get("startup") != self.config_data.get("startup"):
                self.toggle_startup_item(new_data.get("startup"))

            self.config_data.update(new_data)
            self.save_config()
            
            if time_changed:
                self.reset_timer_state()
            
            self.push_state()

    def push_state(self):
        if self.client_sock:
            state = {
                "mode": self.mode,
                "time_left": self.time_left,
                "running": self.running,
                "config": self.config_data
            }
            msg = json.dumps({"type": "STATE_UPDATE", "data": state}) + "\n"
            try:
                self.client_sock.sendall(msg.encode())
            except: self.client_sock = None

    def send_command_to_client(self, cmd):
        if self.client_sock:
            try:
                msg = json.dumps(cmd) + "\n"
                self.client_sock.sendall(msg.encode())
            except: self.client_sock = None

    # --- ACTIONS ---

    def toggle_startup_item(self, enable):
        # Only works if running as a frozen app
        if not getattr(sys, 'frozen', False):
            return
            
        app_path = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
        app_name = "Pomodoro"
        
        # Use AppleScript to manage Login Items
        if enable:
            cmd = f'''
            tell application "System Events"
                if not (exists login item "{app_name}") then
                    make login item at end with properties {{path:"{app_path}", hidden:false}}
                end if
            end tell
            '''
        else:
            cmd = f'''
            tell application "System Events"
                if exists login item "{app_name}" then
                    delete login item "{app_name}"
                end if
            end tell
            '''
        try:
            subprocess.run(["osascript", "-e", cmd], capture_output=True)
        except Exception as e:
            print(f"Failed to toggle startup: {e}")

    def update_menu_labels(self):
        max_time = self.config_data["focus_min"] * 60 if self.mode == "Focus" else self.config_data["rest_min"] * 60
        
        if self.running:
            self.start_button.title = "Pause"
        else:
            if self.time_left == max_time:
                self.start_button.title = f"Start {self.mode}"
            else:
                self.start_button.title = f"Continue {self.mode}"

        # Switch button label
        next_mode = "Rest" if self.mode == "Focus" else "Focus"
        self.switch_button.title = f"Switch to {next_mode}"

    def toggle_timer(self, sender=None):
        if self.running: self.stop_timer()
        else: self.start_timer()
        self.update_menu_labels()
        self.push_state()

    def start_timer(self):
        self.running = True
        self.timer.start()
        self.update_menu_labels()

    def stop_timer(self):
        self.running = False
        self.timer.stop()
        self.update_menu_labels()

    def switch_mode(self, sender=None):
        self.stop_timer()
        if self.mode == "Focus":
            self.mode = "Rest"
            self.time_left = self.config_data["rest_min"] * 60
        else:
            self.mode = "Focus"
            self.time_left = self.config_data["focus_min"] * 60
        
        self.update_title()
        self.update_menu_labels()
        self.push_state()

    @rumps.clicked("Show Timer")
    def show_gui(self, _):
        self.launch_gui_process()

    @rumps.clicked("Preferences")
    def show_prefs(self, _):
        self.launch_gui_process(start_in_settings=True)

    def launch_gui_process(self, start_in_settings=False):
        # Check if socket is already active (Client exists)
        if self.client_sock: 
            if start_in_settings:
                self.send_command_to_client({"type": "SHOW_SETTINGS"})
            # Bring to front?
            return 
        
        cmd = []
        # Launch ourselves with --gui flag
        if getattr(sys, 'frozen', False):
            # Running as .app
            if sys.argv[0].endswith('.py'):
                cmd = [sys.executable, sys.argv[0], "--gui"]
            else:
                cmd = [sys.argv[0], "--gui"]
        else:
            # Running as script
            cmd = [sys.executable, __file__, "--gui"]
            
        if start_in_settings:
            cmd.append("--settings")
            
        subprocess.Popen(cmd)

    def on_tick(self, sender):
        if self.time_left > 0:
            self.time_left -= 1
            self.update_title()
            # Push state every second ensures client clock is synced
            self.push_state() 
        else:
            self.finish_cycle()

    def update_title(self):
        mins = self.time_left // 60
        secs = self.time_left % 60
        emoji = "🍅" if self.mode == "Focus" else "☕"
        self.title = f"{emoji} {mins:02d}:{secs:02d}"

    def finish_cycle(self):
        self.stop_timer()
        self.play_alarm()
        
        if self.config_data.get("notifications", True):
            if self.mode == "Focus":
                rumps.notification("Pomodoro", "Focus time is up!", "Take a break. ☕")
            else:
                rumps.notification("Pomodoro", "Break is over!", "Back to work! 🍅")

        if self.mode == "Focus":
            self.mode = "Rest"
            self.time_left = self.config_data["rest_min"] * 60
        else:
            self.mode = "Focus"
            self.time_left = self.config_data["focus_min"] * 60
            
        self.update_title()
        self.update_menu_labels()
        self.push_state()

    def reset_timer_state(self):
        if self.mode == "Focus":
            self.time_left = self.config_data["focus_min"] * 60
        else:
            self.time_left = self.config_data["rest_min"] * 60
        self.update_title()
        self.update_menu_labels()

    def play_alarm(self):
        sound_path = "/System/Library/Sounds/Glass.aiff"
        if os.path.exists(sound_path):
            subprocess.run(["afplay", sound_path])

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
    if "--gui" in sys.argv:
        PomodoroClient().mainloop()
    else:
        PomodoroServer().run()
