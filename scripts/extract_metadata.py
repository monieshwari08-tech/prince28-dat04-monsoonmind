"""Extract structured metadata from report documents."""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from monsoonmind.config import get_settings
from monsoonmind.db.llm_calls import make_recorder
from monsoonmind.db.models import Document
from monsoonmind.db.session import make_engine, make_sessionmaker
from monsoonmind.llm.extract import extract_metadata
from monsoonmind.llm.gateway import build_gateway


async def main() -> None:
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)
    gateway = build_gateway(settings, make_recorder(session_factory))

    success = failed = skipped = 0

    async with session_factory() as session:
        result = await session.execute(
            select(Document)
            .options(selectinload(Document.pages))
            .where(Document.doc_type == "report")
            .order_by(Document.id)
        )
        documents = result.scalars().all()

        for document in documents:
            pages = sorted(document.pages, key=lambda page: page.page_no)

            if not pages:
                skipped += 1
                continue

            metadata = dict(document.metadata_ or {})
            marker = metadata.get("extraction_v1", {})

            if marker.get("status") == "ok":
                skipped += 1
                continue

            report_text = "\n\n".join(page.text or "" for page in pages)
            if not report_text.strip():
                skipped += 1
                continue

            try:
                extracted = await extract_metadata(gateway, report_text)
                metadata.update(extracted.model_dump())
                metadata["extraction_v1"] = {"status": "ok"}
                document.metadata_ = metadata
                await session.commit()
                success += 1
                print(f"OK: {document.id} - {extracted.title}")
            except Exception as exc:
                await session.rollback()
                failed += 1
                print(f"FAILED: {document.id} - {type(exc).__name__}: {exc}")

            if success + failed >= 5:
                break

    await engine.dispose()
    print(f"success={success} failed={failed} skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
