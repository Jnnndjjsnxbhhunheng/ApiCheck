---
name: api-detect
description: >
  Probe undocumented API endpoints to infer input/output schema and explain from a business perspective.
  TRIGGER when: user says an API has no docs / unknown response / no schema, or asks
  "这个接口返回什么", "接口没有文档", "帮我分析这个API", "不知道返回结构", "schema是什么",
  "帮我分析这批接口", "这几个接口都要看", "批量检测API", "我有N个接口".
  DO NOT TRIGGER when: user already has an OpenAPI/Swagger spec or complete field docs.
---

# API Schema Detection Skill

Probe one or multiple undocumented API endpoints using `probe.py`, then produce
a business-level analysis of each interface.

`probe.py` handles all HTTP calls and schema inference (stable, repeatable).
Claude reads the JSON output and provides business analysis.

## Workflow

Make a todo list and complete each step in order.

---

### Step 0: Single vs Batch mode

**If the user provides a single URL → skip to Step 1.**

**If the user provides multiple APIs or a document describing several interfaces → Batch mode:**

1. **Parse the document** — extract all interfaces into a list. Show the user for confirmation before proceeding:

   | # | 接口名 | Method | URL | 已知参数 |
   |---|--------|--------|-----|---------|

2. **Generate `apis.json`** — write a batch config file:

   ```json
   [
     {
       "name": "订单列表",
       "url": "https://api.example.com/v1/orders",
       "method": "GET",
       "headers": { "Authorization": "Bearer TOKEN" },
       "base_params": {},
       "variants": [{"page":"1"}, {"page":"2"}, {"status":"completed"}],
       "input_description": "分页查询订单，支持 status 过滤"
     }
   ]
   ```

3. **Install dependency if needed:**

   ```bash
   pip install -q requests
   ```

4. **Run batch probe:**

   ```bash
   cd /home/user/ApiCheck && python probe.py --batch apis.json
   ```

5. **Analyze each result** — for every item in the JSON array output, apply Steps 4–5 below.

6. **Output batch summary report** — see Batch Wrap up section.

---

### Step 1: Collect information

Ask the user for anything not yet provided:

- **URL** (required)
- **HTTP method** — default `GET`
- **Auth headers** — e.g. `Authorization: Bearer <token>`
- **Known input parameters** — even a rough description is enough
- **Probe variants** — different param combinations to maximize field coverage

### Step 2: Install dependency if needed

```bash
pip install -q requests
```

### Step 3: Run the probe

```bash
cd /home/user/ApiCheck && python probe.py \
  --url "https://api.example.com/v1/orders" \
  --method GET \
  --header "Authorization: Bearer TOKEN" \
  --variant '{"page": "1"}' \
  --variant '{"page": "2"}' \
  --variant '{"status": "completed"}'
```

`probe.py` outputs a single JSON object to stdout:

```json
{
  "url": "...",
  "method": "GET",
  "probes": 3,
  "success": 3,
  "status_codes": [200, 200, 200],
  "inferred_schema": { "$schema": "...", "type": "object", "properties": { ... } },
  "sample_response": { ... }
}
```

### Step 4: Infer the input schema

From the known parameters and what the API accepted/rejected, document:

- Parameter names, types, required vs optional
- Observed valid values and ranges
- Validation errors (4xx) that reveal constraints

### Step 5: Business-level analysis

Read `inferred_schema` and `sample_response` from the probe output, then explain:

- **Purpose**: What business problem does this API solve?
- **Field meanings**: Plain-language description of each output field
- **Key fields**: Critical for business logic
- **Sensitive fields**: PII, financial data, security tokens
- **Use cases**: When and why a developer calls this API
- **Downstream usage**: What you typically do with the response

### Step 6: Handle errors

| Status | Action |
|--------|--------|
| 401/403 | Ask user for correct credentials, do not guess tokens |
| 404 | Confirm URL with user, try alternate paths |
| 422/400 | Note validation error — reveals input constraints |
| 5xx | Retry once after 2s; note instability in report |
| Timeout | Try with minimal params |

In **batch mode**: record the failure for that interface and continue to the next — never abort the whole batch.

---

## Single Interface Wrap up

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

---

## Batch Wrap up

```markdown
# API 批量探测报告

## 总览
| # | 接口名 | Method | URL | 探测次数 | 成功率 | 状态 |
|---|--------|--------|-----|---------|--------|------|
| 1 | 订单列表 | GET | /v1/orders | 3 | 100% | ✓ |
| 2 | 用户信息 | GET | /v1/user | 3 | 67% | ✓ |
| 3 | 支付回调 | POST | /v1/pay/notify | 0 | 0% | ✗ 401 |

## 各接口详情

### 1. 订单列表
**用途**: ...
**输入参数**: | 参数名 | 类型 | 必填 | 说明 |
**输出字段**: | 字段名 | 类型 | 是否必返回 | 业务含义 |
**JSON Schema**: ```json { ... } ```
**需要关注**: ...

### 2. ...

## 失败接口
| 接口名 | 原因 | 建议 |
```
