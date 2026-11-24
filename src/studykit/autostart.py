import sys
from pathlib import Path

if sys.platform == "win32":
    import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "study-kit"


def supported() -> bool:
    """Auto-start through the Windows registry only works on Windows."""
    return sys.platform == "win32"


def command() -> str:
    """The command Windows should run at login."""
    if getattr(sys, "frozen", False):  # running as the built .exe
        return f'"{sys.executable}"'
    # running from source: pythonw has no black console window
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw}" -m studykit.gui'


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def enable() -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command())


def disable() -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass  # already not enabled