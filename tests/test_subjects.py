import json

import pytest

from studykit import storage, subjects


@pytest.fixture(autouse=True)
def temp_data(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def test_add_and_list_sorted_ignoring_case():
    subjects.add_subject("OS")
    subjects.add_subject("calculus")
    subjects.add_subject("Algorithms")
    assert subjects.list_subjects() == ["Algorithms", "calculus", "OS"]


def test_duplicates_ignored_case_insensitive():
    assert subjects.add_subject("OS") is True
    assert subjects.add_subject("os") is False
    assert subjects.list_subjects() == ["OS"]


def test_empty_name_ignored():
    assert subjects.add_subject("   ") is False
    assert subjects.list_subjects() == []


def test_old_data_file_without_subjects_still_loads():
    old = {"deadlines": [], "exams": []}
    storage.data_path().write_text(json.dumps(old), encoding="utf-8")
    assert subjects.list_subjects() == []
    assert storage.load()["subjects"] == []
