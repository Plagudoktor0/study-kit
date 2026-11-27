import pytest
from pypdf import PdfReader, PdfWriter

from studykit import pdf_tools


def make_pdf(path, widths):
    """A PDF with one blank page per width, so every page can be told apart."""
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def page_widths(path):
    return [round(float(page.mediabox.width)) for page in PdfReader(str(path)).pages]


def test_parse_page_ranges():
    assert pdf_tools.parse_page_ranges("1-3, 5", 6) == [0, 1, 2, 4]


@pytest.mark.parametrize("text", ["0", "7", "3-1", "abc", ""])
def test_parse_page_ranges_rejects_bad_input(text):
    with pytest.raises(ValueError):
        pdf_tools.parse_page_ranges(text, 6)


def test_merge_keeps_the_given_order(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", [101, 102])
    b = make_pdf(tmp_path / "b.pdf", [103])
    pdf_tools.merge_pdfs([a, b], tmp_path / "ab.pdf")
    pdf_tools.merge_pdfs([b, a], tmp_path / "ba.pdf")
    assert page_widths(tmp_path / "ab.pdf") == [101, 102, 103]
    assert page_widths(tmp_path / "ba.pdf") == [103, 101, 102]


def test_merge_needs_two_files(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", [101])
    with pytest.raises(pdf_tools.PdfToolError):
        pdf_tools.merge_pdfs([a], tmp_path / "out.pdf")


def test_split_picks_the_requested_pages(tmp_path):
    source = make_pdf(tmp_path / "s.pdf", [101, 102, 103, 104, 105, 106])
    pdf_tools.split_pdf(source, "2-3, 6", tmp_path / "out.pdf")
    assert page_widths(tmp_path / "out.pdf") == [102, 103, 106]


def test_rotate_only_selected_pages(tmp_path):
    source = make_pdf(tmp_path / "s.pdf", [101, 102])
    pdf_tools.rotate_pdf(source, tmp_path / "out.pdf", 90, "1")
    pages = PdfReader(str(tmp_path / "out.pdf")).pages
    assert [page.rotation for page in pages] == [90, 0]


def test_rotate_rejects_odd_angles(tmp_path):
    source = make_pdf(tmp_path / "s.pdf", [101])
    with pytest.raises(pdf_tools.PdfToolError):
        pdf_tools.rotate_pdf(source, tmp_path / "out.pdf", 45)


def test_a_file_that_is_not_a_pdf_is_rejected(tmp_path):
    fake = tmp_path / "fake.pdf"
    fake.write_text("hello", encoding="utf-8")
    with pytest.raises(pdf_tools.PdfToolError):
        pdf_tools.split_pdf(fake, "1", tmp_path / "out.pdf")


def test_extract_text_reports_how_much_text_it_found(tmp_path):
    source = make_pdf(tmp_path / "s.pdf", [101, 102])
    count = pdf_tools.extract_text(source, tmp_path / "out.txt")
    assert count == 0  # blank pages have no text
    assert (tmp_path / "out.txt").exists()


def fake_reader(decrypt_result):
    """A stand-in for PdfReader that pretends the file is encrypted."""

    class FakeReader:
        is_encrypted = True
        pages = []

        def __init__(self, path):
            pass

        def decrypt(self, password):
            return decrypt_result

    return FakeReader


def test_pdf_that_needs_a_password_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_tools, "PdfReader", fake_reader(0))  # 0 = could not decrypt
    with pytest.raises(pdf_tools.PdfToolError, match="password"):
        pdf_tools.open_pdf(tmp_path / "locked.pdf")


def test_restricted_pdf_that_opens_without_a_password_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_tools, "PdfReader", fake_reader(2))  # 2 = opened with empty password
    assert pdf_tools.open_pdf(tmp_path / "restricted.pdf") is not None
