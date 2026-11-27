"""Read text from pictures inside PDFs (scanned pages, slides saved as images).

OCR is optional. Install it with:  pip install "study-kit[ocr]"
Everything runs on this computer. The first use of a language downloads its small model
(about 8 to 30 MB) into the .studykit/models folder; after that it works offline.
"""

import importlib.util
import os
import sys
from pathlib import Path

from studykit import pdf_tools, storage

LANGUAGES = {"en": "English", "ko": "Korean", "ru": "Russian"}
MIN_TEXT_CHARS = 20  # a page with fewer typed characters than this is treated as a picture
RENDER_SCALE = 2.5  # 72 dpi x 2.5 = 180 dpi: sharp enough to read, fast enough to wait for

_engines: dict = {}


class OcrError(pdf_tools.PdfToolError):
    """A problem the user can understand (a PdfToolError, so existing handlers catch it)."""


class OcrNotInstalled(OcrError):
    """The optional OCR packages are missing."""


class OcrCancelled(Exception):
    """The user pressed Cancel."""


def is_available() -> bool:
    """True if all OCR packages are installed."""
    return all(importlib.util.find_spec(name) for name in ("rapidocr", "onnxruntime", "pypdfium2"))


def models_dir() -> Path:
    """Where the language models are kept (next to the data file)."""
    return storage.data_path().parent / "models"


def _not_installed() -> OcrNotInstalled:
    return OcrNotInstalled('OCR is not installed. Run:  pip install "study-kit[ocr]"')


def _engine(lang: str):
    """Create (once per language) the OCR engine."""
    if lang not in LANGUAGES:
        raise OcrError(f"Unknown language '{lang}'. Choose from: {', '.join(LANGUAGES)}")
    if lang in _engines:
        return _engines[lang]
    try:
        from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
    except ImportError:
        raise _not_installed() from None

    # A windowed .exe has no console; make sure libraries that print progress don't crash.
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))  # noqa: SIM115

    params = {"Global.model_root_dir": str(models_dir()), "Global.log_level": "warning"}
    if lang != "en":  # English uses the default models that RapidOCR ships with
        params.update(
            {
                "Rec.lang_type": LangRec.KOREAN if lang == "ko" else LangRec.ESLAV,
                "Rec.ocr_version": OCRVersion.PPOCRV5,
                "Rec.model_type": ModelType.MOBILE,
            }
        )
    try:
        models_dir().mkdir(parents=True, exist_ok=True)
        engine = RapidOCR(params=params)
    except Exception as error:
        raise OcrError(
            f"Could not load the {LANGUAGES[lang]} OCR model. The first use needs an internet "
            f"connection to download it. ({type(error).__name__})"
        ) from None
    _engines[lang] = engine
    return engine


def _open_document(path):
    """Open the PDF with the page renderer."""
    try:
        import pypdfium2
    except ImportError:
        raise _not_installed() from None
    try:
        return pypdfium2.PdfDocument(str(path))
    except Exception:
        raise OcrError(f"Could not draw the pages of {Path(path).name}") from None


def render_page(document, index: int):
    """Draw one page as a picture."""
    return document[index].render(scale=RENDER_SCALE).to_pil()


def recognize(image, lang: str) -> str:
    """Read the text in one picture. Lines come back top to bottom."""
    import numpy

    result = _engine(lang)(numpy.array(image.convert("RGB")))
    lines = result.txts or ()
    return "\n".join(line.strip() for line in lines if line and line.strip())


def extract_text_ocr(
    source, output, lang: str = "en", force: bool = False, progress=None, cancel=None
) -> dict:
    """Write the text of every page into a .txt file, reading pictures with OCR.

    Pages that already contain typed text are copied as they are, unless `force` is True
    (then every page is read as a picture, which also finds text inside images next to
    typed text). `progress(done, total)` is called after each page. `cancel` is an object
    with `is_set()`; when it becomes true, OcrCancelled is raised and no file is written.
    Returns {'characters': ..., 'pages': ..., 'ocr_pages': ...}.
    """
    reader = pdf_tools.open_pdf(source)
    total = len(reader.pages)
    document = None
    chunks = []
    characters = ocr_pages = 0
    for index, page in enumerate(reader.pages):
        if cancel is not None and cancel.is_set():
            raise OcrCancelled()
        text = (page.extract_text() or "").strip()
        if force or len(text) < MIN_TEXT_CHARS:
            if document is None:
                document = _open_document(source)
            text = recognize(render_page(document, index), lang).strip()
            ocr_pages += 1
        characters += len(text)
        chunks.append(f"--- Page {index + 1} ---\n{text}")
        if progress is not None:
            progress(index + 1, total)

    output = Path(output)
    try:
        output.write_text("\n\n".join(chunks), encoding="utf-8")
    except OSError as error:
        raise OcrError(f"Could not save {output.name}: {error.strerror}") from None
    return {"characters": characters, "pages": total, "ocr_pages": ocr_pages}
