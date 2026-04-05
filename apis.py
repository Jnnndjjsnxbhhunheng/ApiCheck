"""
apis.py — Define all your API endpoints here.

Each entry in APIS is one interface. Fields:
  name        : Human-readable name (used in reports)
  url         : Full URL, use http://localhost:8765/... when testing with mock_server.py
  method      : HTTP method (GET, POST, PUT, PATCH, DELETE)
  headers     : Dict of request headers (e.g. Authorization)
  params      : Query params (GET) or request body (POST/PUT)
  description : What this API does and what the input params mean
"""

APIS = [
    {
        "name": "用户详情",
        "url": "http://localhost:8765/users/1",
        "method": "GET",
        "headers": {},
        "params": {},
        "description": "根据 user_id 获取用户完整信息，包括账户状态、地址、偏好设置等",
    },
    {
        "name": "订单列表",
        "url": "http://localhost:8765/orders",
        "method": "GET",
        "headers": {},
        "params": {"page": "1", "status": "completed"},
        "description": "分页查询当前用户的订单列表，支持按 status 过滤（completed/pending/cancelled）",
    },
]
