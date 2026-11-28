import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from monsoonmind.workers.ingest import startup


def test_startup_requeues_open_items():
    redis = AsyncMock()
    ctx = {"redis": redis}

    session = AsyncMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = session
    session_factory.return_value.__aexit__.return_value = False

    repository = MagicMock()
    repository.open_item_ids = AsyncMock(return_value=[10, 11])

    with (
        patch(
            "monsoonmind.workers.ingest.make_engine",
            return_value=MagicMock(dispose=AsyncMock()),
        ),
        patch(
            "monsoonmind.workers.ingest.make_sessionmaker",
            return_value=session_factory,
        ),
        patch(
            "monsoonmind.workers.ingest.IngestJobRepository",
            return_value=repository,
        ),
    ):
        asyncio.run(startup(ctx))

    assert redis.enqueue_job.await_count == 2
    redis.enqueue_job.assert_any_await(
        "process_ingest_item",
        10,
        _job_id="ingest-item-10",
    )
    redis.enqueue_job.assert_any_await(
        "process_ingest_item",
        11,
        _job_id="ingest-item-11",
    )
