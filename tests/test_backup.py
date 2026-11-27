import json
from datetime import date, datetime, timezone

import pytest
from typer.testing import CliRunner

from studykit import backup, deadlines, exams, ics, storage
from studykit.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def fill():
    deadlines.add_deadline("Math homework", "Math", date(2026, 12, 1))
    done = deadlines.add_deadline("Old reading", "History", date(2026, 11, 20))
    deadlines.mark_done(done["id"])
    exams.add_exam("Networks", date(2026, 12, 10), ["TCP, UDP", "DNS"])


# ---------- backup ----------


def test_export_then_import_into_empty_data(tmp_path):
    fill()
    file = tmp_path / "backup.json"
    assert backup.export_data(file) == {"deadlines": 2, "exams": 1}
    (tmp_path / "data.json").unlink()
    result = backup.import_data(file)
    assert result == {"deadlines": 2, "exams": 1, "skipped": 0}
    titles = [d["title"] for d in deadlines.list_deadlines(include_done=True)]
    assert titles == ["Old reading", "Math homework"]
    assert deadlines.list_finished()[0]["title"] == "Old reading"
    assert storage.load()["subjects"] == ["Math", "History", "Networks"]


def test_backup_leaves_out_settings(tmp_path):
    data = storage.load()
    data["settings"]["theme"] = "dark"
    storage.save(data)
    file = tmp_path / "backup.json"
    backup.export_data(file)
    assert "settings" not in json.loads(file.read_text(encoding="utf-8"))


def test_merge_skips_what_is_already_there(tmp_path):
    fill()
    file = tmp_path / "backup.json"
    backup.export_data(file)
    deadlines.add_deadline("Brand new", "", date(2026, 12, 5))
    result = backup.import_data(file)
    assert result == {"deadlines": 0, "exams": 0, "skipped": 3}
    assert len(deadlines.list_deadlines(include_done=True)) == 3


def test_merge_gives_new_ids_and_keeps_old_ones(tmp_path):
    fill()
    file = tmp_path / "backup.json"
    backup.export_data(file)
    data = json.loads(file.read_text(encoding="utf-8"))
    data["deadlines"].append({"id": 1, "title": "Other", "subject": "", "due": "2026-12-09"})
    file.write_text(json.dumps(data), encoding="utf-8")
    backup.import_data(file)
    ids = [d["id"] for d in deadlines.list_deadlines(include_done=True)]
    assert len(ids) == len(set(ids)) == 3


def test_replace_swaps_everything_and_keeps_a_copy(tmp_path):
    fill()
    file = tmp_path / "backup.json"
    backup.export_data(file)
    deadlines.add_deadline("Will disappear", "", date(2026, 12, 5))
    backup.import_data(file, replace=True)
    titles = [d["title"] for d in deadlines.list_deadlines(include_done=True)]
    assert "Will disappear" not in titles and len(titles) == 2
    copies = list(tmp_path.glob("data.json.before-import-*"))
    assert len(copies) == 1
    assert "Will disappear" in copies[0].read_text(encoding="utf-8")


def test_replace_keeps_settings(tmp_path):
    fill()
    file = tmp_path / "backup.json"
    backup.export_data(file)
    data = storage.load()
    data["settings"]["theme"] = "dark"
    storage.save(data)
    backup.import_data(file, replace=True)
    assert storage.load()["settings"]["theme"] == "dark"


def test_plain_data_file_can_be_imported(tmp_path):
    fill()
    backup.import_data(tmp_path / "data.json", replace=True)  # data.json has no 'format' key
    assert len(deadlines.list_deadlines(include_done=True)) == 2


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not json at all", "not a readable backup"),
        ("[1, 2]", "not a study-kit backup"),
        ('{"format": "something-else"}', "not a study-kit backup"),
        ('{"format": "study-kit-backup", "version": 99}', "newer study-kit"),
        ('{"deadlines": [{"title": "", "due": "2026-12-01"}]}', "Deadline 1: it needs a title"),
        ('{"deadlines": [{"title": "x", "due": "01/12/2026"}]}', "Deadline 1: the date"),
        (
            '{"exams": [{"subject": "x", "date": "2026-12-01", "topics": []}]}',
            "Exam 1: it needs at least",
        ),
        (
            '{"exams": [{"subject": "x", "date": "2026-12-01", "topics": "TCP"}]}',
            "Exam 1: the topics",
        ),
    ],
)
def test_bad_files_are_rejected_and_change_nothing(tmp_path, content, message):
    fill()
    before = (tmp_path / "data.json").read_text(encoding="utf-8")
    file = tmp_path / "bad.json"
    file.write_text(content, encoding="utf-8")
    with pytest.raises(backup.BackupError, match=message):
        backup.import_data(file, replace=True)
    assert (tmp_path / "data.json").read_text(encoding="utf-8") == before
    assert not list(tmp_path.glob("data.json.before-import-*"))


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(backup.BackupError, match="File not found"):
        backup.import_data(tmp_path / "nope.json")


# ---------- calendar ----------

NOW = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)


def test_calendar_has_deadlines_and_exams_but_not_finished_ones():
    fill()
    text, count = ics.build_calendar(now=NOW)
    assert count == 2
    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "SUMMARY:Math homework (Math)\r\n" in text
    assert "DTSTART;VALUE=DATE:20261201\r\nDTEND;VALUE=DATE:20261202\r\n" in text
    assert "SUMMARY:Exam: Networks\r\n" in text
    assert "DESCRIPTION:Topics: TCP\\, UDP\\, DNS\r\n" in text
    assert "DTSTAMP:20261127T120000Z" in text
    assert "Old reading" not in text


def test_calendar_options():
    fill()
    text, count = ics.build_calendar(include_done=True, include_exams=False, now=NOW)
    assert count == 2
    assert "SUMMARY:[done] Old reading (History)" in text
    assert "Exam" not in text


def test_calendar_ids_are_stable_and_unique():
    fill()
    first, _ = ics.build_calendar(now=NOW)
    second, _ = ics.build_calendar(now=NOW)
    assert first == second
    uids = [line for line in first.split("\r\n") if line.startswith("UID:")]
    assert len(uids) == len(set(uids)) == 2


def test_escape_text():
    assert ics.escape_text("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"


def test_long_lines_are_folded_without_breaking_characters():
    line = "SUMMARY:" + "Ж한" * 40
    folded = ics.fold(line)
    parts = folded.split("\r\n")
    assert all(len(part.encode("utf-8")) <= 75 for part in parts)
    assert all(part.startswith(" ") for part in parts[1:])
    assert "".join([parts[0]] + [p[1:] for p in parts[1:]]) == line


def test_empty_calendar_is_still_valid(tmp_path):
    file = tmp_path / "empty.ics"
    assert ics.export_ics(file) == 0
    assert file.read_bytes().startswith(b"BEGIN:VCALENDAR\r\n")


# ---------- command line ----------


def test_cli_export_import_and_ics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # short file names keep the printed lines from wrapping
    runner.invoke(app, ["add", "Essay", "--due", "2026-12-01", "--subject", "Hist"])
    assert "1 deadlines" in runner.invoke(app, ["export", "b.json"]).output
    again = runner.invoke(app, ["import", "b.json"]).output
    assert "0 deadlines" in again and "1 already there" in again
    assert "1 events" in runner.invoke(app, ["ics", "s.ics"]).output
    assert (tmp_path / "s.ics").exists()


def test_cli_import_reports_a_bad_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bad.json").write_text("nope", encoding="utf-8")
    result = runner.invoke(app, ["import", "bad.json"])
    assert result.exit_code == 1
    assert "not a readable backup" in result.output
