import json
import logging
import sys

from monsoonmind.logging_setup import (
    EXTRA_FIELDS,
    JsonFormatter,
    request_id_ctx,
    setup_logging,
)


def test_json_formatter_contains_basic_fields():
    record = logging.LogRecord("test.logger", logging.INFO, __file__, 1, "Hello world", (), None)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["msg"] == "Hello world"
    assert payload["request_id"] == "-"
    assert "ts" in payload


def test_json_formatter_includes_request_id():
    token = request_id_ctx.set("request-123")
    try:
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "Request received", (), None)

        payload = json.loads(JsonFormatter().format(record))

        assert payload["request_id"] == "request-123"
    finally:
        request_id_ctx.reset(token)


def test_json_formatter_includes_extra_fields():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "Request completed", (), None)

    for key in EXTRA_FIELDS:
        setattr(record, key, f"test_{key}")

    payload = json.loads(JsonFormatter().format(record))

    for key in EXTRA_FIELDS:
        assert payload[key] == f"test_{key}"


def test_json_formatter_includes_exception_details():
    try:
        raise ValueError("Test exception")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        "test", logging.ERROR, __file__, 1, "An error occurred", (), exc_info
    )

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError" in payload["exc"]
    assert "Test exception" in payload["exc"]


def test_json_formatter_preserves_unicode():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "தமிழ்நாடு மழை", (), None)

    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["msg"] == "தமிழ்நாடு மழை"


def test_setup_logging_configures_root_logger():
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    try:
        setup_logging("DEBUG")

        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JsonFormatter)
    finally:
        root.handlers[:] = original_handlers
        root.setLevel(original_level)
