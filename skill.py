#!/usr/bin/env python3
"""
API Schema Detection Skill
===========================
Probes an unknown API multiple times, infers input/output schema,
and produces a business-level explanation using Claude.

Usage:
    python skill.py --config probe_config.json
    python skill.py --url https://api.example.com/users \
                    --method GET \
                    --header "Authorization: Bearer TOKEN" \
                    --input-desc "支持 page, pageSize 分页参数" \
                    --variant '{"page": 1}' \
                    --variant '{"page": 2}' \
                    --output report.json

Arguments:
    --url           API endpoint URL (required)
    --method        HTTP method, default GET
    --header        HTTP header in "Key: Value" form (repeatable)
    --base-param    Base parameter in "key=value" form (repeatable)
    --variant       JSON object of param overrides for one probe call (repeatable)
    --input-desc    Free-text description of the input parameters
    --probes        Number of auto-generated probe calls if no --variant given (default 3)
    --timeout       Per-request timeout in seconds (default 15)
    --delay         Seconds between requests (default 0.5)
    --no-ai         Skip Claude analysis, only output schema
    --output        Write JSON report to this file path
    --config        Load all options from a JSON config file
"""

import argparse
import json
import logging
import sys
import os

# Allow running from repo root without installing
sys.path.insert(0, os.path.dirname(__file__))

from src.prober import APIProber
from src.schema_infer import infer_response_schema, summarise_structure
from src.analyzer import APIAnalyzer

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_headers(header_list: list[str]) -> dict:
    headers = {}
    for h in header_list or []:
        if ":" in h:
            k, _, v = h.partition(":")
            headers[k.strip()] = v.strip()
    return headers


def parse_base_params(param_list: list[str]) -> dict:
    params = {}
    for p in param_list or []:
        if "=" in p:
            k, _, v = p.partition("=")
            params[k.strip()] = v.strip()
    return params


def build_variants(raw_variants: list[str]) -> list[dict]:
    variants = []
    for v in raw_variants or []:
        try:
            variants.append(json.loads(v))
        except json.JSONDecodeError as e:
            logger.warning("Could not parse variant JSON '%s': %s", v, e)
    return variants or [{}]


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def run(cfg: dict) -> dict:
    url = cfg["url"]
    method = cfg.get("method", "GET")
    headers = cfg.get("headers", {})
    base_params = cfg.get("base_params", {})
    variants = cfg.get("variants", [{}])
    input_desc = cfg.get("input_description", "")
    timeout = cfg.get("timeout", 15)
    delay = cfg.get("delay", 0.5)
    skip_ai = cfg.get("no_ai", False)

    # --- Probe ---
    prober = APIProber(
        url=url,
        method=method,
        headers=headers,
        base_params=base_params,
        probe_variants=variants,
        timeout=timeout,
        delay_between_calls=delay,
    )
    logger.info("Starting API probing: %s %s  (%d variants)", method, url, len(variants))
    results = prober.probe()

    probe_dicts = [r.to_dict() for r in results]
    success_count = sum(1 for r in results if 200 <= r.status_code < 300)
    logger.info("Probing complete: %d/%d successful", success_count, len(results))

    # --- Infer schema ---
    bodies = prober.successful_bodies(results)
    schema = infer_response_schema(bodies)
    summary = summarise_structure(schema)

    report: dict = {
        "endpoint": {"url": url, "method": method},
        "input_description": input_desc,
        "probe_summary": {
            "total_calls": len(results),
            "successful": success_count,
            "status_codes": list({r.status_code for r in results}),
        },
        "probe_results": probe_dicts,
        "inferred_output_schema": schema,
        "schema_summary": summary,
    }

    # --- AI analysis ---
    if not skip_ai:
        logger.info("Requesting business analysis from Claude...")
        try:
            analyzer = APIAnalyzer()
            analysis = analyzer.analyze(
                url=url,
                method=method,
                input_description=input_desc,
                probe_results=probe_dicts,
                inferred_schema=schema,
                schema_summary=summary,
            )
            report["business_analysis"] = analysis
        except Exception as e:
            logger.error("Claude analysis failed: %s", e)
            report["business_analysis"] = f"Analysis failed: {e}"
    else:
        report["business_analysis"] = "(skipped: --no-ai)"

    return report


def main():
    parser = argparse.ArgumentParser(description="API Schema Detection Skill")
    parser.add_argument("--config", help="Path to JSON config file")
    parser.add_argument("--url", help="API endpoint URL")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--header", action="append", metavar="KEY:VALUE", dest="headers_raw")
    parser.add_argument("--base-param", action="append", metavar="KEY=VALUE", dest="base_params_raw")
    parser.add_argument("--variant", action="append", metavar="JSON", dest="variants_raw",
                        help="JSON object override for one probe call (repeatable)")
    parser.add_argument("--input-desc", dest="input_description", default="")
    parser.add_argument("--probes", type=int, default=3,
                        help="Auto-repeat base params N times if no --variant given")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--no-ai", action="store_true")
    parser.add_argument("--output", help="Write report JSON to file")
    args = parser.parse_args()

    # Load from config file if provided
    if args.config:
        cfg = load_config(args.config)
    else:
        if not args.url:
            parser.error("--url is required (or provide --config)")

        variants = build_variants(args.variants_raw)
        # If no explicit variants, repeat base_params N times to collect more samples
        if not args.variants_raw:
            variants = [{}] * args.probes

        cfg = {
            "url": args.url,
            "method": args.method,
            "headers": parse_headers(args.headers_raw),
            "base_params": parse_base_params(args.base_params_raw),
            "variants": variants,
            "input_description": args.input_description,
            "timeout": args.timeout,
            "delay": args.delay,
            "no_ai": args.no_ai,
        }

    report = run(cfg)

    # Always print to stdout
    print("\n" + "=" * 60)
    print("SCHEMA SUMMARY")
    print("=" * 60)
    print(report["schema_summary"])

    print("\n" + "=" * 60)
    print("BUSINESS ANALYSIS")
    print("=" * 60)
    print(report["business_analysis"])

    print("\n" + "=" * 60)
    print("PROBE SUMMARY")
    print("=" * 60)
    ps = report["probe_summary"]
    print(f"Calls: {ps['total_calls']}  |  Success: {ps['successful']}  |  Status codes: {ps['status_codes']}")

    # Optionally write full report
    if args.output if not args.config else cfg.get("output"):
        out_path = (args.output or cfg.get("output"))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Full report written to %s", out_path)


if __name__ == "__main__":
    main()
