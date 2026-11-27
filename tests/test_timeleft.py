from datetime import date

import pytest

from studykit import timeleft

TODAY = date(2026, 12, 1)


def test_days_until_accepts_date_and_text():
    assert timeleft.days_until(date(2026, 12, 4), TODAY) == 3
    assert timeleft.days_until("2026-12-04", TODAY) == 3
    assert timeleft.days_until("2026-12-01", TODAY) == 0
    assert timeleft.days_until("2026-11-29", TODAY) == -2


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (-2, ("overdue 2 d", "overdue")),
        (-1, ("overdue 1 d", "overdue")),
        (0, ("today", "soon")),
        (1, ("in 1 d", "soon")),
        (3, ("in 3 d", "soon")),
        (4, ("in 4 d", "")),
        (30, ("in 30 d", "")),
    ],
)
def test_deadline_label(days, expected):
    assert timeleft.deadline_label(days) == expected


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (-1, ("passed", "finished")),
        (0, ("today", "soon")),
        (3, ("in 3 d", "soon")),
        (4, ("in 4 d", "")),
    ],
)
def test_exam_label(days, expected):
    assert timeleft.exam_label(days) == expected
