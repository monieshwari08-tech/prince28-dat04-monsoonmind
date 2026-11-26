"""Extract readable text from downloaded local documents."""

import re
from pathlib import Path

import pymupdf
import trafilatura

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
MIN_PAGE_CHARS = 50


def detect_suffix(path: Path) -> str:
    suffix = path.suffix.lower()

    # IMD PDFs may have a .bin extension.
    if suffix == ".bin":
        with path.open("rb") as file:
            if file.read(5) == b"%PDF-":
                suffix = ".pdf"

    return suffix


def _extract_pdf_page(page) -> str:
    """Extract native text first, then OCR scanned pages."""
    try:
        native_text = page.get_text("text").strip()
    except Exception:
        native_text = ""

    if len(native_text) >= MIN_PAGE_CHARS:
        return native_text

    try:
        textpage = page.get_textpage_ocr(
            language="eng",
            dpi=120,
            full=True,
        )
        ocr_text = page.get_text("text", textpage=textpage).strip()

        if len(ocr_text) > len(native_text):
            return ocr_text
    except Exception:
        # Keep native text; corpus script records documents with
        # insufficient extracted text as parse failures.
        pass

    return native_text


def parse_file(path: Path) -> str:
    """Extract text from a downloaded PDF, HTML, TXT, or Markdown file."""
    suffix = detect_suffix(path)

    if suffix == ".pdf":
        with pymupdf.open(path) as document:
            return "\n".join(_extract_pdf_page(page) for page in document)

    if suffix in {".html", ".htm"}:
        html = path.read_text(encoding="utf-8", errors="replace")
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
        )
        return extracted or ""

    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")

    raise ValueError(f"Unsupported file type: {suffix or 'no extension'}")


def parse_pages(path: Path) -> list[dict]:
    """Return page-numbered text and headings from a local document."""
    suffix = detect_suffix(path)

    if suffix == ".pdf":
        with pymupdf.open(path) as document:
            pages = [
                {
                    "page_no": index,
                    "text": _extract_pdf_page(page),
                }
                for index, page in enumerate(document, start=1)
            ]
    else:
        text = parse_file(path)
        pages = [{"page_no": 1, "text": text.strip()}]

    for page in pages:
        headings = []
        for line in page["text"].splitlines():
            line = line.strip()
            if line.startswith("#") or (
                len(line) >= 5 and line.isupper() and any(c.isalpha() for c in line)
            ):
                headings.append(re.sub(r"^#+\s*", "", line)[:300])

        page["headings"] = headings

    return pages
