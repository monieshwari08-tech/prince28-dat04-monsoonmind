"""Evaluate router prompt versions against the labelled JSONL testset."""

import asyncio
import json
import re
from pathlib import Path

from monsoonmind.config import get_settings
from monsoonmind.llm.gateway import build_gateway

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ["v1", "v2", "v3", "v4"]
TESTSET = ROOT / "eval/prompt_testset.jsonl"
CACHE = ROOT / "eval/prompt_results.json"
LABELS = {"docs", "personal", "off_topic"}


def load_questions():
    return [
        json.loads(line)
        for line in TESTSET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def extract_label(text: str) -> str | None:
    text = text.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        data = json.loads(text)
        label = data.get("label")
        return label if label in LABELS else None
    except (json.JSONDecodeError, AttributeError):
        match = re.search(r'"label"\s*:\s*"(docs|personal|off_topic)"', text)
        return match.group(1) if match else None


async def main():
    settings = get_settings()
    gateway = build_gateway(settings)
    questions = load_questions()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    for version in VERSIONS:
        prompt_file = ROOT / f"prompts/classify_{version}.md"
        system_prompt = prompt_file.read_text(encoding="utf-8")
        correct = 0

        for index, item in enumerate(questions, 1):
            key = f"{version}|{item['question']}"
            if key not in cache:
                result = await gateway.generate(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": item["question"]},
                    ],
                    purpose="prompt_eval",
                    prompt_version=f"classify_{version}",
                    temperature=0,
                )
                cache[key] = {
                    "prediction": extract_label(result.text),
                    "expected": item["label"],
                    "provider": result.provider,
                    "model": result.model,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                    "cost_inr": result.cost_inr,
                }
                CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")

            row = cache[key]
            if row["prediction"] == item["label"]:
                correct += 1
            else:
                print(
                    f"  MISS {index:02d}: expected={item['label']} "
                    f"got={row['prediction']} | {item['question']}"
                )

        accuracy = correct / len(questions) * 100
        print(f"classify_{version}: {correct}/{len(questions)} = {accuracy:.1f}%")

    print(f"Cached results: {CACHE}")


if __name__ == "__main__":
    asyncio.run(main())
