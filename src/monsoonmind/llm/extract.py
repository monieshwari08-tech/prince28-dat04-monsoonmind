"""Generic structured extraction with validation, repair and usage tracking."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from monsoonmind.llm.gateway import LLMGateway


@dataclass
class ExtractionResult:
    """Validated extraction and cumulative LLM usage."""

    metadata: BaseModel | None
    attempts: int
    errors: list[str]
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    cost_inr: float

    @property
    def repaired(self) -> bool:
        return self.metadata is not None and self.attempts > 1


def parse_json(response: str) -> dict:
    """Extract the first valid JSON object, even with surrounding text."""
    text = response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character == "{":
            try:
                value, _ = decoder.raw_decode(text[index:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue

    raise json.JSONDecodeError("No valid JSON object found", text, 0)


def parse_metadata[Schema: BaseModel](response: str, schema: type[Schema]) -> Schema:
    """Parse JSON and validate it against the supplied Pydantic schema."""
    return schema.model_validate(parse_json(response))


async def extract_metadata[Schema: BaseModel](
    gateway: LLMGateway,
    document_text: str,
    *,
    schema: type[Schema],
    prompt_path: str = "prompts/extract_v1.md",
    prompt_version: str = "extract_v1",
    title: str = "",
    max_attempts: int = 3,
    native_schema: bool = False,
) -> ExtractionResult:
    """Extract structured data with up to three validation attempts."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    prompt = Path(prompt_path).read_text(encoding="utf-8")
    schema_json = schema.model_json_schema()

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                f"Document title: {title or 'Unknown'}\n"
                "Extract metadata from this document. Return JSON only.\n\n"
                f"DOCUMENT TEXT:\n{document_text}"
            ),
        },
    ]

    response_format = None
    if native_schema:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", schema.__name__)[:64]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": safe_name,
                "strict": True,
                "schema": schema_json,
            },
        }

    errors: list[str] = []
    total_in = total_out = 0
    total_cost = 0.0
    model = provider = ""

    for attempt in range(1, max_attempts + 1):
        options = {
            "purpose": "metadata_extract" if attempt == 1 else "metadata_extract_repair",
            "prompt_version": prompt_version,
            "temperature": 0,
        }
        if response_format is not None:
            options["response_format"] = response_format

        result = await gateway.generate(messages, **options)
        total_in += result.tokens_in
        total_out += result.tokens_out
        total_cost += result.cost_inr
        model, provider = result.model, result.provider

        try:
            metadata = parse_metadata(result.text, schema)
            return ExtractionResult(
                metadata=metadata,
                attempts=attempt,
                errors=errors,
                model=model,
                provider=provider,
                tokens_in=total_in,
                tokens_out=total_out,
                cost_inr=round(total_cost, 6),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            error = str(exc)[:1000]
            errors.append(error)

            if attempt < max_attempts:
                messages.append({"role": "assistant", "content": result.text})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Attempt {attempt} failed schema validation: {error}\n"
                            "Correct the JSON. Return one valid JSON object only. "
                            "Follow every schema requirement and do not invent facts."
                        ),
                    }
                )

    return ExtractionResult(
        metadata=None,
        attempts=max_attempts,
        errors=errors,
        model=model,
        provider=provider,
        tokens_in=total_in,
        tokens_out=total_out,
        cost_inr=round(total_cost, 6),
    )
