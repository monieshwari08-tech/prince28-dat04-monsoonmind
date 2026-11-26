import json

import pytest
from pydantic import ValidationError

from monsoonmind.llm.doc_meta import DocMeta
from monsoonmind.llm.extract import parse_json, parse_metadata

VALID = {
    "doc_kind": "report",
    "year": 2024,
    "language": "en",
    "summary": "Tamil Nadu northeast monsoon rainfall report for the year 2024.",
    "topics": ["rainfall", "monsoon"],
    "season": ["northeast_monsoon"],
    "region": ["Tamil Nadu"],
    "rainfall_mm": ["350 mm"],
    "departure_pct": ["12%"],
    "cyclone_name": [],
}


def test_parse_json_plain_object():
    assert parse_json(json.dumps(VALID)) == VALID


def test_parse_json_markdown_fence():
    response = "```json\n" + json.dumps(VALID) + "\n```"
    assert parse_json(response) == VALID


def test_parse_json_with_surrounding_text():
    response = "Here is the result:\n" + json.dumps(VALID) + "\nDone."
    assert parse_json(response) == VALID


def test_parse_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json("not valid JSON")


def test_parse_metadata_validates_schema():
    result = parse_metadata(json.dumps(VALID), DocMeta)
    assert result.doc_kind == "report"
    assert result.year == 2024
    assert result.topics == ["rainfall", "monsoon"]


def test_parse_metadata_rejects_extra_fields():
    invalid = {**VALID, "unexpected": "value"}
    with pytest.raises(ValidationError):
        parse_metadata(json.dumps(invalid), DocMeta)


def test_parse_metadata_rejects_invalid_doc_kind():
    invalid = {**VALID, "doc_kind": "monsoon_report"}
    with pytest.raises(ValidationError):
        parse_metadata(json.dumps(invalid), DocMeta)


def test_parse_metadata_rejects_invalid_year():
    invalid = {**VALID, "year": 1800}
    with pytest.raises(ValidationError):
        parse_metadata(json.dumps(invalid), DocMeta)


def test_parse_metadata_rejects_empty_topics():
    invalid = {**VALID, "topics": []}
    with pytest.raises(ValidationError):
        parse_metadata(json.dumps(invalid), DocMeta)


def test_parse_metadata_rejects_long_list():
    invalid = {**VALID, "season": ["a"] * 9}
    with pytest.raises(ValidationError):
        parse_metadata(json.dumps(invalid), DocMeta)
