---
name: api-detect
description: >
  Auto-probe an undocumented API to infer input/output schema and explain it from a business perspective.
  TRIGGER when: user says an API has no docs, unknown response format, or asks
  "这个接口返回什么", "接口没有文档", "帮我分析这个接口", "不知道返回结构", "schema是什么".
  DO NOT TRIGGER when: user already has an OpenAPI/Swagger spec or complete field documentation.
---

# API Schema Detection Skill

Probe an undocumented API multiple times, infer the complete input/output schema
from the collected responses, and produce a business-level explanation.

## Workflow

Make a todo list and complete each step in order.

### 1. Collect API information

Ask the user for anything not yet provided:

- **URL** (required)
- **HTTP method** — default `GET`
- **Auth headers** — e.g. `Authorization: Bearer <token>`
- **Known input parameters** — even a rough description is enough
- **Probe variants** — different param combinations that expose more fields
  (e.g. different `status`, `page`, `type` values)

If the user already has a config file, skip to step 2 and use `--config <path>`.

### 2. Install dependencies if needed

```bash
cd /home/user/ApiCheck
pip install -q requests anthropic
```

### 3. Run the probe

Assemble and run `skill.py` with the gathered information:

```bash
cd /home/user/ApiCheck && python skill.py \
  --url "https://api.example.com/v1/orders" \
  --method GET \
  --header "Authorization: Bearer TOKEN" \
  --input-desc "分页查询订单，支持 status 过滤" \
  --variant '{"page": "1"}' \
  --variant '{"page": "2"}' \
  --variant '{"status": "completed"}' \
  --output report.json
```

Or with a config file:

```bash
cd /home/user/ApiCheck && python skill.py --config probe_config.json
```

The script will:
1. Call the API once per `--variant` (union-merge covers more fields)
2. Infer a JSON Schema from all 2xx responses
3. Call Claude to produce a business-level analysis
4. Print schema summary + analysis to stdout; write full JSON to `--output` if specified

### 4. Present results to the user

Show three sections clearly:

**Output Schema** — the inferred field tree (types, nested objects, arrays, formats).

**Business Analysis** — what the API does, meaning of each field, use cases,
sensitive fields, and how to use the response downstream.

**Probe Stats** — total calls / successful / HTTP status codes seen.

### 5. Offer next steps

- More variants → better field coverage: suggest additional `--variant` values
- Save report: remind user the full JSON is in `--output` if they specified it
- Auth issues (401/403): ask for correct credentials and retry

## Wrap up

End with a summary in this format:

**接口用途**: 一句话说明这个 API 做什么

**返回字段总览**:

| 字段名 | 类型 | 业务含义 |
|--------|------|----------|
| ...    | ...  | ...      |

**需要关注**: 敏感字段、关键业务字段、分页标记等

**建议下一步**: 开发者拿到响应后通常怎么用

---

## Config file format reference

```json
{
  "url": "https://api.example.com/v1/orders",
  "method": "GET",
  "headers": { "Authorization": "Bearer TOKEN" },
  "base_params": { "pageSize": "20" },
  "variants": [
    {"page": "1"},
    {"page": "2"},
    {"status": "completed"},
    {"status": "pending"}
  ],
  "input_description": "分页查询订单列表，支持按 status 过滤（completed/pending/cancelled）",
  "timeout": 15,
  "delay": 0.5,
  "output": "order_report.json"
}
```
