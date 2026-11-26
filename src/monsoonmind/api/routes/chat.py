import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from monsoonmind.api.deps import GatewayDep, UsageDep
from monsoonmind.llm.gateway import LLMResult, LLMUnavailable

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    stream: bool = True


def load_prompt(prompts_dir: Path) -> str:
    path = prompts_dir / "chat_system_v1.md"
    if not path.is_file():
        raise RuntimeError(f"System prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def result_summary(result: LLMResult) -> dict:
    return {
        "provider": result.provider,
        "model": result.model,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "latency_ms": result.latency_ms,
        "cost_inr": result.cost_inr,
        "fallback_used": result.fallback_used,
    }


def sse(data: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data)}\n\n"


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, gateway: GatewayDep):
    messages = [
        {"role": "system", "content": request.app.state.system_prompt},
        {"role": "user", "content": body.message},
    ]

    if not body.stream:
        try:
            result = await gateway.generate(
                messages, purpose="chat", prompt_version="chat_system_v1"
            )
        except LLMUnavailable as exc:
            raise HTTPException(
                status_code=503,
                detail=f"No model could answer: {exc}",
            ) from exc

        return {"answer": result.text, **result_summary(result)}

    stream = gateway.stream(messages, purpose="chat", prompt_version="chat_system_v1")

    try:
        first = await anext(stream)
    except (LLMUnavailable, StopAsyncIteration) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No model could answer: {exc}",
        ) from exc

    async def events() -> AsyncIterator[str]:
        item = first
        while True:
            if isinstance(item, LLMResult):
                yield sse(result_summary(item), "done")
                return

            yield sse({"delta": item})

            try:
                item = await anext(stream)
            except StopAsyncIteration:
                return
            except LLMUnavailable as exc:
                yield sse({"detail": str(exc)}, "error")
                return

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/usage")
async def usage(
    repo: UsageDep,
    days: int = Query(default=7, ge=1, le=90),
) -> dict:
    rows = await repo.by_day(days=days)
    total_calls = sum(row["calls"] for row in rows)
    total_cost = round(sum(row.get("cost_inr", row.get("cost", 0)) for row in rows), 4)

    return {
        "days": rows,
        "days_requested": days,
        "calls": total_calls,
        "total_cost_inr": total_cost,
    }
