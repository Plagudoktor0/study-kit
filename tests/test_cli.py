from datetime import date, timedelta

import pytest
from pypdf import PdfReader, PdfWriter
from typer.testing import CliRunner

from studykit.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


def blank_pdf(path, pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def test_delete_and_restore_deadline():
    runner.invoke(app, ["add", "Essay", "--due", "2026-12-01"])
    runner.invoke(app, ["done", "1"])
    assert "Restored" in runner.invoke(app, ["restore", "1"]).output
    assert "Deleted" in runner.invoke(app, ["delete", "1"]).output
    assert runner.invoke(app, ["delete", "1"]).exit_code == 1


def test_exam_add_list_plan_delete():
    exam_day = (date.today() + timedelta(days=6)).isoformat()
    result = runner.invoke(app, ["exam", "add", "Networks", "-d", exam_day, "-t", "TCP, UDP, DNS"])
    assert result.exit_code == 0
    assert "Networks" in runner.invoke(app, ["exam", "list"]).output
    plan = runner.invoke(app, ["exam", "plan", "1"])
    assert plan.exit_code == 0 and "EXAM" in plan.output and "TCP" in plan.output
    assert runner.invoke(app, ["exam", "delete", "1"]).exit_code == 0
    assert runner.invoke(app, ["exam", "plan", "1"]).exit_code == 1


def test_exam_plan_fails_for_unknown_id():
    assert runner.invoke(app, ["exam", "plan", "99"]).exit_code == 1


def test_pdf_merge_split_rotate_text(tmp_path):
    a = blank_pdf(tmp_path / "a.pdf", 2)
    b = blank_pdf(tmp_path / "b.pdf", 3)
    merged = tmp_path / "ab.pdf"
    assert runner.invoke(app, ["pdf", "merge", str(a), str(b), "-o", str(merged)]).exit_code == 0
    assert len(PdfReader(str(merged)).pages) == 5

    part = tmp_path / "part.pdf"
    assert (
        runner.invoke(app, ["pdf", "split", str(merged), "-p", "2-3", "-o", str(part)]).exit_code
        == 0
    )
    assert len(PdfReader(str(part)).pages) == 2

    rotated = tmp_path / "rot.pdf"
    assert (
        runner.invoke(app, ["pdf", "rotate", str(part), "-a", "90", "-o", str(rotated)]).exit_code
        == 0
    )
    assert PdfReader(str(rotated)).pages[0].rotation == 90

    text = runner.invoke(app, ["pdf", "text", str(part)])
    assert text.exit_code == 0 and "No text found" in text.output
    assert (tmp_path / "part.txt").exists()


def test_pdf_errors_are_readable(tmp_path):
    result = runner.invoke(app, ["pdf", "split", str(tmp_path / "nope.pdf"), "-p", "1"])
    assert result.exit_code == 1 and "File not found" in result.output
    one = blank_pdf(tmp_path / "one.pdf", 1)
    result = runner.invoke(app, ["pdf", "split", str(one), "-p", "5"])
    assert result.exit_code == 1 and "outside the document" in result.output
    result = runner.invoke(app, ["pdf", "merge", str(one), "-o", str(tmp_path / "x.pdf")])
    assert result.exit_code == 1 and "at least two" in result.output
