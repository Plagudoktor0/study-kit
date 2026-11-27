import sys


def send(title: str, message: str) -> bool:
    """Show a Windows toast notification. Returns False if it could not be shown."""
    if sys.platform != "win32":
        return False
    try:
        from winotify import Notification

        Notification(app_id="study-kit", title=title, msg=message, duration="short").show()
        return True
    except Exception:
        return False  # a failed pop-up must never crash the app
