import os

from fastapi import APIRouter, Response

from monsoonmind.api.deps import DbCheckDep, SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    """Liveness: is the process alive?"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": os.getenv("GIT_SHA", "unknown"),
    }


@router.get("/ready")
async def ready(database: DbCheckDep, response: Response) -> dict:
    """Readiness: can this instance connect to PostgreSQL?"""
    checks = {"database": database}
    ok = all(checks.values())
    if not ok:
        response.status_code = 503
    return {"status": "ready" if ok else "not_ready", "checks": checks}
