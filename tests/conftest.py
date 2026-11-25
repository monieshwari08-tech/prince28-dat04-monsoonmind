"""Shared unit-test fixtures."""

import pytest

from monsoonmind.llm.gateway import FakeLLM


@pytest.fixture
def llm():
    """A fake provider; unit tests never call external LLM APIs."""
    return FakeLLM()
