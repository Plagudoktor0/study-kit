from datetime import date, timedelta

import pytest

from studykit import deadlines


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    """Every test gets its own empty data file, so your real data is never touched."""
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def test_add_assigns_incrementing_ids():
    first = deadlines.add_deadline("A", "OS", date(2026, 12, 1))
    second = deadlines.add_deadline("B", "OS", date(2026, 12, 2))
    assert first["id"] == 1
    assert second["id"] == 2


def test_list_is_sorted_by_due_date():
    deadlines.add_deadline("late", "", date(2026, 12, 20))
    deadlines.add_deadline("early", "", date(2026, 11, 28))
    titles = [d["title"] for d in deadlines.list_deadlines()]
    assert titles == ["early", "late"]


def test_list_hides_done_by_default():
    deadlines.add_deadline("A", "", date(2026, 12, 1))
    deadlines.add_deadline("B", "", date(2026, 12, 2))
    deadlines.mark_done(1)
    assert len(deadlines.list_deadlines()) == 1
    assert len(deadlines.list_deadlines(include_done=True)) == 2


def test_mark_done_saves_the_change():
    deadlines.add_deadline("A", "", date(2026, 12, 1))
    item = deadlines.mark_done(1)
    assert item["done"] is True
    assert deadlines.list_deadlines(include_done=True)[0]["done"] is True


def test_mark_done_unknown_id_returns_none():
    assert deadlines.mark_done(99) is None


def test_next_deadline_returns_closest():
    deadlines.add_deadline("far", "", date(2026, 12, 20))
    deadlines.add_deadline("near", "", date(2026, 11, 28))
    assert deadlines.next_deadline()["title"] == "near"


def test_next_deadline_when_empty():
    assert deadlines.next_deadline() is None


def test_days_left():
    in_five_days = {"due": (date.today() + timedelta(days=5)).isoformat()}
    two_days_ago = {"due": (date.today() - timedelta(days=2)).isoformat()}
    assert deadlines.days_left(in_five_days) == 5
    assert deadlines.days_left(two_days_ago) == -2

def test_delete_removes_only_that_deadline():
    deadlines.add_deadline("A", "", date(2026, 12, 1))
    deadlines.add_deadline("B", "", date(2026, 12, 2))
    assert deadlines.delete_deadline(1) is True
    titles = [d["title"] for d in deadlines.list_deadlines(include_done=True)]
    assert titles == ["B"]


def test_delete_unknown_id_returns_false():
    assert deadlines.delete_deadline(99) is False   

def test_list_finished_only_returns_done_items():
    deadlines.add_deadline("A", "", date(2026, 12, 1))
    deadlines.add_deadline("B", "", date(2026, 12, 2))
    deadlines.mark_done(1)
    titles = [d["title"] for d in deadlines.list_finished()]
    assert titles == ["A"]


def test_restore_moves_item_back_to_active_list():
    deadlines.add_deadline("A", "", date(2026, 12, 1))
    deadlines.mark_done(1)
    assert deadlines.list_deadlines() == []
    deadlines.restore_deadline(1)
    assert [d["title"] for d in deadlines.list_deadlines()] == ["A"]
    assert deadlines.list_finished() == []


def test_restore_unknown_id_returns_none():
    assert deadlines.restore_deadline(99) is None  

def test_update_changes_fields():
    deadlines.add_deadline("A", "OS", date(2026, 12, 1))
    item = deadlines.update_deadline(1, "B", "Calculus", date(2026, 12, 5))
    assert item["title"] == "B"
    stored = deadlines.list_deadlines()[0]
    assert stored["subject"] == "Calculus"
    assert stored["due"] == "2026-12-05"


def test_update_keeps_done_status():
    deadlines.add_deadline("A", "", date(2026, 12, 1))
    deadlines.mark_done(1)
    deadlines.update_deadline(1, "A2", "", date(2026, 12, 2))
    assert deadlines.list_finished()[0]["title"] == "A2"


def test_update_unknown_id_returns_none():
    assert deadlines.update_deadline(99, "x", "", date(2026, 12, 1)) is None    

def test_summary_counts():
    today = date(2026, 11, 24)
    deadlines.add_deadline("late", "", date(2026, 11, 20))
    deadlines.add_deadline("today", "", date(2026, 11, 24))
    deadlines.add_deadline("in 7 days", "", date(2026, 12, 1))
    deadlines.add_deadline("in 8 days", "", date(2026, 12, 2))
    deadlines.add_deadline("finished", "", date(2026, 11, 25))
    deadlines.mark_done(5)
    assert deadlines.summary(today) == {"overdue": 1, "week": 2, "finished": 1}


def test_summary_when_empty():
    assert deadlines.summary(date(2026, 11, 24)) == {"overdue": 0, "week": 0, "finished": 0}      