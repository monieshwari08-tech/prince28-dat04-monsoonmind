"""Resumable structured metadata extraction for parsed documents."""

import argparse
import asyncio
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from monsoonmind.config import get_settings
from monsoonmind.db.llm_calls import make_recorder
from monsoonmind.db.models import Document
from monsoonmind.db.session import make_engine, make_sessionmaker
from monsoonmind.llm.doc_meta import DocMeta
from monsoonmind.llm.extract import extract_metadata
from monsoonmind.llm.gateway import LLMUnavailable, build_gateway


def latest_prompt() -> tuple[str, str]:
    """Select the newest extract_vN.md prompt."""
    prompts = list(Path("prompts").glob("extract_v*.md"))
    if not prompts:
        raise FileNotFoundError("No prompts/extract_v*.md file found")

    def version(path: Path) -> int:
        match = re.search(r"extract_v(\d+)", path.stem)
        return int(match.group(1)) if match else 0

    path = max(prompts, key=version)
    return str(path), path.stem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Maximum documents; 0 means all")
    parser.add_argument("--rpm", type=float, default=12, help="Target documents per minute")
    parser.add_argument(
        "--chars",
        type=int,
        default=6000,
        help="Maximum text characters per document",
    )
    parser.add_argument("--retry-failed", action="store_true", help="Retry previous failures")
    parser.add_argument("--schema", action="store_true", help="Request native JSON-schema output")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.limit < 0 or args.rpm <= 0 or args.chars < 1:
        raise ValueError("--limit must be >= 0, --rpm and --chars must be positive")

    prompt_path, prompt_version = latest_prompt()
    settings = get_settings()
    engine = make_engine(settings)
    session_factory = make_sessionmaker(engine)
    gateway = build_gateway(settings, make_recorder(session_factory))

    counts = {"ok": 0, "repaired": 0, "failed": 0, "skipped": 0}
    total_in = total_out = 0
    total_cost = 0.0
    consecutive_unavailable = 0

    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Document)
                .options(selectinload(Document.pages))
                .where(Document.doc_type != "record")
                .order_by(Document.id)
            )
            documents = result.scalars().all()

            for document in documents:
                metadata = dict(document.metadata_ or {})
                previous = metadata.get("extract", {})
                previous_prompt = previous.get("prompt")
                previous_error = bool(previous.get("error"))

                if previous_prompt == prompt_version and not (args.retry_failed and previous_error):
                    counts["skipped"] += 1
                    continue

                pages = sorted(document.pages, key=lambda page: page.page_no)
                if not pages:
                    counts["skipped"] += 1
                    continue

                text = "\n\n".join(page.text or "" for page in pages[:3])
                text = text[: args.chars]
                if not text.strip():
                    counts["skipped"] += 1
                    continue

                try:
                    extracted = await extract_metadata(
                        gateway,
                        text,
                        schema=DocMeta,
                        prompt_path=prompt_path,
                        prompt_version=prompt_version,
                        title=document.title or "",
                        max_attempts=3,
                        native_schema=args.schema,
                    )
                except LLMUnavailable as exc:
                    consecutive_unavailable += 1
                    print(f"PROVIDER UNAVAILABLE: {exc}")
                    if consecutive_unavailable >= 2:
                        print("Two consecutive provider failures; stopping safely.")
                        break
                    await asyncio.sleep(60)
                    continue
                except Exception as exc:
                    await session.rollback()
                    counts["failed"] += 1
                    metadata["extract"] = {
                        "prompt": prompt_version,
                        "error": f"{type(exc).__name__}: {exc}"[:1000],
                    }
                    document.metadata_ = metadata
                    await session.commit()
                    print(f"FAILED: {document.id} - {exc}")
                    continue

                consecutive_unavailable = 0
                total_in += extracted.tokens_in
                total_out += extracted.tokens_out
                total_cost += extracted.cost_inr

                if extracted.metadata is None:
                    counts["failed"] += 1
                    metadata["extract"] = {
                        "prompt": prompt_version,
                        "model": extracted.model,
                        "provider": extracted.provider,
                        "attempts": extracted.attempts,
                        "tokens_in": extracted.tokens_in,
                        "tokens_out": extracted.tokens_out,
                        "cost_inr": extracted.cost_inr,
                        "errors": extracted.errors,
                        "error": extracted.errors[-1] if extracted.errors else "Invalid output",
                    }
                    print(f"FAILED: {document.id} after {extracted.attempts} attempts")
                else:
                    metadata.update(extracted.metadata.model_dump())
                    metadata["extract"] = {
                        "prompt": prompt_version,
                        "model": extracted.model,
                        "provider": extracted.provider,
                        "attempts": extracted.attempts,
                        "tokens_in": extracted.tokens_in,
                        "tokens_out": extracted.tokens_out,
                        "cost_inr": extracted.cost_inr,
                        "errors": extracted.errors,
                    }
                    counts["repaired" if extracted.repaired else "ok"] += 1
                    print(
                        f"OK: {document.id} - "
                        f"{metadata.get('summary', document.title or 'Untitled')[:100]}"
                    )

                document.metadata_ = metadata
                await session.commit()

                processed = counts["ok"] + counts["repaired"] + counts["failed"]
                if args.limit and processed >= args.limit:
                    break

                await asyncio.sleep(60 / args.rpm)

    finally:
        await engine.dispose()

    print(
        json.dumps(
            {
                **counts,
                "tokens_in": total_in,
                "tokens_out": total_out,
                "cost_inr": round(total_cost, 6),
                "prompt": prompt_version,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
