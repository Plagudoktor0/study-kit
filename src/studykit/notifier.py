import subprocess
import sys


def send(title: str, message: str) -> bool:
    """Show a desktop notification. Returns False if it could not be shown."""
    try:
        if sys.platform == "win32":
            from winotify import Notification

            Notification(app_id="study-kit", title=title, msg=message, duration="short").show()
            return True
        if sys.platform == "darwin":
            script = [
                "on run argv",
                "display notification (item 1 of argv) with title (item 2 of argv)",
                "end run",
            ]
            args = ["osascript"] + [part for line in script for part in ("-e", line)]
            subprocess.run(args + [message, title], check=True, capture_output=True)
            return True
    except Exception:
        return False  # a failed pop-up must never crash the app
    return False
