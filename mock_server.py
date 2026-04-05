#!/usr/bin/env python3
"""
mock_server.py — Fake API server for testing probe.py against apis.py definitions.

Reads apis.py at startup and registers one Flask route per unique (method, path).
Mock responses are defined here in MOCK_RESPONSES — decoupled from apis.py.

Usage:
    python mock_server.py          # foreground
    python mock_server.py &        # background (store PID to kill later)
    PORT=9000 python mock_server.py  # custom port
"""

import importlib.util
import os
import sys
from urllib.parse import urlparse

try:
    from flask import Flask, jsonify
except ImportError:
    sys.exit("flask not installed. Run: pip install flask")

PORT = int(os.environ.get("MOCK_PORT", 8765))
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Mock responses — keyed by (METHOD, /path)
# Add new entries here when you add new APIs to apis.py
# ---------------------------------------------------------------------------

MOCK_RESPONSES: dict[tuple[str, str], object] = {
    ("GET", "/users/1"): {
        "id": 1,
        "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "username": "zhang_san",
        "email": "zhang.san@example.com",
        "full_name": "张三",
        "age": 28,
        "is_active": True,
        "balance": 1024.50,
        "avatar_url": "https://cdn.example.com/avatars/1.png",
        "created_at": "2023-06-15T08:30:00Z",
        "last_login": "2026-04-04T14:22:10Z",
        "phone": None,
        "address": {
            "city": "上海",
            "district": "浦东新区",
            "street": "张江高科技园区博云路2号",
            "zip_code": "201203",
        },
        "tags": ["vip", "early_adopter"],
        "preferences": {
            "language": "zh-CN",
            "notifications_enabled": True,
            "theme": "dark",
        },
    },
    ("GET", "/orders"): {
        "total": 2,
        "page": 1,
        "page_size": 20,
        "has_next": False,
        "items": [
            {
                "order_id": "ORD-20240615-001",
                "status": "completed",
                "created_at": "2024-06-15T10:00:00Z",
                "amount": 299.00,
                "currency": "CNY",
                "customer_id": 1,
                "is_paid": True,
                "paid_at": "2024-06-15T10:05:32Z",
                "note": None,
                "items": [
                    {
                        "sku": "PROD-001",
                        "name": "云服务套餐A",
                        "quantity": 1,
                        "unit_price": 299.00,
                    }
                ],
            },
            {
                "order_id": "ORD-20240620-002",
                "status": "completed",
                "created_at": "2024-06-20T14:30:00Z",
                "amount": 598.00,
                "currency": "CNY",
                "customer_id": 1,
                "is_paid": True,
                "paid_at": "2024-06-20T14:31:10Z",
                "note": "加急处理",
                "items": [
                    {
                        "sku": "PROD-001",
                        "name": "云服务套餐A",
                        "quantity": 2,
                        "unit_price": 299.00,
                    }
                ],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Route registration — reads apis.py, extracts paths, binds to MOCK_RESPONSES
# ---------------------------------------------------------------------------

def register_routes() -> None:
    spec = importlib.util.spec_from_file_location("_apis", "apis.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    registered: set[tuple[str, str]] = set()

    for api in mod.APIS:
        path = urlparse(api["url"]).path
        method = api.get("method", "GET").upper()
        key = (method, path)
        if key in registered:
            continue
        registered.add(key)

        def make_handler(k: tuple[str, str]):
            def handler(**kwargs):
                data = MOCK_RESPONSES.get(k)
                if data is None:
                    return jsonify({"error": f"no mock defined for {k[0]} {k[1]}"}), 404
                return jsonify(data), 200
            handler.__name__ = f"mock_{k[0]}_{k[1].replace('/', '_').strip('_')}"
            return handler

        app.add_url_rule(path, view_func=make_handler(key), methods=[method])
        print(f"  {method:6s} {path}")

    undefined = [k for k in MOCK_RESPONSES if k not in registered]
    if undefined:
        print(f"  (unused mock responses: {undefined})")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists("apis.py"):
        sys.exit("apis.py not found — run from the project root directory.")

    print("Loading apis.py and registering routes:")
    register_routes()
    print(f"\nMock server running on http://localhost:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
