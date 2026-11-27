from datetime import date

import pytest
from typer.testing import CliRunner

from studykit import deadlines
from studykit.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def make_items():
    return [
        {"id": 1, "title": "Math homework", "subject": "Math", "due": "2026-12-01", "done": False},
        {"id": 2, "title": "Lab report", "subject": "Physics", "due": "2026-12-02", "done": False},
        {"id": 3, "title": "Read math notes", "subject": "", "due": "2026-12-03", "done": False},
    ]


def ids(items):
    return [item["id"] for item in items]


def test_no_filter_keeps_everything():
    assert ids(deadlines.filter_items(make_items())) == [1, 2, 3]
    assert ids(deadlines.filter_items(make_items(), "  ", " ")) == [1, 2, 3]


def test_search_matches_title_or_subject_ignoring_case():
    assert ids(deadlines.filter_items(make_items(), "MATH")) == [1, 3]  # title and subject
    assert ids(deadlines.filter_items(make_items(), "phys")) == [2]  # subject only
    assert ids(deadlines.filter_items(make_items(), "lab")) == [2]  # title only


def test_subject_filter_is_exact_and_ignores_case():
    assert ids(deadlines.filter_items(make_items(), subject="math")) == [1]
    assert ids(deadlines.filter_items(make_items(), subject="Mat")) == []


def test_search_and_subject_work_together():
    assert ids(deadlines.filter_items(make_items(), "report", "Physics")) == [2]
    assert ids(deadlines.filter_items(make_items(), "report", "Math")) == []


def test_used_subjects_are_sorted_unique_and_skip_empty():
    deadlines.add_deadline("a", "physics", date(2026, 12, 1))
    deadlines.add_deadline("b", "Math", date(2026, 12, 1))
    deadlines.add_deadline("c", "Physics", date(2026, 12, 1))
    deadlines.add_deadline("d", "", date(2026, 12, 1))
    assert deadlines.used_subjects() == ["Math", "physics"]


def test_used_subjects_include_finished_deadlines():
    item = deadlines.add_deadline("a", "History", date(2026, 12, 1))
    deadlines.mark_done(item["id"])
    assert deadlines.used_subjects() == ["History"]


def test_cli_list_filters_by_subject_and_search():
    runner.invoke(app, ["add", "Essay", "--due", "2026-12-01", "--subject", "Hist"])
    runner.invoke(app, ["add", "Lab", "--due", "2026-12-02", "--subject", "Phys"])
    by_subject = runner.invoke(app, ["list", "--subject", "phys"]).output
    assert "Lab" in by_subject and "Essay" not in by_subject
    by_search = runner.invoke(app, ["list", "-q", "ess"]).output
    assert "Essay" in by_search and "Lab" not in by_search


def test_cli_list_says_when_nothing_matches():
    runner.invoke(app, ["add", "Essay", "--due", "2026-12-01"])
    assert "No deadlines match this filter" in runner.invoke(app, ["list", "-q", "zzz"]).output
