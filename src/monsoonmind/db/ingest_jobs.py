"""Database operations for ingestion batches and items."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from monsoonmind.db.models import Document, IngestItem, IngestJob


class IngestJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def known_ids(self, external_ids: list[str]) -> set[str]:
        if not external_ids:
            return set()

        rows = await self.session.scalars(
            select(Document.external_id).where(Document.external_id.in_(external_ids))
        )
        return set(rows.all())

    async def create(self, records: list[dict[str, Any]], job_id: str) -> list[int]:
        job = IngestJob(id=job_id, requested=len(records))
        self.session.add(job)
        await self.session.flush()

        items = [IngestItem(job_id=job_id, record=record) for record in records]
        self.session.add_all(items)
        await self.session.flush()

        return [item.id for item in items]

    async def progress(self, job_id: str) -> dict[str, int] | None:
        job = await self.session.get(IngestJob, job_id)
        if job is None:
            return None

        rows = await self.session.execute(
            select(IngestItem.status, func.count(IngestItem.id))
            .where(IngestItem.job_id == job_id)
            .group_by(IngestItem.status)
        )
        counts = dict(rows.all())

        return {
            "total": sum(counts.values()),
            "queued": counts.get("queued", 0),
            "running": counts.get("running", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
        }

    async def dead_letter(self, item_id: int, error: str) -> None:
        item = await self.session.get(IngestItem, item_id)
        if item is not None:
            item.status = "failed"
            item.error = error[:4000]

    async def list_dead_letters(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = await self.session.scalars(
            select(IngestItem)
            .where(IngestItem.status == "failed")
            .order_by(IngestItem.id)
            .limit(limit)
        )
        return [
            {
                "item_id": item.id,
                "job_id": item.job_id,
                "record": item.record,
                "error": item.error,
                "attempts": item.attempts,
            }
            for item in rows.all()
        ]

    async def failed_records(self, job_id: str) -> list[dict[str, Any]]:
        rows = await self.session.scalars(
            select(IngestItem)
            .where(
                IngestItem.job_id == job_id,
                IngestItem.status == "failed",
            )
            .order_by(IngestItem.id)
        )
        return [
            {
                "item_id": item.id,
                "record": item.record,
                "error": item.error,
                "attempts": item.attempts,
            }
            for item in rows.all()
        ]

    async def retry_failed(self, job_id: str) -> list[int]:
        job = await self.session.get(IngestJob, job_id)
        if job is None:
            return []

        rows = await self.session.scalars(
            select(IngestItem).where(
                IngestItem.job_id == job_id,
                IngestItem.status == "failed",
            )
        )
        items = list(rows.all())

        for item in items:
            item.status = "queued"
            item.attempts = 0
            item.error = ""

        await self.session.flush()
        return [item.id for item in items]

    async def open_item_ids(self) -> list[int]:
        rows = await self.session.scalars(
            select(IngestItem.id)
            .where(IngestItem.status.in_(["queued", "running"]))
            .order_by(IngestItem.id)
        )
        return list(rows.all())
