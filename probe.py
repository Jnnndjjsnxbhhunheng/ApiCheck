#!/usr/bin/env python3
"""
probe.py — HTTP probe + JSON Schema inference for api-detect skill.

Single:  python probe.py --url URL [--method GET] [--header "K:V"] [--variant '{}']
Batch:   python probe.py --batch apis.json
"""

import argparse
import json
import sys
import time
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("requests not installed. Run: pip install requests")


# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------

def detect_format(value: str) -> str | None:
    import re
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*", value):
        return "date-time"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return "date"
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value, re.I):
        return "uuid"
    if re.fullmatch(r"https?://\S+", value):
        return "uri"
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return "email"
    return None


def infer_type(value: Any) -> dict:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        schema: dict = {"type": "string"}
        fmt = detect_format(value)
        if fmt:
            schema["format"] = fmt
        return schema
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {}}
        item_schema = merge_schemas([infer_type(item) for item in value])
        return {"type": "array", "items": item_schema}
    if isinstance(value, dict):
        return infer_object(value)
    return {}


def infer_object(obj: dict) -> dict:
    props = {k: infer_type(v) for k, v in obj.items()}
    return {"type": "object", "properties": props, "required": list(obj.keys())}


def merge_schemas(schemas: list[dict]) -> dict:
    """Union-merge multiple schemas for the same field position."""
    if not schemas:
        return {}
    if len(schemas) == 1:
        return schemas[0]

    types = set()
    merged: dict = {}

    for s in schemas:
        t = s.get("type")
        if isinstance(t, list):
            types.update(t)
        elif t:
            types.add(t)

    if "object" in types:
        all_props: dict[str, list] = {}
        all_required: list[set] = []
        for s in schemas:
            if s.get("type") == "object" and "properties" in s:
                for k, v in s["properties"].items():
                    all_props.setdefault(k, []).append(v)
                if "required" in s:
                    all_required.append(set(s["required"]))
        merged_props = {k: merge_schemas(v) for k, v in all_props.items()}
        required = list(all_required[0].intersection(*all_required[1:])) if all_required else []
        merged = {"type": "object", "properties": merged_props}
        if required:
            merged["required"] = required

    if "array" in types:
        item_schemas = [s["items"] for s in schemas if s.get("type") == "array" and "items" in s]
        merged = {"type": "array", "items": merge_schemas(item_schemas) if item_schemas else {}}

    if not merged:
        type_list = sorted(types)
        merged = {"type": type_list[0] if len(type_list) == 1 else type_list}
        for s in schemas:
            if "format" in s:
                merged["format"] = s["format"]
                break

    return merged


def union_merge_responses(responses: list[Any]) -> dict:
    schemas = [infer_type(r) for r in responses]
    schema = merge_schemas(schemas)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


# ---------------------------------------------------------------------------
# HTTP probing
# ---------------------------------------------------------------------------

def probe_one(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    variants: list[dict] | None = None,
    timeout: int = 15,
    delay: float = 0.3,
) -> dict:
    headers = headers or {}
    variants = variants or [{}]
    method = method.upper()

    results = []
    status_codes = []

    for params in variants:
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            else:
                resp = requests.request(method, url, headers=headers, json=params or None, timeout=timeout)

            status_codes.append(resp.status_code)

            if resp.status_code < 300:
                try:
                    results.append(resp.json())
                except ValueError:
                    pass

        except requests.exceptions.RequestException as exc:
            status_codes.append(0)
            return {
                "url": url, "method": method,
                "probes": len(variants), "success": 0,
                "status_codes": status_codes,
                "error": str(exc),
            }

        if delay:
            time.sleep(delay)

    schema = union_merge_responses(results) if results else {}
    return {
        "url": url,
        "method": method,
        "probes": len(variants),
        "success": len(results),
        "status_codes": status_codes,
        "inferred_schema": schema,
        "sample_response": results[0] if results else None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_headers(raw: list[str]) -> dict:
    headers = {}
    for h in raw:
        if ":" in h:
            k, _, v = h.partition(":")
            headers[k.strip()] = v.strip()
    return headers


def main():
    parser = argparse.ArgumentParser(description="Probe API and infer JSON Schema")
    parser.add_argument("--batch", help="Path to JSON array config file for batch mode")
    parser.add_argument("--url", help="API URL (single mode)")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--header", action="append", default=[], metavar="K:V")
    parser.add_argument("--variant", action="append", default=[], metavar="JSON")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()

    if args.batch:
        with open(args.batch) as f:
            apis = json.load(f)
        results = []
        for api in apis:
            variants = api.get("variants") or [api.get("base_params", {})]
            result = probe_one(
                url=api["url"],
                method=api.get("method", "GET"),
                headers=api.get("headers", {}),
                variants=variants,
                timeout=api.get("timeout", args.timeout),
                delay=api.get("delay", args.delay),
            )
            result["name"] = api.get("name", api["url"])
            result["input_description"] = api.get("input_description", "")
            results.append(result)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.url:
        variants = [json.loads(v) for v in args.variant] if args.variant else [{}]
        result = probe_one(
            url=args.url,
            method=args.method,
            headers=parse_headers(args.header),
            variants=variants,
            timeout=args.timeout,
            delay=args.delay,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
