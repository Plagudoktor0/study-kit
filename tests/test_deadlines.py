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