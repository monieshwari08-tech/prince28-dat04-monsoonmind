from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from monsoonmind.api.deps import RepoDep
from monsoonmind.db.repository import FILTER_KEY

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    request: Request,
    repo: RepoDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    filters = {}
    for key, value in request.query_params.items():
        if key in {"q", "limit", "offset"}:
            continue
        if not FILTER_KEY.fullmatch(key):
            raise HTTPException(status_code=400, detail=f"Invalid filter name: {key}")
        filters[key] = value

    total, rows = await repo.list(q=q, filters=filters, limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": filters,
        "items": rows,
    }


@router.get("/{doc_id}")
async def get_document(doc_id: str, repo: RepoDep) -> dict:
    record = await repo.get(doc_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{doc_id}'.")
    return record
