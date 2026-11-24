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