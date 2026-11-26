import httpx
import pytest

from monsoonmind.llm.gateway import (
    CircuitBreaker,
    FakeLLM,
    LLMError,
    LLMGateway,
    LLMUnavailable,
    OpenAICompatProvider,
    Reply,
    cost_inr,
    estimate_tokens,
)


@pytest.mark.asyncio
async def test_generate_returns_answer_tokens_and_cost():
    provider = FakeLLM("gemini", "gemini-3.5-flash-lite", ["Hello farmer."])
    gateway = LLMGateway([provider], usd_inr=95)

    result = await gateway.generate([{"role": "user", "content": "Hello"}])

    assert result.text == "Hello farmer."
    assert result.provider == "gemini"
    assert result.tokens_in == 12
    assert result.tokens_out == 2
    assert result.cost_inr > 0
    assert not result.fallback_used


@pytest.mark.asyncio
async def test_retryable_error_retries():
    waits = []
    provider = FakeLLM(
        "gemini",
        "gemini-3.5-flash-lite",
        [LLMError("HTTP 429", retryable=True, retry_after=1), "Recovered"],
    )
    gateway = LLMGateway(
        [provider],
        sleep=lambda seconds: _capture_wait(waits, seconds),
        max_attempts=2,
    )

    result = await gateway.generate([{"role": "user", "content": "Hi"}])

    assert result.text == "Recovered"
    assert provider.calls == 2
    assert len(waits) == 1 and 1 <= waits[0] <= 20


async def _capture_wait(waits, seconds):
    waits.append(seconds)


@pytest.mark.asyncio
async def test_fallback_after_primary_fails():
    records = []
    primary = FakeLLM(
        "gemini",
        "gemini-3.5-flash-lite",
        [LLMError("HTTP 503", retryable=False)],
    )
    backup = FakeLLM("groq", "openai/gpt-oss-20b", ["Backup answer"])
    gateway = LLMGateway(
        [primary, backup],
        recorder=_capture_record(records),
    )

    result = await gateway.generate([{"role": "user", "content": "Hi"}])

    assert result.provider == "groq"
    assert result.fallback_used
    assert [row["status"] for row in records] == ["error", "ok"]


def _capture_record(records):
    async def record(row):
        records.append(row)

    return record


