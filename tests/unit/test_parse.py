import pymupdf
import pytest

from monsoonmind.ingest.parse import parse_file


def test_extracts_text_from_pdf(tmp_path):
    path = tmp_path / "report.pdf"

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Monsoon rainfall report")
    document.save(path)
    document.close()

    text = parse_file(path)

    assert "Monsoon rainfall report" in text


def test_extracts_main_text_from_html(tmp_path):
    path = tmp_path / "report.html"
    path.write_text(
        """
        <html>
          <head><title>Rainfall Report</title></head>
          <body>
            <nav>Navigation menu</nav>
            <main>
              <h1>Rainfall Report</h1>
              <p>Heavy rainfall occurred across Tamil Nadu.</p>
            </main>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    text = parse_file(path)

    assert "Rainfall Report" in text
    assert "Heavy rainfall occurred across Tamil Nadu" in text


@pytest.mark.parametrize("extension", [".txt", ".md", ".markdown"])
def test_reads_text_and_markdown_files(tmp_path, extension):
    path = tmp_path / f"notes{extension}"
    path.write_text("# MonsoonMind\nRainfall data", encoding="utf-8")

    assert parse_file(path) == "# MonsoonMind\nRainfall data"


def test_empty_html_returns_empty_text(tmp_path):
    path = tmp_path / "empty.html"
    path.write_text("<html><body></body></html>", encoding="utf-8")

    assert parse_file(path) == ""


def test_unsupported_file_type_raises_error(tmp_path):
    path = tmp_path / "archive.zip"
    path.write_bytes(b"not a text document")

    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file(path)
