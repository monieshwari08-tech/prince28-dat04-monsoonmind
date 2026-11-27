"""ARQ worker for reliable document ingestion."""

import hashlib
from pathlib import Path

from arq.connections import RedisSettings
from sqlalchemy import delete, select

from monsoonmind.config import get_settings
from monsoonmind.db.models import Document, IngestItem, Page, ParseFailure
from monsoonmind.db.session import make_engine, make_sessionmaker
from monsoonmind.ingest.fetch import Manifest, Source, fetch_all
from monsoonmind.ingest.parse import detect_suffix, parse_pages


def external_id(url: str) -> str:
    return "imd-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


async def process_ingest_item(ctx: dict, item_id: int) -> dict:
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)

    try:
        # Claim the item and record the attempt.
        async with session_factory() as session, session.begin():
            item = await session.get(IngestItem, item_id)
            if item is None:
                return {"item_id": item_id, "status": "missing"}
            if item.status == "done":
                return {"item_id": item_id, "status": "done"}

            item.status = "running"
            item.attempts = (item.attempts or 0) + 1
            row = dict(item.record)

        try:
            path = Path(row.get("path", ""))

            # On a live worker, the local corpus file may not exist.
            if not path.is_file():
                if not row.get("url") or not row.get("licence"):
                    raise ValueError("Missing local file, URL, or licence")

                source = Source(
                    url=row["url"],
                    source=str(row.get("source") or "unknown"),
                    licence=row["licence"],
                    title=str(row.get("title") or ""),
                )
                await fetch_all(
                    [source],
                    root=Path.cwd(),
                    max_concurrency=1,
                    per_host_delay=60.0 / settings.ingest_rpm,
                    max_attempts=settings.ingest_max_tries,
                )

                manifest = Manifest(settings.manifest_file)
                downloaded = manifest.records.get(source.url, {})
                if downloaded.get("status") != "downloaded":
                    raise RuntimeError(
                        f"Download {downloaded.get('status', 'missing')}: "
                        f"{downloaded.get('error', 'no manifest result')}"
                    )

                row = downloaded
                path = Path(row["path"])

            if not path.is_file():
                raise FileNotFoundError(str(path))

            pages = parse_pages(path)
            total_chars = sum(len(page["text"]) for page in pages)

            if total_chars < 50:
                reason = "no_text_layer" if detect_suffix(path) == ".pdf" else "empty"
                detail = f"Extracted only {total_chars} characters"

                async with session_factory() as session, session.begin():
                    failure = await session.scalar(
                        select(ParseFailure).where(ParseFailure.path == str(path))
                    )
                    if failure is None:
                        session.add(
                            ParseFailure(
                                path=str(path),
                                sha256=row.get("sha256", ""),
                                source_url=row.get("url"),
                                reason=reason,
                                detail=detail,
                                attempts=1,
                            )
                        )
                    else:
                        failure.reason = reason
                        failure.detail = detail
                        failure.attempts = (failure.attempts or 0) + 1

                    item = await session.get(IngestItem, item_id)
                    item.status = "failed"
                    item.error = reason

                return {"item_id": item_id, "status": "failed", "reason": reason}

            url = row["url"]
            doc_id = external_id(url)
            digest = row.get("sha256") or hashlib.sha256(path.read_bytes()).hexdigest()

            # Save document and all pages atomically.
            async with session_factory() as session, session.begin():
                document = await session.scalar(
                    select(Document).where(Document.external_id == doc_id)
                )

                if document is not None and document.sha256 == digest:
                    existing_page = await session.scalar(
                        select(Page.id).where(Page.document_id == document.id).limit(1)
                    )
                    if existing_page is not None:
                        item = await session.get(IngestItem, item_id)
                        item.status = "done"
                        item.error = ""
                        item.pages = len(pages)
                        return {
                            "item_id": item_id,
                            "status": "done",
                            "pages": len(pages),
                            "duplicate": True,
                        }

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
                        sha256=digest,
                        metadata_=metadata,
                    )
                    session.add(document)
                    await session.flush()
                else:
                    document.title = row.get("title") or path.name
                    document.source_url = url
                    document.licence = row.get("licence")
                    document.doc_type = "report"
                    document.sha256 = digest
                    document.metadata_ = metadata
                    await session.execute(delete(Page).where(Page.document_id == document.id))

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

                item = await session.get(IngestItem, item_id)
                item.status = "done"
                item.error = ""
                item.pages = len(pages)

            return {"item_id": item_id, "status": "done", "pages": len(pages)}

        except Exception as exc:
            async with session_factory() as session, session.begin():
                item = await session.get(IngestItem, item_id)
                if item is not None:
                    item.error = str(exc)[:4000]
                    item.status = (
                        "failed" if item.attempts >= settings.ingest_max_tries else "queued"
                    )
            raise

    finally:
        await engine.dispose()


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [process_ingest_item]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = get_settings().ingest_concurrency
    job_timeout = get_settings().ingest_job_timeout
    max_tries = get_settings().ingest_max_tries
