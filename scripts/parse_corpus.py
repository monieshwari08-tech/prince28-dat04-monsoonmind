"""Parse downloaded corpus files into Postgres, page by page.

Run from the repository root:
    uv run python scripts/parse_corpus.py
"""

import asyncio
import hashlib
import json
from pathlib import Path

from sqlalchemy import delete, select

from monsoonmind.config import get_settings
from monsoonmind.db.models import Document, Page, ParseFailure
from monsoonmind.db.session import make_engine, make_sessionmaker
from monsoonmind.ingest.parse import detect_suffix, parse_pages

MANIFEST = Path("data/manifest.jsonl")


def external_id(url: str) -> str:
    """Stable ID derived from the source URL."""
    return "imd-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


async def record_failure(session, row: dict, reason: str, detail: str) -> None:
    path = row.get("path", "")
    failure = await session.scalar(select(ParseFailure).where(ParseFailure.path == path))

    if failure is None:
        session.add(
            ParseFailure(
                path=path,
                sha256=row.get("sha256", ""),
                source_url=row.get("url"),
                reason=reason,
                detail=detail[:4000],
                attempts=1,
            )
        )
    else:
        failure.sha256 = row.get("sha256", "")
        failure.source_url = row.get("url")
        failure.reason = reason
        failure.detail = detail[:4000]
        failure.attempts = (failure.attempts or 0) + 1


async def main() -> None:
    settings = get_settings()
    rows = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)

    inserted = updated = skipped = failures = 0

    for row in rows:
        if row.get("status") != "downloaded":
            skipped += 1
            continue

        path = Path(row.get("path", ""))
        if not path.is_file():
            skipped += 1
            continue

        try:
            pages = parse_pages(path)
            total_chars = sum(len(page["text"]) for page in pages)

            if total_chars < 50:
                reason = "no_text_layer" if detect_suffix(path) == ".pdf" else "empty"
                async with session_factory() as session, session.begin():
                    await record_failure(
                        session,
                        row,
                        reason,
                        f"Extracted only {total_chars} characters from {path}",
                    )
                failures += 1
                continue

        except Exception as exc:
            reason = "encrypted" if "password" in str(exc).lower() else "corrupt"
            async with session_factory() as session, session.begin():
                await record_failure(session, row, reason, repr(exc))
            failures += 1
            continue

        url = row["url"]
        doc_id = external_id(url)

        async with session_factory() as session, session.begin():
            document = await session.scalar(select(Document).where(Document.external_id == doc_id))

            if document is not None and document.sha256 == row.get("sha256"):
                page_count = await session.scalar(
                    select(Page.id).where(Page.document_id == document.id).limit(1)
                )
                if page_count is not None:
                    await session.execute(
                        delete(ParseFailure).where(ParseFailure.path == str(path))
                    )
                    skipped += 1
                    continue

            metadata = {
                "source": row.get("source"),
                "path": str(path),
                "content_type": row.get("content_type"),
                "bytes": row.get("bytes"),
                "via": row.get("via"),
            }

            if document is None:
                document = Document(
                    external_id=doc_id,
                    title=row.get("title") or path.name,
                    source_url=url,
                    licence=row.get("licence"),
                    doc_type="report",
                    published_on=None,
                    sha256=row.get("sha256") or "",
                    metadata_=metadata,
                )
                session.add(document)
                await session.flush()
                inserted += 1
            else:
                document.title = row.get("title") or path.name
                document.source_url = url
                document.licence = row.get("licence")
                document.doc_type = "report"
                document.sha256 = row.get("sha256") or ""
                document.metadata_ = metadata
                await session.execute(delete(Page).where(Page.document_id == document.id))
                updated += 1

            session.add_all(
                [
                    Page(
                        document_id=document.id,
                        page_no=page["page_no"],
                        text=page["text"],
                        headings=page["headings"],
                    )
                    for page in pages
                ]
            )
            await session.execute(delete(ParseFailure).where(ParseFailure.path == str(path)))

    await engine.dispose()
    print(
        f"manifest={len(rows)} inserted={inserted} updated={updated} "
        f"skipped={skipped} failures={failures}"
    )


if __name__ == "__main__":
    asyncio.run(main())
