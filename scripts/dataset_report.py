"""Measure the downloaded MonsoonMind PDF corpus and generate capacity reports."""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifest.jsonl"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-pages", type=int, default=4000)
    parser.add_argument("--embed-usd", type=float, default=0.20)
    parser.add_argument("--dims", type=int, default=1024)
    parser.add_argument("--chunk-tokens", type=int, default=500)
    parser.add_argument("--usd-inr", type=float, default=95)
    args = parser.parse_args()

    records = []
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            path = ROOT / item.get("path", "")
            if (
                item.get("status") == "downloaded"
                and path.is_file()
                and path.suffix.lower() == ".pdf"
            ):
                item["_path"] = path
                records.append(item)

    # A manifest may contain repeated entries; count each local path once.
    unique = {}
    for item in records:
        unique[str(item["_path"])] = item
    records = list(unique.values())

    total_bytes = 0
    total_pages = 0
    total_chars = 0
    pages_with_text = 0
    source_stats = defaultdict(lambda: {"files": 0, "pages": 0, "bytes": 0})
    rows = []

    for item in sorted(records, key=lambda x: x.get("title", "")):
        path = item["_path"]
        size = path.stat().st_size
        total_bytes += size
        pages = 0
        chars = 0
        text_pages = 0
        error = ""

        try:
            reader = PdfReader(str(path), strict=False)
            pages = len(reader.pages)
            for page in reader.pages:
                try:
                    extracted = page.extract_text() or ""
                    if extracted.strip():
                        text_pages += 1
                        chars += len(extracted)
                except Exception:
                    pass
        except Exception as exc:
            error = f"PDF read error: {type(exc).__name__}"

        total_pages += pages
        total_chars += chars
        pages_with_text += text_pages

        source = item.get("source", "unknown")
        stats = source_stats[source]
        stats["files"] += 1
        stats["pages"] += pages
        stats["bytes"] += size

        rows.append(
            {
                "title": item.get("title", path.name),
                "source": source,
                "pages": pages,
                "size_mb": size / 1024 / 1024,
                "text_pages": text_pages,
                "licence": item.get("licence", "Not recorded"),
                "error": error,
            }
        )

    total_mb = total_bytes / 1024 / 1024
    tokens_per_page = (total_chars / 4 / total_pages) if total_pages else 0
    full_tokens = tokens_per_page * args.full_pages
    chunks = math.ceil(full_tokens / args.chunk_tokens) if full_tokens else 0
    embedding_usd = full_tokens / 1_000_000 * args.embed_usd
    embedding_inr = embedding_usd * args.usd_inr
    vector_mb = chunks * args.dims * 4 / 1024 / 1024
    text_mb = full_tokens * 4 / 1024 / 1024

    source_lines = [
        "| Source | Files | Pages | Size (MB) |",
        "|---|---:|---:|---:|",
    ]
    for source, stats in sorted(source_stats.items()):
        source_lines.append(
            f"| {source} | {stats['files']} | {stats['pages']} | "
            f"{stats['bytes'] / 1024 / 1024:.2f} |"
        )

    document_lines = [
        "| Document | Source | Pages | Size (MB) | Text pages |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rows:
        document_lines.append(
            f"| {row['title'].replace('|', '/')} | {row['source']} | "
            f"{row['pages']} | {row['size_mb']:.2f} | {row['text_pages']} |"
        )

    dataset_generated = f"""## Measured corpus

- **PDF files:** {len(rows)}
- **Pages:** {total_pages}
- **Local size:** {total_mb:.2f} MB
- **Pages with extractable text:** {pages_with_text} / {total_pages}
- **Estimated extracted text:** {total_chars:,} characters
- **Estimated tokens per page:** {tokens_per_page:,.0f} (characters ÷ 4)

### By source

{chr(10).join(source_lines)}

### Downloaded documents

{chr(10).join(document_lines)}
"""

    capacity_generated = f"""## Measured capacity estimate

| Measure | Estimate |
|---|---:|
| Measured average tokens per page | {tokens_per_page:,.0f} |
| Full corpus target | {args.full_pages:,} pages |
| Projected full-corpus tokens | {full_tokens:,.0f} ({full_tokens / 1_000_000:.2f} M) |
| Chunk size | {args.chunk_tokens} tokens |
| Projected chunks | {chunks:,} |
| Embedding dimensions | {args.dims} |
| Estimated embedding cost | ${embedding_usd:.4f} (about Rs {embedding_inr:,.2f}) |
| Estimated vector storage (float32) | {vector_mb:.2f} MB |
| Estimated raw text storage (rough) | {text_mb:.2f} MB |

*Assumptions: tokens are estimated as extracted characters ÷ 4; embedding price is
the supplied USD per million tokens; vector storage assumes 4 bytes per dimension.
Actual database storage will be higher due to indexes, metadata and row overhead.*
"""

    dataset_path = ROOT / "DATASET.md"
    capacity_path = ROOT / "docs/CAPACITY.md"

    dataset_template = """# Dataset: MonsoonMind

Explains Tamil Nadu's monsoon and weather history from IMD reports
(northeast monsoon statistics, district rainfall, cyclone reports) and
sets it next to live forecasts.

- **Start target:** 10 years of NE monsoon reports + 20 cyclone reports
- **Full target:** All monsoon, cyclone and RMC reports since 2010 (4,000+ pages)
- **Collected by:** `scripts/fetch.py`; source URLs and download metadata
  are recorded in `data/manifest.jsonl`.

## Where the documents come from

- https://mausam.imd.gov.in/
- https://rsmcnewdelhi.imd.gov.in/
- https://open-meteo.com/

## Terms I follow

Public IMD publications; copyright applies unless a source states
otherwise. Open-Meteo data is provided under CC BY 4.0.

- Every answer links to the original document.
- No personal data is collected.

<!-- generated:start -->
<!-- generated:end -->

## Known gaps

- Only 8 dedicated annual Northeast Monsoon reports (2018–2025) are
  confirmed in the current collection. 2016 and 2017 have supporting IMD
  annual reports, not confirmed dedicated annual NEM reports.
- Some reports may be scanned or have little extractable text; inspect the text-page counts above.
- IMD copyright and permission for displaying full report text require manual review.
"""
    capacity_template = """# Capacity plan: MonsoonMind

Full corpus target: All monsoon, cyclone and RMC reports since 2010 (4,000+ pages)

<!-- generated:start -->
<!-- generated:end -->

## What I conclude

1. Is embedding cost a problem for this product? (Use the estimate above and explain in one line.)
2. Do the vectors and text fit in my free Postgres? (Compare the estimates
   above with the storage limit on my database dashboard.)
3. Which number above am I least sure about, and how will I measure it better?
4. What changes if the corpus grows 10 times? (Consider embedding cost,
   vector storage and retrieval speed.)
"""

    def replace_generated(path, template, generated):
        content = path.read_text(encoding="utf-8") if path.exists() else template
        start = "<!-- generated:start -->"
        end = "<!-- generated:end -->"
        if start in content and end in content:
            before, rest = content.split(start, 1)
            _, after = rest.split(end, 1)
            content = before + start + "\n\n" + generated.rstrip() + "\n\n" + end + after
        else:
            content = template.replace(
                start + "\n" + end,
                start + "\n\n" + generated.rstrip() + "\n\n" + end,
            )
        path.write_text(content, encoding="utf-8")

    replace_generated(dataset_path, dataset_template, dataset_generated)
    replace_generated(capacity_path, capacity_template, capacity_generated)

    print(
        f"files={len(rows)} pages={total_pages} size={total_mb:.2f} MB "
        f"-> wrote DATASET.md and docs/CAPACITY.md"
    )
    if not rows:
        print("WARNING: No downloaded PDF files were found in the manifest.")
    if any(row["error"] for row in rows):
        print("WARNING: Some PDFs could not be read; check DATASET.md and the errors.")


if __name__ == "__main__":
    main()
