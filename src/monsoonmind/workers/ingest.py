"""ARQ worker entry point for MonsoonMind ingestion."""

from arq.connections import RedisSettings

from monsoonmind.config import get_settings
from monsoonmind.db.ingest_jobs import IngestJobRepository
from monsoonmind.db.session import make_engine, make_sessionmaker
from monsoonmind.ingest.worker import (
    process_ingest_item as run_ingest_item,
)


async def process_ingest_item(ctx: dict, item_id: int) -> dict:
    """Process one queued ingestion item."""
    return await run_ingest_item(ctx, item_id)


async def startup(ctx: dict) -> None:
    """Requeue unfinished items when the worker starts."""
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)

    try:
        async with session_factory() as session:
            item_ids = await IngestJobRepository(session).open_item_ids()

        for item_id in item_ids:
            await ctx["redis"].enqueue_job(
                "process_ingest_item",
                item_id,
                _job_id=f"ingest-item-{item_id}",
            )
    finally:
        await engine.dispose()


class WorkerSettings:
    """ARQ worker configuration."""

    functions = [process_ingest_item]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = get_settings().ingest_concurrency
    job_timeout = get_settings().ingest_job_timeout
    max_tries = get_settings().ingest_max_tries
