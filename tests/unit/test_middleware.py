import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from monsoonmind.api.middleware import request_context
from monsoonmind.logging_setup import request_id_ctx


def create_test_app(endpoint):
    app = FastAPI()
    app.middleware("http")(request_context)
    app.get("/test")(endpoint)
    return app


def test_request_context_generates_request_id():
    async def endpoint(request):
        return {"status": "ok"}

    app = create_test_app(endpoint)

    with TestClient(app) as client:
        response = client.get("/test")

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 16


def test_request_context_uses_provided_request_id():
    async def endpoint(request):
        return {"status": "ok"}

    app = create_test_app(endpoint)

    with TestClient(app) as client:
        response = client.get(
            "/test",
            headers={"X-Request-ID": "custom-request-123"},
        )

    assert response.headers["X-Request-ID"] == "custom-request-123"


def test_request_context_logs_request_details(caplog):
    async def endpoint(request):
        return {"status": "ok"}

    app = create_test_app(endpoint)

    with caplog.at_level(logging.INFO, logger="monsoonmind.http"), TestClient(app) as client:
        response = client.get(
            "/test",
            headers={"X-Request-ID": "logging-test"},
        )

    record = next(record for record in caplog.records if record.message == "request finished")

    assert record.request_id == "logging-test"
    assert record.method == "GET"
    assert record.path == "/test"
    assert record.status == response.status_code
    assert record.duration_ms >= 0


def test_request_context_handles_unexpected_exception(caplog):
    async def endpoint(request):
        raise RuntimeError("test failure")

    app = create_test_app(endpoint)

    with caplog.at_level(logging.ERROR, logger="monsoonmind.http"), TestClient(app) as client:
        response = client.get("/test")

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["X-Request-ID"]
    assert "unhandled error" in caplog.text


def test_request_context_resets_request_id_after_request():
    async def endpoint(request):
        return {"status": "ok"}

    app = create_test_app(endpoint)

    with TestClient(app) as client:
        client.get("/test", headers={"X-Request-ID": "temporary-id"})

    assert request_id_ctx.get() == "-"
