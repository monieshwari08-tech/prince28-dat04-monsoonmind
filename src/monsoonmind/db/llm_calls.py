from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from monsoonmind.db.models import LlmCall


def make_recorder(sessionmaker: async_sessionmaker):
    """Create an async recorder that stores each LLM call in Postgres."""

    async def record(row: dict) -> None:
        async with sessionmaker() as session:
            session.add(LlmCall(**row))
            await session.commit()

    return record


class UsageRepository:
    """Read daily LLM usage and cost summaries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_day(self, days: int = 7) -> list[dict]:
        local = func.timezone("Asia/Kolkata", LlmCall.created_at)
        day = func.date_trunc("day", local).label("day")
        failed = func.sum(cast(LlmCall.status == "error", Integer))
        fallbacks = func.sum(cast(LlmCall.fallback_used, Integer))

        stmt = (
            select(
                day,
                func.count(LlmCall.id).label("calls"),
                failed.label("errors"),
                fallbacks.label("fallbacks"),
                func.sum(LlmCall.tokens_in + LlmCall.tokens_out).label("tokens"),
                func.sum(LlmCall.cost_inr).label("cost"),
            )
            .where(LlmCall.created_at >= datetime.now(UTC) - timedelta(days=days))
            .group_by(day)
            .order_by(day.desc())
        )

        rows = (await self.session.execute(stmt)).all()

        return [
            {
                "day": row.day.isoformat(),
                "calls": row.calls,
                "errors": int(row.errors or 0),
                "fallbacks": int(row.fallbacks or 0),
                "tokens": int(row.tokens or 0),
                "cost": round(float(row.cost or 0), 4),
            }
            for row in rows
        ]
