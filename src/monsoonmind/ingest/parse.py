"""Extract readable text from downloaded local documents."""

from pathlib import Path

import pymupdf
import trafilatura

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def parse_file(path: Path) -> str:
    """Extract text from a downloaded PDF, HTML, TXT, or Markdown file.

    This function works only with local files. It does not download content.
    """
    suffix = path.suffix.lower()

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
