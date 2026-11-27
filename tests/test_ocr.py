import os
import sys
import threading

import pytest
from typer.testing import CliRunner

from studykit import ocr, pdf_tools
from studykit.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYKIT_DATA", str(tmp_path / "data.json"))


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class FakeReader:
    def __init__(self, texts):
        self.pages = [FakePage(t) for t in texts]


@pytest.fixture
def fake_pdf(monkeypatch):
    """Pretend the PDF has these pages; every OCR call is recorded in `calls`."""
    calls = []

    def setup(texts):
        monkeypatch.setattr(pdf_tools, "open_pdf", lambda path: FakeReader(texts))
        monkeypatch.setattr(ocr, "_open_document", lambda path: object())
        monkeypatch.setattr(ocr, "render_page", lambda document, index: index)

        def fake_recognize(image, lang):
            calls.append((image, lang))
            return f"picture text {image + 1} ({lang})"

        monkeypatch.setattr(ocr, "recognize", fake_recognize)
        return calls

    return setup


TYPED = "This page has plenty of typed text on it."


def test_ocr_errors_are_pdf_tool_errors():
    assert issubclass(ocr.OcrError, pdf_tools.PdfToolError)
    assert issubclass(ocr.OcrNotInstalled, ocr.OcrError)


def test_only_pages_without_text_are_read_with_ocr(tmp_path, fake_pdf):
    calls = fake_pdf([TYPED, "", "ab"])
    out = tmp_path / "out.txt"
    result = ocr.extract_text_ocr("x.pdf", out, lang="ko")
    assert [index for index, _ in calls] == [1, 2]  # page 1 has typed text
    text = out.read_text(encoding="utf-8")
    assert f"--- Page 1 ---\n{TYPED}" in text
    assert "--- Page 2 ---\npicture text 2 (ko)" in text
    assert "--- Page 3 ---\npicture text 3 (ko)" in text
    assert result == {
        "characters": len(TYPED) + 2 * len("picture text 2 (ko)"),
        "pages": 3,
        "ocr_pages": 2,
    }


def test_force_reads_every_page_as_a_picture(tmp_path, fake_pdf):
    calls = fake_pdf([TYPED, TYPED])
    result = ocr.extract_text_ocr("x.pdf", tmp_path / "out.txt", force=True)
    assert len(calls) == 2
    assert result["ocr_pages"] == 2


def test_no_ocr_is_started_when_every_page_has_text(tmp_path, fake_pdf, monkeypatch):
    calls = fake_pdf([TYPED, TYPED])

    def must_not_open(path):
        raise AssertionError("the page renderer should not be needed")

    monkeypatch.setattr(ocr, "_open_document", must_not_open)
    result = ocr.extract_text_ocr("x.pdf", tmp_path / "out.txt")
    assert calls == [] and result["ocr_pages"] == 0


def test_progress_is_reported_after_each_page(tmp_path, fake_pdf):
    fake_pdf(["", "", ""])
    seen = []
    ocr.extract_text_ocr("x.pdf", tmp_path / "out.txt", progress=lambda d, n: seen.append((d, n)))
    assert seen == [(1, 3), (2, 3), (3, 3)]


def test_cancel_stops_and_writes_nothing(tmp_path, fake_pdf):
    fake_pdf(["", "", ""])
    cancel = threading.Event()
    out = tmp_path / "out.txt"

    def stop_after_first(done, total):
        cancel.set()

    with pytest.raises(ocr.OcrCancelled):
        ocr.extract_text_ocr("x.pdf", out, progress=stop_after_first, cancel=cancel)
    assert not out.exists()


def test_unknown_language_is_rejected():
    with pytest.raises(ocr.OcrError, match="Unknown language"):
        ocr._engine("xx")


def test_missing_packages_give_a_clear_message(monkeypatch):
    monkeypatch.setitem(sys.modules, "rapidocr", None)  # makes 'import rapidocr' fail
    monkeypatch.setitem(sys.modules, "pypdfium2", None)
    with pytest.raises(ocr.OcrNotInstalled, match=r"pip install"):
        ocr._engine("en")
    with pytest.raises(ocr.OcrNotInstalled, match=r"pip install"):
        ocr._open_document("x.pdf")


def test_models_are_kept_next_to_the_data_file(tmp_path):
    assert ocr.models_dir() == tmp_path / "models"


# ---------- command line ----------


def test_cli_ocr_option(tmp_path, fake_pdf, monkeypatch):
    fake_pdf(["", TYPED])
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["pdf", "text", "s.pdf", "--ocr", "--lang", "ru", "-o", "o.txt"])
    assert result.exit_code == 0, result.output
    assert "1 of 2 pages read with OCR" in result.output.replace("\n", " ")
    assert "(ru)" in (tmp_path / "o.txt").read_text(encoding="utf-8")


def test_cli_ocr_rejects_unknown_language(tmp_path, fake_pdf, monkeypatch):
    fake_pdf([""])
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["pdf", "text", "s.pdf", "--ocr", "--lang", "xx"])
    assert result.exit_code == 1 and "Unknown language" in result.output


def test_cli_ocr_not_installed_is_a_clean_error(tmp_path, fake_pdf, monkeypatch):
    fake_pdf([""])

    def not_installed(path):
        raise ocr.OcrNotInstalled('OCR is not installed. Run:  pip install "study-kit[ocr]"')

    monkeypatch.setattr(ocr, "_open_document", not_installed)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["pdf", "text", "s.pdf", "--ocr"])
    assert result.exit_code == 1 and "not installed" in result.output


def test_cli_plain_text_without_text_suggests_ocr(tmp_path, monkeypatch):
    from pypdf import PdfWriter

    monkeypatch.chdir(tmp_path)
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open("blank.pdf", "wb") as handle:
        writer.write(handle)
    result = runner.invoke(app, ["pdf", "text", "blank.pdf"])
    assert result.exit_code == 0 and "--ocr" in result.output


# ---------- the real thing (needs the OCR packages and internet; off by default) ----------


@pytest.mark.skipif(
    os.environ.get("STUDYKIT_OCR_TESTS") != "1", reason="set STUDYKIT_OCR_TESTS=1 to run"
)
def test_real_ocr_reads_a_picture_only_pdf(tmp_path):
    pytest.importorskip("rapidocr")
    pytest.importorskip("pypdfium2")
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1600, 500), "white")
    ImageDraw.Draw(image).text(
        (80, 150), "Lecture 3: Transport layer", fill="black", font=ImageFont.load_default(size=70)
    )
    pdf = tmp_path / "slide.pdf"
    image.save(pdf, resolution=100)
    out = tmp_path / "slide.txt"
    result = ocr.extract_text_ocr(pdf, out, lang="en")
    assert result["ocr_pages"] == 1
    assert "Transport layer" in out.read_text(encoding="utf-8")
