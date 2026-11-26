from datetime import date

import pytest

from studykit import exams


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def test_plan_matches_worked_example():
    topics = ["limits", "derivatives", "integrals", "series"]
    plan = exams.make_plan(topics, date(2026, 12, 4), today=date(2026, 11, 24))
    assert plan == [
        (date(2026, 11, 24), ["limits"]),
        (date(2026, 11, 26), ["derivatives"]),
        (date(2026, 11, 29), ["integrals"]),
        (date(2026, 12, 1), ["series"]),
    ]


def test_plan_with_more_topics_than_days_groups_them():
    topics = [f"t{i}" for i in range(10)]
    plan = exams.make_plan(topics, date(2026, 11, 28), today=date(2026, 11, 24))
    assert [len(day_topics) for _, day_topics in plan] == [3, 2, 3, 2]


def test_plan_is_empty_when_exam_is_today_or_past():
    assert exams.make_plan(["a"], date(2026, 11, 24), today=date(2026, 11, 24)) == []
    assert exams.make_plan(["a"], date(2026, 11, 20), today=date(2026, 11, 24)) == []


def test_plan_is_empty_without_topics():
    assert exams.make_plan([], date(2026, 12, 4), today=date(2026, 11, 24)) == []


def test_parse_topics_handles_commas_and_new_lines():
    assert exams.parse_topics("limits, derivatives\nintegrals,, ") == [
        "limits",
        "derivatives",
        "integrals",
    ]


def test_add_list_and_delete_exam():
    exams.add_exam("OS", date(2026, 12, 10), ["threads"])
    exams.add_exam("Calculus", date(2026, 12, 2), ["series"])
    assert [e["subject"] for e in exams.list_exams()] == ["Calculus", "OS"]
    assert exams.delete_exam(1) is True
    assert exams.delete_exam(99) is False
    assert [e["subject"] for e in exams.list_exams()] == ["Calculus"]