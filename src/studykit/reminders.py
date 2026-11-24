from datetime import date

from studykit import deadlines, storage


def is_enabled() -> bool:
    return storage.load()["settings"].get("notifications", True)


def set_enabled(value: bool) -> None:
    data = storage.load()
    data["settings"]["notifications"] = value
    storage.save(data)


def due_soon(today: date | None = None, within_days: int = 1) -> list[dict]:
    """Unfinished deadlines that are overdue or due within `within_days` days."""
    today = today or date.today()
    soon = []
    for item in deadlines.list_deadlines():
        left = (date.fromisoformat(item["due"]) - today).days
        if left <= within_days:
            soon.append(item)
    return soon


def describe(item: dict, today: date) -> str:
    left = (date.fromisoformat(item["due"]) - today).days
    if left < 0:
        return f"overdue {-left} d"
    if left == 0:
        return "due today"
    if left == 1:
        return "due tomorrow"
    return f"in {left} d"


def build_message(items: list[dict], today: date | None = None, limit: int = 3) -> str:
    """One line per deadline, at most `limit` lines, then '...and N more'."""
    today = today or date.today()
    lines = []
    for item in items[:limit]:
        subject = f" ({item['subject']})" if item["subject"] else ""
        lines.append(f"{item['title']}{subject}: {describe(item, today)}")
    extra = len(items) - limit
    if extra > 0:
        lines.append(f"...and {extra} more")
    return "\n".join(lines)


def check_and_notify(send, today: date | None = None) -> bool:
    """Send at most one reminder per day. `send(title, message)` must return True on success."""
    today = today or date.today()
    settings = storage.load()["settings"]
    if not settings.get("notifications", True):
        return False
    if settings.get("last_notified") == today.isoformat():
        return False
    items = due_soon(today)
    if not items:
        return False
    count = len(items)
    title = "1 deadline needs attention" if count == 1 else f"{count} deadlines need attention"
    if not send(title, build_message(items, today)):
        return False
    data = storage.load()
    data["settings"]["last_notified"] = today.isoformat()
    storage.save(data)
    return True