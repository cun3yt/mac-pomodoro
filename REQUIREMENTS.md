# Project Requirements

This document outlines the necessary system and software dependencies required to build and run the Pomodoro Menu Bar App.

## 1. System Dependencies (macOS)

This application is designed for macOS and relies on the native windowing system (`tcl-tk`) and audio playback (`afplay`).

### Required Tools
- **macOS**: Tested on Sonoma/Sequoia (14.x/15.x).
- **Homebrew**: Package manager for installing system libraries.

### Library Installation
The `tkinter` GUI library requires `tcl-tk` version 8. Standard Python installs often miss this link.

```bash
# 1. Unlink any conflicting versions
brew unlink tcl-tk

# 2. Install version 8 explicitly (most stable for Python GUI on macOS)
brew install tcl-tk@8
brew link --force tcl-tk@8
```

## 2. Python Environment

### Python Version
- **Python 3.10+** is recommended.
- **Python 3.12.4** was used for development.

### Python Installation with Tkinter Hooks
**CRITICAL:** You must install Python with specific flags to link against the Homebrew `tcl-tk` library.

If using `pyenv`:
```bash
env PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$(brew --prefix tcl-tk@8)/include' --with-tcltk-libs='-L$(brew --prefix tcl-tk@8)/lib -ltcl8.6 -ltk8.6'" pyenv install 3.12.4 --force
```

## 3. Python Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### Dependency List
| Package | Purpose |
|---------|---------|
| `rumps` | Creates the macOS Menu Bar application. |
| `py2app` | Bundles the Python script into a standalone `.app`. |
| `setuptools` | Build system (pinned <70.0.0 for py2app compatibility). |

## 4. Runtime Dependencies

- **Audio**: The app uses `/System/Library/Sounds/Glass.aiff`. This is a standard macOS system sound.
- **Fonts**: Uses "Helvetica", which is standard on macOS.

