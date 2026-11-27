"""Write deadlines and exams to an .ics calendar file (Google Calendar, Outlook, Apple Calendar)."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from studykit import storage


def escape_text(text: str) -> str:
    """Escape the characters that have a special meaning in an .ics text value."""
    text = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def fold(line: str) -> str:
    """Split a long line into pieces of at most 75 bytes, never cutting a character in half."""
    pieces = []
    current = ""
    size = 0
    limit = 75
    for char in line:
        char_size = len(char.encode("utf-8"))
        if size + char_size > limit:
            pieces.append(current)
            current, size, limit = "", 0, 74  # continuation lines start with one space
        current += char
        size += char_size
    pieces.append(current)
    return "\r\n ".join(pieces)


def _all_day(day: str) -> tuple[str, str]:
    start = date.fromisoformat(day)
    return start.strftime("%Y%m%d"), (start + timedelta(days=1)).strftime("%Y%m%d")


def _event(uid: str, stamp: str, day: str, summary: str, description: str = "") -> list[str]:
    start, end = _all_day(day)
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{start}",
        f"DTEND;VALUE=DATE:{end}",
        f"SUMMARY:{escape_text(summary)}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{escape_text(description)}")
    lines.append("END:VEVENT")
    return lines


def build_calendar(
    include_done: bool = False, include_exams: bool = True, now: datetime | None = None
) -> tuple[str, int]:
    """Return the text of the calendar and how many events it has."""
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    data = storage.load()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//study-kit//EN", "CALSCALE:GREGORIAN"]
    count = 0

    for item in sorted(data["deadlines"], key=lambda d: d["due"]):
        if item["done"] and not include_done:
            continue
        subject = f" ({item['subject']})" if item["subject"] else ""
        summary = f"{'[done] ' if item['done'] else ''}{item['title']}{subject}"
        lines += _event(f"deadline-{item['id']}@study-kit", stamp, item["due"], summary)
        count += 1

    if include_exams:
        for exam in sorted(data["exams"], key=lambda e: e["date"]):
            topics = f"Topics: {', '.join(exam['topics'])}"
            lines += _event(
                f"exam-{exam['id']}@study-kit",
                stamp,
                exam["date"],
                f"Exam: {exam['subject']}",
                topics,
            )
            count += 1

    lines.append("END:VCALENDAR")
    text = "".join(fold(line) + "\r\n" for line in lines)
    return text, count


def export_ics(path, include_done: bool = False, include_exams: bool = True) -> int:
    """Write the calendar file. Returns the number of events."""
    text, count = build_calendar(include_done, include_exams)
    Path(path).write_bytes(text.encode("utf-8"))
    return count
