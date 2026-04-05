---
name: api-detect
description: >
  Probe an undocumented API multiple times to infer its input/output schema and
  explain it from a business perspective.
  TRIGGER when: user says an API has no docs / unknown response / no schema, or asks
  "这个接口返回什么", "接口没有文档", "帮我分析这个API", "不知道返回结构", "schema是什么".
  DO NOT TRIGGER when: user already has an OpenAPI/Swagger spec or complete field docs.
---

# API Schema Detection Skill

Probe an undocumented API endpoint multiple times with varying parameters,
infer the full input/output schema by merging all responses, and produce
a business-level explanation.

## Workflow

Make a todo list and complete each step in order.

### 1. Collect information

Ask the user for anything not yet provided:

- **URL** (required)
- **HTTP method** — default `GET`
- **Auth headers** — e.g. `Authorization: Bearer <token>`
- **Known input parameters** — even a rough description is enough
- **Probe variants** — different param combinations to maximize field coverage
  (e.g. different page numbers, status values, IDs, filters)

### 2. Probe the API multiple times

Use the Bash tool to call the API with `curl`. Run one call per variant.
Collect every response body, HTTP status code, and notable headers.

Example single call:
```bash
curl -s -w "\n%{http_code}" \
  -H "Authorization: Bearer TOKEN" \
  "https://api.example.com/v1/orders?page=1&status=completed"
```

Aim for at least 3–5 calls with different parameter combinations so that
fields which only appear conditionally (e.g. nullable fields, paginated data,
different status branches) are captured.

### 3. Infer the output schema

From all successful (2xx) response bodies, build a JSON Schema by:

1. **Union-merging** all responses — a field is included if it appears in *any* response
2. **Detecting types**: `string`, `integer`, `number`, `boolean`, `array`, `object`, `null`
3. **Detecting formats**: ISO dates (`date`, `date-time`), UUIDs, URLs, emails
4. **Noting optionality**: mark fields that only appear in some responses as optional
5. **Handling arrays**: infer the item schema from all observed array elements

Output the schema in JSON Schema (draft 2020-12) format.

### 4. Infer the input schema

From the known parameters and what the API accepted/rejected, document:

- Parameter names, types, and whether required or optional
- Observed valid values and ranges
- Any validation errors (4xx responses) that reveal constraints

### 5. Produce a business-level analysis

Explain the API as if writing for a product manager or a new developer:

- **Purpose**: What business problem does this API solve?
- **Field meanings**: Plain-language description of each output field
- **Key fields**: Which fields are critical for business logic?
- **Sensitive fields**: Flag any PII, financial data, or security tokens
- **Use cases**: When and why would a developer call this API?
- **Downstream usage**: What do you typically do with the response?

### 6. Handle errors

| Status | Action |
|--------|--------|
| 401/403 | Ask user for correct credentials, do not guess tokens |
| 404 | Confirm URL with user, try alternate paths |
| 422/400 | Note the validation error — it reveals input constraints |
| 5xx | Retry once after 2s; note instability in the report |
| Timeout | Reduce scope, try with minimal params |

## Wrap up

End with a structured summary:

**接口用途**: 一句话说明业务功能

**输入参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|

**输出字段**:

| 字段名 | 类型 | 是否必返回 | 业务含义 |
|--------|------|-----------|----------|

**完整 JSON Schema**:
```json
{ "$schema": "...", "type": "...", "properties": { ... } }
```

**需要关注**: 敏感字段、分页标记、状态枚举值等

**建议下一步**: 开发者拿到响应后通常怎么用
