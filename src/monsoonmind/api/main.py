"""App factory: build a fully wired FastAPI app from settings."""

import asyncio
import logging
from contextlib import asynccontextmanager

from arq.worker import create_worker
from fastapi import APIRouter, FastAPI

from monsoonmind.api.errors import register_error_handlers
from monsoonmind.api.middleware import request_context
from monsoonmind.api.routes import chat, documents, health, ingest
from monsoonmind.config import Settings, get_settings
from monsoonmind.db.llm_calls import make_recorder
from monsoonmind.db.session import make_engine, make_sessionmaker
from monsoonmind.llm.gateway import build_gateway
from monsoonmind.logging_setup import setup_logging
from monsoonmind.workers.ingest import WorkerSettings

logger = logging.getLogger("monsoonmind")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    engine = make_engine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("starting", extra={"status": settings.app_env})
        worker = None
        worker_task = None

        try:
            if settings.worker_in_api:
                worker = create_worker(WorkerSettings)
                worker_task = asyncio.create_task(worker.async_run())

            yield
        finally:
            if worker is not None:
                await worker.close()
            if worker_task is not None:
                await worker_task
            await engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.system_prompt = chat.load_prompt(settings.prompts_dir)
    app.state.gateway = build_gateway(settings, make_recorder(app.state.sessionmaker))

    app.middleware("http")(request_context)
    register_error_handlers(app)

    v1 = APIRouter(prefix="/v1")
    v1.include_router(documents.router)
    v1.include_router(ingest.router)
    v1.include_router(chat.router)
    app.include_router(health.router)
    app.include_router(v1)

    return app
