from datetime import date

from studykit import storage, timeleft


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


def filter_items(items: list[dict], query: str = "", subject: str = "") -> list[dict]:
    """Keep deadlines whose title or subject contains `query`, and whose subject is `subject`.

    Both checks ignore upper/lower case. An empty `query` or `subject` means 'no filter'.
    """
    query = query.strip().lower()
    subject = subject.strip().lower()
    result = []
    for item in items:
        item_subject = item["subject"].lower()
        if subject and item_subject != subject:
            continue
        if query and query not in item["title"].lower() and query not in item_subject:
            continue
        result.append(item)
    return result


def used_subjects() -> list[str]:
    """Subjects that appear on at least one deadline, A to Z, without case-only duplicates."""
    names: dict[str, str] = {}
    for item in storage.load()["deadlines"]:
        name = item["subject"].strip()
        if name:
            names.setdefault(name.lower(), name)
    return sorted(names.values(), key=str.lower)


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
    return timeleft.days_until(item["due"])


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
        left = timeleft.days_until(item["due"], today)
        if left < 0:
            overdue += 1
        elif left <= 7:
            week += 1
    return {"overdue": overdue, "week": week, "finished": len(items) - len(active)}
