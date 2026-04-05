"""
Unit tests for src/schema_infer.py — no network access required.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.schema_infer import _infer_single, _merge_schemas, infer_response_schema, summarise_structure


# ---------------------------------------------------------------------------
# _infer_single
# ---------------------------------------------------------------------------

def test_infer_null():
    assert _infer_single(None) == {"type": "null"}


def test_infer_bool():
    assert _infer_single(True) == {"type": "boolean"}


def test_infer_int():
    assert _infer_single(42) == {"type": "integer"}


def test_infer_float():
    assert _infer_single(3.14) == {"type": "number"}


def test_infer_string():
    assert _infer_single("hello") == {"type": "string"}


def test_infer_date_format():
    s = _infer_single("2024-03-15")
    assert s["type"] == "string"
    assert s.get("format") == "date"


def test_infer_datetime_format():
    s = _infer_single("2024-03-15T10:30:00Z")
    assert s["type"] == "string"
    assert s.get("format") == "date-time"


def test_infer_uuid_format():
    s = _infer_single("550e8400-e29b-41d4-a716-446655440000")
    assert s["type"] == "string"
    assert s.get("format") == "uuid"


def test_infer_empty_array():
    s = _infer_single([])
    assert s["type"] == "array"
    assert s["items"] == {}


def test_infer_array_of_ints():
    s = _infer_single([1, 2, 3])
    assert s["type"] == "array"
    assert s["items"]["type"] == "integer"


def test_infer_simple_object():
    s = _infer_single({"id": 1, "name": "Alice"})
    assert s["type"] == "object"
    assert s["properties"]["id"]["type"] == "integer"
    assert s["properties"]["name"]["type"] == "string"


def test_infer_nested_object():
    s = _infer_single({"user": {"id": 1, "active": True}})
    assert s["type"] == "object"
    user = s["properties"]["user"]
    assert user["type"] == "object"
    assert user["properties"]["id"]["type"] == "integer"
    assert user["properties"]["active"]["type"] == "boolean"


# ---------------------------------------------------------------------------
# _merge_schemas
# ---------------------------------------------------------------------------

def test_merge_same_type():
    merged = _merge_schemas([{"type": "string"}, {"type": "string"}])
    assert merged["type"] == "string"


def test_merge_different_types_becomes_list():
    merged = _merge_schemas([{"type": "string"}, {"type": "integer"}])
    t = merged["type"]
    assert isinstance(t, list)
    assert set(t) == {"string", "integer"}


def test_merge_objects_union_properties():
    a = {"type": "object", "properties": {"id": {"type": "integer"}}}
    b = {"type": "object", "properties": {"name": {"type": "string"}}}
    merged = _merge_schemas([a, b])
    assert "id" in merged["properties"]
    assert "name" in merged["properties"]


def test_merge_objects_overlapping_properties():
    a = {"type": "object", "properties": {"count": {"type": "integer"}}}
    b = {"type": "object", "properties": {"count": {"type": "integer"}}}
    merged = _merge_schemas([a, b])
    assert merged["properties"]["count"]["type"] == "integer"


# ---------------------------------------------------------------------------
# infer_response_schema
# ---------------------------------------------------------------------------

def test_empty_bodies_returns_null():
    schema = infer_response_schema([])
    assert schema["type"] == "null"


def test_single_body():
    schema = infer_response_schema([{"id": 1, "title": "Hello"}])
    assert schema["type"] == "object"
    assert "id" in schema["properties"]
    assert "title" in schema["properties"]
    assert schema.get("$schema") is not None


def test_multiple_bodies_union_coverage():
    """Fields appearing in any response should appear in the merged schema."""
    bodies = [
        {"id": 1, "title": "Post 1"},
        {"id": 2, "title": "Post 2", "tags": ["a", "b"]},
        {"id": 3, "status": "published"},
    ]
    schema = infer_response_schema(bodies)
    props = schema["properties"]
    assert "id" in props
    assert "title" in props
    assert "tags" in props       # only in body[1]
    assert "status" in props     # only in body[2]


def test_array_response():
    """Top-level array response."""
    bodies = [
        [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    ]
    schema = infer_response_schema(bodies)
    assert schema["type"] == "array"
    assert schema["items"]["type"] == "object"
    assert "id" in schema["items"]["properties"]


# ---------------------------------------------------------------------------
# summarise_structure
# ---------------------------------------------------------------------------

def test_summarise_primitive():
    out = summarise_structure({"type": "string"})
    assert "string" in out


def test_summarise_object():
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
        },
    }
    out = summarise_structure(schema)
    assert "object" in out
    assert "id" in out
    assert "name" in out


def test_summarise_array():
    schema = {
        "type": "array",
        "items": {"type": "string"},
    }
    out = summarise_structure(schema)
    assert "array" in out
    assert "string" in out
