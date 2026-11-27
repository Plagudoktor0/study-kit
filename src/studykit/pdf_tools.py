from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


class PdfToolError(Exception):
    """A problem the user can understand: bad file, bad page range, and so on."""


def parse_page_ranges(text: str, total_pages: int) -> list[int]:
    """Turn '1-3, 5' into zero-based page indexes [0, 1, 2, 4]."""
    pages: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                start, end = int(start_text), int(end_text)
            else:
                start = end = int(part)
        except ValueError:
            raise ValueError(f"'{part}' is not a page number or a range like 3-5") from None
        if start < 1 or end > total_pages:
            raise ValueError(f"'{part}' is outside the document ({total_pages} pages)")
        if start > end:
            raise ValueError(f"'{part}' goes backwards")
        pages.extend(range(start - 1, end))
    if not pages:
        raise ValueError("Enter at least one page, for example 1-3, 5")
    return pages


def _can_open(reader: PdfReader) -> bool:
    """Many PDFs are 'restricted' (no copying, no printing) but open without a password."""
    try:
        return reader.decrypt("") != 0
    except Exception:  # wrong password, or an encryption this setup can't read
        return False


def open_pdf(path) -> PdfReader:
    """Open a PDF, turning every failure into a readable PdfToolError."""
    path = Path(path)
    try:
        reader = PdfReader(str(path))
    except FileNotFoundError:
        raise PdfToolError(f"File not found: {path.name}") from None
    except PdfReadError:
        raise PdfToolError(f"{path.name} is not a readable PDF") from None
    except OSError as error:
        raise PdfToolError(f"Could not open {path.name}: {error.strerror}") from None

    if reader.is_encrypted and not _can_open(reader):
        raise PdfToolError(f"{path.name} is password-protected")
    return reader


def _select(reader: PdfReader, ranges_text: str) -> list[int]:
    try:
        return parse_page_ranges(ranges_text, len(reader.pages))
    except ValueError as error:
        raise PdfToolError(str(error)) from None


def _save(writer: PdfWriter, output) -> Path:
    output = Path(output)
    try:
        with output.open("wb") as handle:
            writer.write(handle)
    except OSError as error:
        raise PdfToolError(f"Could not save {output.name}: {error.strerror}") from None
    return output


def merge_pdfs(inputs: list, output) -> Path:
    """Join several PDFs into one, in the order given."""
    if len(inputs) < 2:
        raise PdfToolError("Choose at least two PDF files to merge")
    writer = PdfWriter()
    for path in inputs:
        for page in open_pdf(path).pages:
            writer.add_page(page)
    return _save(writer, output)


def split_pdf(source, ranges: str, output) -> Path:
    """Save only the pages in `ranges` (like '1-3, 5') as a new PDF."""
    reader = open_pdf(source)
    writer = PdfWriter()
    for index in _select(reader, ranges):
        writer.add_page(reader.pages[index])
    return _save(writer, output)


def rotate_pdf(source, output, angle: int, ranges: str = "") -> Path:
    """Rotate clockwise by 90, 180 or 270 degrees. Empty `ranges` means all pages."""
    if angle not in (90, 180, 270):
        raise PdfToolError("The angle must be 90, 180 or 270")
    reader = open_pdf(source)
    if ranges.strip():
        selected = set(_select(reader, ranges))
    else:
        selected = set(range(len(reader.pages)))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index in selected:
            page.rotate(angle)
        writer.add_page(page)
    return _save(writer, output)


def extract_text(source, output) -> int:
    """Write the text of every page into a .txt file. Returns how many characters were found."""
    reader = open_pdf(source)
    chunks = []
    total = 0
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        total += len(text)
        chunks.append(f"--- Page {number} ---\n{text}")
    output = Path(output)
    try:
        output.write_text("\n\n".join(chunks), encoding="utf-8")
    except OSError as error:
        raise PdfToolError(f"Could not save {output.name}: {error.strerror}") from None
    return total