@pytest.mark.asyncio
async def test_non_retryable_error_is_not_retried():
    provider = FakeLLM(
        "gemini",
        "gemini-3.5-flash-lite",
        [LLMError("HTTP 401", retryable=False)],
    )
    gateway = LLMGateway([provider], max_attempts=3)

    with pytest.raises(LLMUnavailable):
        await gateway.generate([{"role": "user", "content": "Hi"}])

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_all_providers_down_raises_unavailable():
    primary = FakeLLM("gemini", "m1", [LLMError("down", retryable=False)])
    backup = FakeLLM("groq", "m2", [LLMError("down", retryable=False)])
    gateway = LLMGateway([primary, backup])

    with pytest.raises(LLMUnavailable):
        await gateway.generate([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_no_provider_raises_unavailable():
    gateway = LLMGateway([])

    with pytest.raises(LLMUnavailable):
        await gateway.generate([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_recovers():
    now = [0.0]
    provider = FakeLLM(
        "gemini",
        "m1",
        [
            LLMError("down", retryable=False),
            LLMError("down", retryable=False),
            LLMError("down", retryable=False),
            "Recovered",
        ],
    )
    gateway = LLMGateway(
        [provider],
        clock=lambda: now[0],
        breaker_threshold=3,
        breaker_cooldown=30,
    )

    for _ in range(3):
        with pytest.raises(LLMUnavailable):
            await gateway.generate([{"role": "user", "content": "Hi"}])

    assert gateway.breakers["gemini"].state == "open"
    with pytest.raises(LLMUnavailable):
        await gateway.generate([{"role": "user", "content": "Hi"}])

    now[0] = 31
    result = await gateway.generate([{"role": "user", "content": "Hi"}])
    assert result.text == "Recovered"


def test_breaker_state_transitions():
    now = [0.0]
    breaker = CircuitBreaker(threshold=2, cooldown=10, clock=lambda: now[0])

    assert breaker.state == "closed"
    breaker.failure()
    breaker.failure()
    assert breaker.state == "open"
    assert not breaker.allow()

    now[0] = 11
    assert breaker.allow()
    assert breaker.state == "half-open"

    breaker.success()
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_stream_yields_pieces_then_result():
    provider = FakeLLM("gemini", "m1", ["hello world"])
    gateway = LLMGateway([provider])

    output = [item async for item in gateway.stream([{"role": "user", "content": "Hi"}])]

    assert "".join(item for item in output[:-1]).strip() == "hello world"
    assert isinstance(output[-1], object)
    assert output[-1].text.strip() == "hello world"


@pytest.mark.asyncio
async def test_stream_falls_back_before_first_piece():
    primary = FakeLLM(
        "gemini",
        "m1",
        [LLMError("down", retryable=False)],
    )
    backup = FakeLLM("groq", "m2", ["backup answer"])
    gateway = LLMGateway([primary, backup])

    output = [item async for item in gateway.stream([{"role": "user", "content": "Hi"}])]

    assert output[-1].provider == "groq"
    assert output[-1].fallback_used


@pytest.mark.asyncio
async def test_stream_does_not_switch_mid_answer():
    primary = FakeLLM(
        "gemini",
        "m1",
        [("partial answer", LLMError("connection lost", retryable=True))],
    )
    backup = FakeLLM("groq", "m2", ["backup answer"])
    gateway = LLMGateway([primary, backup])

    output = []
    with pytest.raises(LLMUnavailable):
        async for item in gateway.stream([{"role": "user", "content": "Hi"}]):
            output.append(item)

    assert output
    assert backup.calls == 0


@pytest.mark.asyncio
async def test_recorder_failure_does_not_break_answer():
    async def broken_recorder(row):
        raise RuntimeError("database unavailable")

    provider = FakeLLM("gemini", "m1", ["Still works"])
    gateway = LLMGateway([provider], recorder=broken_recorder)

    result = await gateway.generate([{"role": "user", "content": "Hi"}])
    assert result.text == "Still works"


def test_cost_pricing_and_unknown_model():
    assert cost_inr("gemini-3.5-flash-lite", 1000, 1000, 95) > 0
    assert cost_inr("unknown-model", 1000, 1000, 95) == 0


def test_estimate_tokens_minimum_and_length():
    assert estimate_tokens("") == 1
    assert estimate_tokens("abcdefgh") == 2


@pytest.mark.asyncio
async def test_provider_sends_openai_compatible_request():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Hello"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider(
        "gemini",
        "https://llm.test/v1/",
        "k-123",
        "m-1",
        client=client,
    )

    reply = await provider.generate([{"role": "user", "content": "Hi"}])

    assert seen["url"] == "https://llm.test/v1/chat/completions"
    assert seen["auth"] == "Bearer k-123"
    assert reply == Reply("Hello", 4, 2)
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_http_error_classification():
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "2"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider("gemini", "https://llm.test/v1", "key", "m", client=client)

    with pytest.raises(LLMError) as caught:
        await provider.generate([{"role": "user", "content": "Hi"}])

    assert caught.value.retryable
    assert caught.value.retry_after == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_sse_stream():
    body = (
        'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
        'data: {"choices":[{"finish_reason":"stop"}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request):
        return httpx.Response(200, text=body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider("gemini", "https://llm.test/v1", "key", "m", client=client)
    usage = Reply()
    pieces = [piece async for piece in provider.stream([{"role": "user", "content": "Hi"}], usage)]

    assert pieces == ["Hello", " world"]
    assert "".join(pieces) == "Hello world"
    await client.aclose()


@pytest.mark.asyncio
async def test_stream_cutoff_without_done_raises():
    body = 'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'

    def handler(request):
        return httpx.Response(200, text=body)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatProvider("gemini", "https://llm.test/v1", "key", "m", client=client)

    with pytest.raises(LLMError):
        async for _ in provider.stream([{"role": "user", "content": "Hi"}], Reply()):
            pass

    await client.aclose()


@pytest.mark.asyncio
async def test_timeout_not_retryable_and_connection_error_retryable():
    def timeout_handler(request):
        raise httpx.ReadTimeout("timed out")

    client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler))
    provider = OpenAICompatProvider("gemini", "https://llm.test/v1", "key", "m", client=client)

    with pytest.raises(LLMError) as caught:
        await provider.generate([{"role": "user", "content": "Hi"}])

    assert not caught.value.retryable
    await client.aclose()

    def dropped_handler(request):
        raise httpx.ConnectError("connection dropped")

    client = httpx.AsyncClient(transport=httpx.MockTransport(dropped_handler))
    provider = OpenAICompatProvider("gemini", "https://llm.test/v1", "key", "m", client=client)

    with pytest.raises(LLMError) as caught:
        await provider.generate([{"role": "user", "content": "Hi"}])

    assert caught.value.retryable
    await client.aclose()
