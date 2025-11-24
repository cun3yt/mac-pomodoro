import rumps
import subprocess
import json
import os

CONFIG_FILE = os.path.expanduser("~/.pomodoro_config.json")

class PomodoroApp(rumps.App):
    def __init__(self):
        super(PomodoroApp, self).__init__("🍅 25:00")
        
        # Default Configuration
        self.config_data = {
            "focus_min": 25,
            "rest_min": 5
        }
        self.load_config()

        # State
        self.mode = "Focus"  # or "Rest"
        self.time_left = self.config_data["focus_min"] * 60
        self.running = False

        # Timer
        self.timer = rumps.Timer(self.on_tick, 1)

        # Menu Items
        self.menu = [
            "Start Focus",
            "Switch to Rest",
            None,  # Separator
            "Preferences"
        ]
        
        # Update initial title
        self.update_title()

    @rumps.clicked("Start Focus")
    def toggle_timer(self, sender):
        if self.running:
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        self.running = True
        self.menu["Start Focus"].title = "Stop"
        self.timer.start()

    def stop_timer(self):
        self.running = False
        next_action = "Focus" if self.mode == "Focus" else "Rest"
        self.menu["Start Focus"].title = f"Start {next_action}"
        self.timer.stop()

    @rumps.clicked("Switch to Rest")
    def switch_mode(self, sender):
        self.stop_timer()
        
        if self.mode == "Focus":
            self.mode = "Rest"
            self.time_left = self.config_data["rest_min"] * 60
            sender.title = "Switch to Focus"
        else:
            self.mode = "Focus"
            self.time_left = self.config_data["focus_min"] * 60
            sender.title = "Switch to Rest"
            
        # Update the Start/Stop button text to match new mode
        self.menu["Start Focus"].title = f"Start {self.mode}"
        
        self.update_title()

    @rumps.clicked("Preferences")
    def preferences(self, _):
        # Focus Time Prompt
        window = rumps.Window(
            message="Enter Focus duration in minutes:",
            title="Preferences",
            default_text=str(self.config_data["focus_min"]),
            dimensions=(100, 20)
        )
        response = window.run()
        if not response.clicked:
            return
            
        try:
            new_focus = int(response.text)
        except ValueError:
            rumps.alert("Invalid Input", "Please enter a valid integer for minutes.")
            return

        # Rest Time Prompt
        window = rumps.Window(
            message="Enter Rest duration in minutes:",
            title="Preferences",
            default_text=str(self.config_data["rest_min"]),
            dimensions=(100, 20)
        )
        response = window.run()
        if not response.clicked:
            return

        try:
            new_rest = int(response.text)
        except ValueError:
            rumps.alert("Invalid Input", "Please enter a valid integer for minutes.")
            return

        # Save and Apply
        self.config_data["focus_min"] = new_focus
        self.config_data["rest_min"] = new_rest
        self.save_config()

        # Reset timer if not running, or just update config for next run
        if not self.running:
            if self.mode == "Focus":
                self.time_left = self.config_data["focus_min"] * 60
            else:
                self.time_left = self.config_data["rest_min"] * 60
            self.update_title()

    def on_tick(self, sender):
        if self.time_left > 0:
            self.time_left -= 1
            self.update_title()
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
        
        # Auto-switch modes logic (optional, but standard pomodoro behavior)
        # For now, we just stop and let user switch, OR we can switch automatically.
        # The previous Tkinter app switched modes automatically. Let's preserve that.
        
        if self.mode == "Focus":
            self.mode = "Rest"
            self.time_left = self.config_data["rest_min"] * 60
            self.menu["Switch to Rest"].title = "Switch to Focus"
            rumps.notification("Pomodoro", "Focus time is up!", "Take a break. ☕")
        else:
            self.mode = "Focus"
            self.time_left = self.config_data["focus_min"] * 60
            self.menu["Switch to Rest"].title = "Switch to Rest"
            rumps.notification("Pomodoro", "Break is over!", "Back to work! 🍅")
            
        self.menu["Start Focus"].title = f"Start {self.mode}"
        self.update_title()

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
    PomodoroApp().run()
