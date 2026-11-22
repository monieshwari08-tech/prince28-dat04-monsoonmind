import asyncio
from unittest.mock import AsyncMock

import pytest

from monsoonmind.db.repository import DocumentRepository, _value_candidates


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("false", False),
    ],
)
def test_value_candidates_boolean(value, expected):
    candidates = _value_candidates(value)

    assert candidates == [value, [value], expected]


def test_value_candidates_decimal():
    candidates = _value_candidates("3.14")

    assert candidates == ["3.14", ["3.14"], 3.14]


def test_get_returns_none_when_document_does_not_exist():
    session = AsyncMock()
    session.scalar.return_value = None

    repository = DocumentRepository(session)

    result = asyncio.run(repository.get("missing-document"))

    assert result is None
    session.scalar.assert_awaited_once()
