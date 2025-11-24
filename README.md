# Native macOS Pomodoro Timer

A clean, native-feeling Pomodoro timer for macOS written in Python. It features a dark-mode GUI, configurable timers, a "flip" animation for settings, and a custom-generated app icon.

## Features

- **Focus & Rest Modes:** Default 25m / 5m (Configurable).
- **Native Look:** Dark grey theme matching macOS aesthetics.
- **Custom UI:** Flat buttons with custom hover/click states to bypass standard macOS Tkinter limitations.
- **Sound:** Uses native macOS system sounds (afplay) for non-intrusive alarms.
- **Flip Animation:** 3D-like flip effect when switching between Timer and Settings views.
- **Standalone App:** Bundles into a .app file that lives in your Dock.

## Prerequisites

This project requires Python 3 and the `tcl-tk` library for the GUI.

### Crucial Note for macOS Users

Standard Python installations (via pyenv or brew) often miss the link to the macOS windowing system (Tcl/Tk). If you encounter `_tkinter` errors, you must reinstall Python with the specific hooks below.

### 1. Install System Dependencies

```bash
# Unlink any conflicting versions first
brew unlink tcl-tk

# Install version 8 explicitly (most stable for Python GUI)
brew install tcl-tk@8
brew link --force tcl-tk@8
```

### 2. Install Python with Tk Hooks

If using `pyenv`, you must force a reinstall to link the GUI framework:

```bash
env PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$(brew --prefix tcl-tk@8)/include' --with-tcltk-libs='-L$(brew --prefix tcl-tk@8)/lib -ltcl8.6 -ltk8.6'" pyenv install 3.12.4 --force
```

### 3. Install Python Packages

```bash
pip install -r requirements.txt
```

## How to Build & Run

### Generate the Icon

Create the high-quality tomato icon using the helper script.

```bash
python create_icon.py
```

This generates `icon.png` (trying to use macOS QuickLook for SVG rendering first, falling back to pixel-art if needed).

### Build the App

Use `py2app` to bundle the script into a macOS Application.

```bash
rm -rf build dist
python setup.py py2app
```

### Run

Launch the app directly from the terminal or drag it to your Applications folder.

```bash
./dist/Pomodoro.app/Contents/MacOS/Pomodoro
```

## Project Structure

- `pomodoro.py`: Main application logic, GUI, and timer thread.
- `setup.py`: Build configuration for `py2app`.

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. Use it at your own risk.

