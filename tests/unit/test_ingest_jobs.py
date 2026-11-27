import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from monsoonmind.db.ingest_jobs import IngestJobRepository


def test_known_ids_returns_existing_ids():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = ["doc-1", "doc-2"]
    session.scalars.return_value = result_mock

    result = asyncio.run(IngestJobRepository(session).known_ids(["doc-1", "doc-2"]))

    assert result == {"doc-1", "doc-2"}


def test_known_ids_empty_input():
    session = AsyncMock()

    result = asyncio.run(IngestJobRepository(session).known_ids([]))

    assert result == set()
    session.scalars.assert_not_awaited()


def test_progress_returns_status_counts():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = [
        ("queued", 2),
        ("done", 3),
        ("failed", 1),
    ]
    session.execute.return_value = result_mock

    result = asyncio.run(IngestJobRepository(session).progress("job-1"))

    assert result == {
        "total": 6,
        "queued": 2,
        "running": 0,
        "done": 3,
        "failed": 1,
    }


def test_dead_letter_marks_item_failed():
    session = AsyncMock()
    item = SimpleNamespace(status="running", error="")
    session.get.return_value = item

    asyncio.run(IngestJobRepository(session).dead_letter(1, "Download failed"))

    assert item.status == "failed"
    assert item.error == "Download failed"


def test_failed_records_returns_failed_items():
    session = AsyncMock()
    item = SimpleNamespace(
        id=1,
        record={"url": "https://example.com/report.pdf"},
        error="Parse failed",
        attempts=3,
    )
    result_mock = MagicMock()
    result_mock.all.return_value = [item]
    session.scalars.return_value = result_mock

    result = asyncio.run(IngestJobRepository(session).failed_records("job-1"))

    assert result == [
        {
            "item_id": 1,
            "record": item.record,
            "error": "Parse failed",
            "attempts": 3,
        }
    ]


def test_open_item_ids_returns_queued_and_running_ids():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.all.return_value = [1, 2]
    session.scalars.return_value = result_mock

    result = asyncio.run(IngestJobRepository(session).open_item_ids())

    assert result == [1, 2]
