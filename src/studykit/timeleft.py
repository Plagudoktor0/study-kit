"""One place that decides how 'days left' is calculated and shown.

Used by the window, the command line and the reminders, so they always agree.
"""

from datetime import date

SOON_DAYS = 3  # a deadline this close (or closer) is shown in orange


def days_until(day: date | str, today: date | None = None) -> int:
    """Days from `today` to `day` (a date or an ISO text like '2026-12-01'). Negative = past."""
    if isinstance(day, str):
        day = date.fromisoformat(day)
    return (day - (today or date.today())).days


def _upcoming(days: int) -> tuple[str, str]:
    """(text, color tag) for today or a future day. The tag is '' for 'no special color'."""
    if days == 0:
        return "today", "soon"
    return f"in {days} d", "soon" if days <= SOON_DAYS else ""


def deadline_label(days: int) -> tuple[str, str]:
    """Text and row tag for a deadline: 'overdue 2 d', 'today', 'in 5 d'."""
    if days < 0:
        return f"overdue {-days} d", "overdue"
    return _upcoming(days)


def exam_label(days: int) -> tuple[str, str]:
    """Text and row tag for an exam: 'passed', 'today', 'in 5 d'."""
    if days < 0:
        return "passed", "finished"
    return _upcoming(days)
