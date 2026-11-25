"""Extract readable text from downloaded local documents."""

import re
from pathlib import Path

import pymupdf
import trafilatura

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def detect_suffix(path: Path) -> str:
    suffix = path.suffix.lower()

    # IMD PDFs may have a .bin extension.
    if suffix == ".bin":
        with path.open("rb") as file:
            if file.read(5) == b"%PDF-":
                suffix = ".pdf"

    return suffix


def parse_file(path: Path) -> str:
    """Extract text from a downloaded PDF, HTML, TXT, or Markdown file."""
    suffix = detect_suffix(path)

    if suffix == ".pdf":
        with pymupdf.open(path) as document:
            return "\n".join(page.get_text("text") for page in document)

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
                {"page_no": index, "text": page.get_text("text").strip()}
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
