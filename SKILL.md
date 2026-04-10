---
name: api-detect
description: >
  探测缺少文档的 API 接口，推断输入/输出 schema，并从业务角度解释接口含义。
  当用户提到以下情况时触发：接口没有文档 / 不知道返回内容 / 没有 schema，或用户说
  “这个接口返回什么”、“接口没有文档”、“帮我分析这个 API”、“不知道返回结构”、“schema 是什么”、
  “帮我分析这批接口”、“这几个接口都要看”、“批量检测 API”、“我有 N 个接口”、
  “用户有一个 apis.py 文件”、“API 是用 Python 文件定义的”、“我有 apis.py”。
  当用户已经提供 OpenAPI / Swagger 规范或完整字段文档时，不要触发。
---

# API Schema 探测技能

使用 `probe.py` 探测一个或多个缺少文档的 API 接口，然后为每个接口输出业务层面的分析。

`probe.py` 负责所有 HTTP 请求与 schema 推断（稳定且可重复）。
Claude 读取 JSON 输出后，补充业务分析结论。

## 工作流

先建立待办清单，并按顺序完成每一步。

---

### 第 0 步：选择输入模式

---

**① 如果用户有 `apis.py` 文件 → 使用 apis.py 模式（优先）：**

1. **如果需要，先安装依赖：**

   ```bash
   pip install -q requests flask
   ```

2. **在后台启动模拟服务：**

   ```bash
   cd /home/user/ApiCheck && python mock_server.py &
   MOCK_PID=$!
   sleep 1
   ```

3. **针对 Python 文件运行探测：**

   ```bash
   cd /home/user/ApiCheck && python probe.py --from-py apis.py
   ```

4. **分析每个结果** —— 对 JSON 数组输出中的每一项，执行下面第 4～5 步。

5. **输出批量总结报告** —— 参考文末的“批量收尾”部分。

6. **停止模拟服务：**

   ```bash
   kill $MOCK_PID 2>/dev/null || true
   ```

---

**② 如果用户提供了多个 API，或给了一份描述多个接口的文档 → 使用批量模式：**

1. **解析文档** —— 提取所有接口形成列表，并在继续前展示给用户确认：

   | # | 接口名 | 请求方法 | URL | 已知参数 |
   |---|--------|--------|-----|---------|

2. **生成 `apis.json`** —— 写出批量配置文件：

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

3. **如果需要，先安装依赖：**

   ```bash
   pip install -q requests
   ```

4. **运行批量探测：**

   ```bash
   cd /home/user/ApiCheck && python probe.py --batch apis.json
   ```

5. **分析每个结果** —— 对 JSON 数组输出中的每一项，执行下面第 4～5 步。

6. **输出批量总结报告** —— 参考文末的“批量收尾”部分。

---

**③ 如果用户只提供了单个 URL → 直接跳到第 1 步。**

---

### 第 1 步：收集信息

向用户索取尚未提供的信息：

- **URL**（必需）
- **HTTP 请求方法** —— 默认为 `GET`
- **鉴权请求头** —— 例如 `Authorization: Bearer <token>`
- **已知输入参数** —— 即使只是粗略描述也可以
- **探测变体** —— 提供不同参数组合，以便尽可能覆盖更多字段

### 第 2 步：如有需要，安装依赖

```bash
pip install -q requests
```

### 第 3 步：运行探测

```bash
cd /home/user/ApiCheck && python probe.py \
  --url "https://api.example.com/v1/orders" \
  --method GET \
  --header "Authorization: Bearer TOKEN" \
  --variant '{"page": "1"}' \
  --variant '{"page": "2"}' \
  --variant '{"status": "completed"}'
```

`probe.py` 会向 stdout 输出一个 JSON 对象：

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

### 第 4 步：推断输入 schema

基于已知参数，以及接口对不同请求的接受 / 拒绝情况，整理：

- 参数名、类型、必填 / 选填
- 观察到的合法取值与范围
- 暴露约束条件的校验错误（4xx）

### 第 5 步：业务层分析

读取探测输出中的 `inferred_schema` 和 `sample_response`，然后解释：

- **接口用途**：这个 API 解决什么业务问题？
- **字段含义**：用通俗语言解释每个输出字段
- **关键字段**：哪些字段对业务逻辑最关键
- **敏感字段**：PII、财务数据、安全令牌等
- **使用场景**：开发者会在什么情况下调用它，为什么要调用
- **下游用法**：通常会如何消费这个返回结果

### 第 6 步：处理错误

| 状态 | 动作 |
|------|------|
| 401/403 | 向用户索取正确凭证，不要猜测 token |
| 404 | 与用户确认 URL，尝试可能的备用路径 |
| 422/400 | 记录校验错误 —— 这些信息能暴露输入约束 |
| 5xx | 间隔 2 秒后重试一次，并在报告中注明接口不稳定 |
| Timeout | 用最小参数重试 |

在 **批量模式** 下：记录该接口失败原因，并继续处理下一个接口 —— 不要因为单个失败而中断整批任务。

---

## 单接口收尾

**接口用途**：一句话说明业务功能

**输入参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|

**输出字段**：

| 字段名 | 类型 | 是否必返回 | 业务含义 |
|--------|------|-----------|----------|

**完整 JSON 结构**：
```json
{ "$schema": "...", "type": "...", "properties": { ... } }
```

**需要关注**：敏感字段、分页标记、状态枚举值等

**建议下一步**：开发者拿到响应后通常怎么使用

---

## 批量收尾

```markdown
# API 批量探测报告

## 总览
| # | 接口名 | 请求方法 | URL | 探测次数 | 成功率 | 状态 |
|---|--------|--------|-----|---------|--------|------|
| 1 | 订单列表 | GET | /v1/orders | 3 | 100% | ✓ |
| 2 | 用户信息 | GET | /v1/user | 3 | 67% | ✓ |
| 3 | 支付回调 | POST | /v1/pay/notify | 0 | 0% | ✗ 401 |

## 各接口详情

### 1. 订单列表
**用途**：...
**输入参数**：| 参数名 | 类型 | 必填 | 说明 |
**输出字段**：| 字段名 | 类型 | 是否必返回 | 业务含义 |
**JSON 结构**：```json { ... } ```
**需要关注**：...

### 2. ...

## 失败接口
| 接口名 | 原因 | 建议 |
```
