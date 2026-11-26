from datetime import date

from studykit import storage


def add_deadline(title: str, subject: str, due: date) -> dict:
    """Create a new deadline, save it, and return it."""
    data = storage.load()
    items = data["deadlines"]
    new_id = max((d["id"] for d in items), default=0) + 1
    item = {
        "id": new_id,
        "title": title,
        "subject": subject,
        "due": due.isoformat(),  # stored as text like "2026-12-01"
        "done": False,
    }
    items.append(item)
    storage.save(data)
    return item


def list_deadlines(include_done: bool = False) -> list[dict]:
    """Return deadlines sorted by due date. Hides finished ones by default."""
    items = storage.load()["deadlines"]
    if not include_done:
        items = [d for d in items if not d["done"]]
    return sorted(items, key=lambda d: d["due"])

def mark_done(deadline_id: int) -> dict | None:
    """Mark a deadline as finished. Returns it, or None if the ID doesn't exist."""
    data = storage.load()
    for item in data["deadlines"]:
        if item["id"] == deadline_id:
            item["done"] = True
            storage.save(data)
            return item
    return None


def next_deadline() -> dict | None:
    """Return the closest unfinished deadline, or None if there are none."""
    items = list_deadlines()
    return items[0] if items else None


def days_left(item: dict) -> int:
    """Days from today until the due date (negative means overdue)."""
    return (date.fromisoformat(item["due"]) - date.today()).days

def delete_deadline(deadline_id: int) -> bool:
    """Remove a deadline completely. Returns False if the ID doesn't exist."""
    data = storage.load()
    remaining = [d for d in data["deadlines"] if d["id"] != deadline_id]
    if len(remaining) == len(data["deadlines"]):
        return False
    data["deadlines"] = remaining
    storage.save(data)
    return True    

def list_finished() -> list[dict]:
    """Return finished deadlines, newest due date first."""
    items = [d for d in storage.load()["deadlines"] if d["done"]]
    return sorted(items, key=lambda d: d["due"], reverse=True)


def restore_deadline(deadline_id: int) -> dict | None:
    """Move a finished deadline back to the active list."""
    data = storage.load()
    for item in data["deadlines"]:
        if item["id"] == deadline_id:
            item["done"] = False
            storage.save(data)
            return item
    return None    

def update_deadline(deadline_id: int, title: str, subject: str, due: date) -> dict | None:
    """Change title, subject and due date. Returns None if the ID doesn't exist."""
    data = storage.load()
    for item in data["deadlines"]:
        if item["id"] == deadline_id:
            item["title"] = title
            item["subject"] = subject
            item["due"] = due.isoformat()
            storage.save(data)
            return item
    return None

def summary(today: date | None = None) -> dict:
    """Counts for the dashboard cards. 'week' means due today up to 7 days ahead."""
    today = today or date.today()
    items = storage.load()["deadlines"]
    active = [d for d in items if not d["done"]]
    overdue = 0
    week = 0
    for item in active:
        left = (date.fromisoformat(item["due"]) - today).days
        if left < 0:
            overdue += 1
        elif left <= 7:
            week += 1
    return {"overdue": overdue, "week": week, "finished": len(items) - len(active)}