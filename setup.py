from setuptools import setup

APP = ['pomodoro.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.png',
    'plist': {
        'CFBundleName': "Pomodoro",
        'CFBundleDisplayName': "Pomodoro",
        'CFBundleGetInfoString': "Pomodoro Timer",
        'CFBundleIdentifier': "com.user.pomodoro",
        'CFBundleVersion': "0.1.0",
        'CFBundleShortVersionString': "0.1.0",
        'NSHumanReadableCopyright': "Copyright © 2025",
    },
    # CRITICAL FIX: Force include the binary _tkinter module and the package
    'includes': ['_tkinter', 'tkinter'],
    'packages': ['tkinter'],
    'excludes': ['numpy', 'matplotlib', 'scipy', 'pandas'], 
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
