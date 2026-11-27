from monsoonmind.api.deps import get_ingest_repo, get_manifest


def test_ingest_requires_admin_token(client):
    response = client.post(
        "/v1/ingest",
        json={"limit": 1},
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert response.status_code == 401


def test_ingest_requires_token_header(client):
    response = client.post("/v1/ingest", json={"limit": 1})
    assert response.status_code == 422


def test_ingest_admin_token_must_be_configured(client):
    client.app.state.settings.admin_token = ""
    response = client.post(
        "/v1/ingest",
        json={"limit": 1},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 503


def test_ingest_queues_downloaded_records(client):
    response = client.post(
        "/v1/ingest",
        json={"limit": 1},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["requested"] == 1
    assert data["queued"] == 1
    assert len(data["item_ids"]) == 1


def test_ingest_job_progress(client):
    created = client.post(
        "/v1/ingest",
        json={"limit": 1},
        headers={"X-Admin-Token": "test-admin-token"},
    ).json()

    response = client.get(f"/v1/ingest/{created['job_id']}")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["queued"] == 1


def test_ingest_unknown_job_returns_404(client):
    response = client.get("/v1/ingest/not-a-real-job")
    assert response.status_code == 404


def test_dead_letter_endpoint(client):
    response = client.get("/v1/ingest/dead-letter")
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_ingest_rejects_invalid_limit(client):
    response = client.post(
        "/v1/ingest",
        json={"limit": 0},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 422


def test_ingest_returns_404_when_manifest_is_empty(client):
    class EmptyManifest:
        records = {}

    client.app.dependency_overrides[get_manifest] = lambda: EmptyManifest()

    response = client.post(
        "/v1/ingest",
        json={"limit": 1},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 404


def test_retry_failed_ingestion(client):
    class FakeRetryRepo:
        class Session:
            async def commit(self):
                pass

        session = Session()

        async def progress(self, job_id):
            return {
                "total": 1,
                "queued": 0,
                "running": 0,
                "done": 0,
                "failed": 1,
            }

        async def retry_failed(self, job_id):
            return [77]

    client.app.dependency_overrides[get_ingest_repo] = lambda: FakeRetryRepo()

    response = client.post(
        "/v1/ingest/test-job/retry",
        headers={"X-Admin-Token": "test-admin-token"},
    )

    assert response.status_code == 202
    assert response.json()["retried"] == 1
    assert response.json()["queued"] == 1
    assert response.json()["item_ids"] == [77]
