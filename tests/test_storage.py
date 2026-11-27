import json

import pytest

from studykit import storage


@pytest.fixture
def data_file(tmp_path, monkeypatch):
    path = tmp_path / "data.json"
    monkeypatch.setenv("STUDYKIT_DATA", str(path))
    return path


def test_load_without_a_file_gives_empty_data(data_file):
    data = storage.load()
    assert data["deadlines"] == []
    assert data["exams"] == []
    assert data["subjects"] == []
    assert data["settings"] == {}


def test_save_then_load_round_trip(data_file):
    data = storage.load()
    data["subjects"].append("Networks")
    data["settings"]["theme"] = "dark"
    storage.save(data)
    again = storage.load()
    assert again["subjects"] == ["Networks"]
    assert again["settings"]["theme"] == "dark"


def test_save_keeps_non_ascii_text_readable(data_file):
    data = storage.load()
    data["subjects"].append("Сети и 네트워크")
    storage.save(data)
    assert "Сети и 네트워크" in data_file.read_text(encoding="utf-8")


def test_save_leaves_no_temp_files_behind(data_file):
    storage.save(storage.load())
    assert [p.name for p in data_file.parent.iterdir()] == ["data.json"]


def test_failed_save_keeps_the_old_file(data_file):
    storage.save({"deadlines": [{"id": 1}]})
    with pytest.raises(TypeError):
        storage.save({"bad": object()})  # cannot be turned into JSON
    assert json.loads(data_file.read_text(encoding="utf-8")) == {"deadlines": [{"id": 1}]}
    assert [p.name for p in data_file.parent.iterdir()] == ["data.json"]


def test_damaged_file_is_backed_up_and_data_starts_empty(data_file):
    data_file.write_text('{"deadlines": [', encoding="utf-8")  # cut off in the middle
    data = storage.load()
    assert data["deadlines"] == []
    backups = list(data_file.parent.glob("data.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == '{"deadlines": ['
    assert not data_file.exists()


def test_file_with_wrong_shape_is_treated_as_damaged(data_file):
    data_file.write_text("[1, 2, 3]", encoding="utf-8")
    assert storage.load()["deadlines"] == []
    assert len(list(data_file.parent.glob("data.json.corrupt-*"))) == 1


def test_file_with_bad_encoding_is_treated_as_damaged(data_file):
    data_file.write_bytes(b"\xff\xfe\x00bad")
    assert storage.load()["subjects"] == []
    assert len(list(data_file.parent.glob("data.json.corrupt-*"))) == 1


def test_old_file_without_new_keys_still_loads(data_file):
    data_file.write_text(json.dumps({"deadlines": [{"id": 1}]}), encoding="utf-8")
    data = storage.load()
    assert data["deadlines"] == [{"id": 1}]
    assert data["exams"] == [] and data["subjects"] == [] and data["settings"] == {}
