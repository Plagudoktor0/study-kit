from datetime import date

import pytest

from studykit import deadlines, reminders

TODAY = date(2026, 11, 24)


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def test_due_soon_includes_overdue_today_tomorrow_only():
    deadlines.add_deadline("overdue", "", date(2026, 11, 22))
    deadlines.add_deadline("today", "", date(2026, 11, 24))
    deadlines.add_deadline("tomorrow", "", date(2026, 11, 25))
    deadlines.add_deadline("later", "", date(2026, 11, 28))
    titles = [d["title"] for d in reminders.due_soon(TODAY)]
    assert titles == ["overdue", "today", "tomorrow"]


def test_due_soon_skips_finished():
    deadlines.add_deadline("A", "", date(2026, 11, 24))
    deadlines.mark_done(1)
    assert reminders.due_soon(TODAY) == []


def test_build_message_lines_and_limit():
    items = [
        {"title": "A", "subject": "OS", "due": "2026-11-22"},
        {"title": "B", "subject": "", "due": "2026-11-24"},
        {"title": "C", "subject": "", "due": "2026-11-25"},
        {"title": "D", "subject": "", "due": "2026-11-25"},
    ]
    lines = reminders.build_message(items, TODAY).split("\n")
    assert lines == [
        "A (OS): overdue 2 d",
        "B: due today",
        "C: due tomorrow",
        "...and 1 more",
    ]


def test_check_sends_once_per_day():
    deadlines.add_deadline("A", "", date(2026, 11, 25))
    sent = []
    fake = lambda title, message: sent.append((title, message)) or True
    assert reminders.check_and_notify(fake, TODAY) is True
    assert reminders.check_and_notify(fake, TODAY) is False
    assert len(sent) == 1
    assert reminders.check_and_notify(fake, date(2026, 11, 25)) is True


def test_nothing_due_soon_sends_nothing():
    deadlines.add_deadline("A", "", date(2026, 12, 20))
    assert reminders.check_and_notify(lambda t, m: True, TODAY) is False


def test_disabled_notifications_send_nothing():
    deadlines.add_deadline("A", "", date(2026, 11, 24))
    reminders.set_enabled(False)
    assert reminders.check_and_notify(lambda t, m: True, TODAY) is False


def test_failed_send_is_not_marked_as_notified():
    deadlines.add_deadline("A", "", date(2026, 11, 24))
    assert reminders.check_and_notify(lambda t, m: False, TODAY) is False
    assert reminders.check_and_notify(lambda t, m: True, TODAY) is True
