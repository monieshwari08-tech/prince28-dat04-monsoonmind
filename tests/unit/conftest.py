import pytest
from fastapi.testclient import TestClient

from monsoonmind.api.deps import (
    check_db,
    get_gateway,
    get_ingest_repo,
    get_manifest,
    get_queue,
    get_repo,
    get_usage_repo,
)
from monsoonmind.api.main import create_app
from monsoonmind.config import Settings
from monsoonmind.llm.gateway import LLMGateway

SAMPLE = [
    {"id": "001", "title": "Alpha guideline", "year": 2023, "kind": "guideline"},
    {"id": "002", "title": "Beta circular", "year": 2024, "kind": "circular"},
    {"id": "003", "title": "Gamma notice", "year": 2025, "kind": "circular"},
]

INGEST_RECORDS = [
    {"url": "https://example.com/report.pdf", "status": "downloaded"},
]


class FakeRepo:
    def __init__(self, rows):
        self.rows = rows

    async def list(self, *, q, filters, limit, offset):
        rows = [
            r
            for r in self.rows
            if (not q or q.lower() in str(r).lower())
            and all(str(r.get(k)) == v for k, v in filters.items())
        ]
        return len(rows), rows[offset : offset + limit]

    async def get(self, external_id):
        return next((r for r in self.rows if r["id"] == external_id), None)


class FakeUsageRepo:
    async def by_day(self, days=7):
        return [
            {
                "day": "2026-11-26",
                "calls": 3,
                "errors": 0,
                "fallbacks": 0,
                "tokens_in": 300,
                "tokens_out": 30,
                "tokens": 330,
                "cost": 0.0642,
            }
        ]


class FakeSession:
    async def commit(self):
        return None


class FakeIngestRepo:
    def __init__(self):
        self.session = FakeSession()
        self.jobs = {}
        self.next_id = 1

    async def create(self, records, job_id):
        item_ids = []
        for _record in records:
            item_ids.append(self.next_id)
            self.next_id += 1
        self.jobs[job_id] = {
            "total": len(item_ids),
            "queued": len(item_ids),
            "running": 0,
            "done": 0,
            "failed": 0,
        }
        return item_ids

    async def progress(self, job_id):
        return self.jobs.get(job_id)

    async def list_dead_letters(self, limit=100):
        return []


class FakeQueue:
    async def put(self, item_ids):
        return len(item_ids)

    async def close(self):
        return None


class FakeManifest:
    def __init__(self):
        self.records = {record["url"]: record for record in INGEST_RECORDS}


@pytest.fixture
def settings():
    return Settings(
        app_env="ci",
        database_url="postgresql://localhost:5432/unused",
        admin_token="test-admin-token",
        _env_file=None,
    )


@pytest.fixture
def db_state():
    return {"up": True}


@pytest.fixture
def client(settings, db_state, llm):
    app = create_app(settings)
    gateway = LLMGateway([llm], max_attempts=1)

    app.dependency_overrides[get_repo] = lambda: FakeRepo(SAMPLE)
    app.dependency_overrides[check_db] = lambda: db_state["up"]
    app.dependency_overrides[get_gateway] = lambda: gateway
    app.dependency_overrides[get_usage_repo] = lambda: FakeUsageRepo()
    fake_ingest_repo = FakeIngestRepo()
    app.dependency_overrides[get_ingest_repo] = lambda: fake_ingest_repo
    app.dependency_overrides[get_queue] = lambda: FakeQueue()
    app.dependency_overrides[get_manifest] = lambda: FakeManifest()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
