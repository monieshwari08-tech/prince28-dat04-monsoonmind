"""Admin API for queuing and monitoring document ingestion."""

import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from monsoonmind.api.deps import IngestRepoDep, ManifestDep, QueueDep, SettingsDep

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)


def require_admin(settings: SettingsDep, token: str) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="Admin token is not configured")
    if not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/dead-letter")
async def get_dead_letter(repo: IngestRepoDep, limit: int = Query(100, ge=1, le=500)):
    items = await repo.list_dead_letters(limit)
    return {"count": len(items), "items": items}


@router.post("/{job_id}/retry", status_code=202)
async def retry_failed_ingestion(
    job_id: str,
    settings: SettingsDep,
    repo: IngestRepoDep,
    queue: QueueDep,
    admin_token: Annotated[str, Header(alias="X-Admin-Token")],
):
    require_admin(settings, admin_token)

    progress = await repo.progress(job_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    item_ids = await repo.retry_failed(job_id)
    if not item_ids:
        raise HTTPException(status_code=409, detail="No failed items to retry")

    await repo.session.commit()

    try:
        queued = await queue.put(item_ids)
    finally:
        await queue.close()

    return {
        "job_id": job_id,
        "retried": len(item_ids),
        "queued": queued,
        "item_ids": item_ids,
    }


@router.get("/{job_id}")
async def get_ingest_job(job_id: str, repo: IngestRepoDep):
    progress = await repo.progress(job_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return {"job_id": job_id, **progress}


@router.post("", status_code=202)
async def queue_ingestion(
    body: IngestRequest,
    request: Request,
    settings: SettingsDep,
    manifest: ManifestDep,
    repo: IngestRepoDep,
    queue: QueueDep,
    admin_token: Annotated[str, Header(alias="X-Admin-Token")],
):
    require_admin(settings, admin_token)

    records = [
        record for record in manifest.records.values() if record.get("status") == "downloaded"
    ][: body.limit]

    if not records:
        raise HTTPException(status_code=404, detail="No downloaded documents found")

    job_id = uuid.uuid4().hex
    item_ids = await repo.create(records, job_id)
    await repo.session.commit()

    try:
        queued = await queue.put(item_ids)
    finally:
        await queue.close()

    return {
        "job_id": job_id,
        "requested": len(item_ids),
        "queued": queued,
        "item_ids": item_ids,
    }
