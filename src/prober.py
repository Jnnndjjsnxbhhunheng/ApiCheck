"""
API Prober: Makes multiple calls to an API endpoint with varying parameters,
collects all responses to maximize schema coverage.
"""

import time
import json
import copy
import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)


class APIProbeResult:
    def __init__(self, params: dict, status_code: int, body: Any, elapsed_ms: float, error: str | None = None):
        self.params = params
        self.status_code = status_code
        self.body = body
        self.elapsed_ms = elapsed_ms
        self.error = error

    def to_dict(self) -> dict:
        return {
            "params": self.params,
            "status_code": self.status_code,
            "body": self.body,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "error": self.error,
        }


class APIProber:
    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        base_params: dict | None = None,
        probe_variants: list[dict] | None = None,
        timeout: int = 15,
        delay_between_calls: float = 0.5,
    ):
        """
        url: API endpoint
        method: HTTP method (GET/POST/PUT etc.)
        headers: fixed headers for every request (e.g. Authorization)
        base_params: baseline query params / body fields
        probe_variants: list of param overrides to merge into base_params for each probe call.
                        If None, a single call with base_params is made.
        timeout: per-request timeout in seconds
        delay_between_calls: seconds to wait between consecutive requests
        """
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.base_params = base_params or {}
        self.probe_variants = probe_variants or [{}]  # at least one call
        self.timeout = timeout
        self.delay = delay_between_calls

    def _merge(self, base: dict, override: dict) -> dict:
        merged = copy.deepcopy(base)
        merged.update(override)
        return merged

    def _call(self, params: dict) -> APIProbeResult:
        start = time.monotonic()
        try:
            if self.method in ("GET", "DELETE", "HEAD"):
                resp = requests.request(
                    self.method, self.url,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout,
                )
            else:
                resp = requests.request(
                    self.method, self.url,
                    json=params,
                    headers=self.headers,
                    timeout=self.timeout,
                )
            elapsed = (time.monotonic() - start) * 1000
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            return APIProbeResult(params, resp.status_code, body, elapsed)
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("Request failed: %s", e)
            return APIProbeResult(params, -1, None, elapsed, error=str(e))

    def probe(self) -> list[APIProbeResult]:
        results = []
        for i, variant in enumerate(self.probe_variants):
            params = self._merge(self.base_params, variant)
            logger.info("Probe %d/%d  params=%s", i + 1, len(self.probe_variants), params)
            result = self._call(params)
            results.append(result)
            if i < len(self.probe_variants) - 1:
                time.sleep(self.delay)
        return results

    def successful_bodies(self, results: list[APIProbeResult]) -> list[Any]:
        """Return response bodies from 2xx responses only."""
        return [r.body for r in results if 200 <= r.status_code < 300 and r.body is not None]
