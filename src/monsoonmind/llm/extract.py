"""Extract and validate structured metadata from report text."""

import json
import re

from monsoonmind.llm.doc_meta import DocMeta
from monsoonmind.llm.gateway import LLMGateway


def parse_metadata(response: str) -> DocMeta:
    """Parse JSON returned by the model and validate it with Pydantic."""
    text = response.strip()

    # Remove optional Markdown JSON fences.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)
    return DocMeta.model_validate(data)


async def extract_metadata(
    gateway: LLMGateway,
    document_text: str,
) -> DocMeta:
    """Call the gateway and return validated document metadata."""
    from pathlib import Path

    prompt = Path("prompts/extract_v1.md").read_text(encoding="utf-8")

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Extract metadata from this report text. "
                "Return JSON only.\n\n"
                f"REPORT TEXT:\n{document_text[:24000]}"
            ),
        },
    ]

    result = await gateway.generate(
        messages,
        purpose="metadata_extract",
        prompt_version="extract_v1",
        temperature=0,
    )

    try:
        return parse_metadata(result.text)
    except (json.JSONDecodeError, ValueError) as exc:
        # One repair attempt, recorded by the same gateway.
        messages.append({"role": "assistant", "content": result.text})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Your JSON failed validation: {exc}. "
                    "Return corrected JSON only, matching the schema."
                ),
            }
        )

        repaired = await gateway.generate(
            messages,
            purpose="metadata_extract_repair",
            prompt_version="extract_v1",
            temperature=0,
        )
        return parse_metadata(repaired.text)
