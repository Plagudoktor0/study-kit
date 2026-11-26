from datetime import date, timedelta

from studykit import storage


def parse_topics(text: str) -> list[str]:
    """Split 'a, b, c' (commas or new lines) into a clean list of topics."""
    parts = text.replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


def add_exam(subject: str, exam_date: date, topics: list[str]) -> dict:
    data = storage.load()
    items = data["exams"]
    new_id = max((e["id"] for e in items), default=0) + 1
    item = {
        "id": new_id,
        "subject": subject,
        "date": exam_date.isoformat(),
        "topics": topics,
    }
    items.append(item)
    storage.save(data)
    return item


def list_exams() -> list[dict]:
    """All exams, closest date first."""
    return sorted(storage.load()["exams"], key=lambda e: e["date"])


def delete_exam(exam_id: int) -> bool:
    data = storage.load()
    remaining = [e for e in data["exams"] if e["id"] != exam_id]
    if len(remaining) == len(data["exams"]):
        return False
    data["exams"] = remaining
    storage.save(data)
    return True


def make_plan(
    topics: list[str], exam_date: date, today: date | None = None
) -> list[tuple[date, list[str]]]:
    """Spread topics over the days from today to the day before the exam.

    Returns [(day, [topics for that day]), ...], only for days that have topics.
    """
    today = today or date.today()
    study_days = (exam_date - today).days
    if study_days <= 0 or not topics:
        return []
    by_offset: dict[int, list[str]] = {}
    for k, topic in enumerate(topics):
        offset = k * study_days // len(topics)
        by_offset.setdefault(offset, []).append(topic)
    return [(today + timedelta(days=offset), by_offset[offset]) for offset in sorted(by_offset)]