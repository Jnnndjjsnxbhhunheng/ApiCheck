"""
Schema Inferrer: Derives a JSON Schema from a collection of response samples.
Merges multiple samples to maximise field coverage (union approach).
"""

from typing import Any


def _python_type_to_json_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def _infer_single(value: Any) -> dict:
    """Infer schema for a single value."""
    if value is None:
        return {"type": "null"}

    t = _python_type_to_json_type(value)

    if t == "object":
        props = {}
        for k, v in value.items():
            props[k] = _infer_single(v)
        return {"type": "object", "properties": props}

    if t == "array":
        if not value:
            return {"type": "array", "items": {}}
        item_schema = _merge_schemas([_infer_single(item) for item in value])
        return {"type": "array", "items": item_schema}

    if t == "string":
        schema: dict = {"type": "string"}
        # Detect common string formats
        import re
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(T[\d:.+Z-]+)?", value):
            schema["format"] = "date-time" if "T" in value else "date"
        elif re.fullmatch(r"[a-fA-F0-9\-]{36}", value):
            schema["format"] = "uuid"
        return schema

    return {"type": t}


def _merge_types(types: list[str]) -> str | list[str]:
    unique = list(dict.fromkeys(types))  # preserve order, deduplicate
    return unique[0] if len(unique) == 1 else unique


def _merge_schemas(schemas: list[dict]) -> dict:
    """Merge multiple schema objects for the same field (union coverage)."""
    if not schemas:
        return {}
    if len(schemas) == 1:
        return schemas[0]

    # Collect all types
    all_types = []
    for s in schemas:
        t = s.get("type")
        if isinstance(t, list):
            all_types.extend(t)
        elif t:
            all_types.append(t)

    merged_type = _merge_types(all_types)
    merged: dict = {"type": merged_type}

    # Merge object properties
    if "object" in (all_types if isinstance(all_types, list) else [all_types]):
        all_props: dict = {}
        for s in schemas:
            if s.get("type") == "object":
                for k, v in s.get("properties", {}).items():
                    if k not in all_props:
                        all_props[k] = v
                    else:
                        all_props[k] = _merge_schemas([all_props[k], v])
        if all_props:
            merged["properties"] = all_props

    # Merge array items
    if "array" in (all_types if isinstance(all_types, list) else [all_types]):
        item_schemas = [s["items"] for s in schemas if s.get("type") == "array" and "items" in s]
        if item_schemas:
            merged["items"] = _merge_schemas(item_schemas)

    # Keep format if consistent
    formats = list({s["format"] for s in schemas if "format" in s})
    if len(formats) == 1:
        merged["format"] = formats[0]

    return merged


def infer_response_schema(bodies: list[Any]) -> dict:
    """
    Given a list of successful response bodies (parsed JSON),
    return a merged JSON Schema that covers all observed fields.
    """
    if not bodies:
        return {"type": "null", "description": "No successful responses collected"}

    schemas = [_infer_single(b) for b in bodies]
    schema = _merge_schemas(schemas)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def summarise_structure(schema: dict, indent: int = 0) -> str:
    """Produce a human-readable summary of a schema (for display)."""
    lines = []
    t = schema.get("type", "unknown")
    prefix = "  " * indent

    if t == "object":
        lines.append(f"{prefix}object {{")
        for key, sub in schema.get("properties", {}).items():
            sub_type = sub.get("type", "unknown")
            extra = f"  [{sub.get('format')}]" if "format" in sub else ""
            lines.append(f"{prefix}  {key}: {sub_type}{extra}")
            if sub_type == "object" and sub.get("properties"):
                lines.append(summarise_structure(sub, indent + 2))
            elif sub_type == "array" and sub.get("items"):
                lines.append(f"{prefix}    items: {summarise_structure(sub['items'], indent + 2).strip()}")
        lines.append(f"{prefix}}}")
    elif t == "array":
        items = schema.get("items", {})
        lines.append(f"{prefix}array of {summarise_structure(items, indent).strip()}")
    else:
        fmt = f" [{schema['format']}]" if "format" in schema else ""
        lines.append(f"{prefix}{t}{fmt}")

    return "\n".join(lines)
