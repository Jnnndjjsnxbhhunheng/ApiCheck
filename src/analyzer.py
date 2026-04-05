"""
Analyzer: Uses Claude to produce a business-level explanation of the API
based on collected probe results and inferred schema.
"""

import json
import anthropic


SYSTEM_PROMPT = """You are a senior API analyst. Given raw API probe data, you will:
1. Explain what this API endpoint does from a **business perspective** (not technical jargon).
2. Document each output field with a plain-language description of its business meaning.
3. Identify the key use cases for this API.
4. Flag any fields that appear sensitive (PII, financial, security-related).
5. Suggest what a developer would typically do with this response.

Be concise, practical, and focused on business value. Write in Chinese if the input description is in Chinese, otherwise use English."""


def build_analysis_prompt(
    url: str,
    method: str,
    input_description: str,
    probe_results: list[dict],
    inferred_schema: dict,
    schema_summary: str,
) -> str:
    # Limit probe samples shown to Claude to avoid excessive token use
    sample_bodies = [r["body"] for r in probe_results if r.get("status_code", 0) in range(200, 300)][:3]

    return f"""## API 基本信息

- **Endpoint**: `{method} {url}`
- **输入参数描述**: {input_description or "（未提供）"}

## 响应样本（最多3条成功响应）

```json
{json.dumps(sample_bodies, ensure_ascii=False, indent=2)}
```

## 推断的输出 Schema（结构摘要）

```
{schema_summary}
```

## 推断的 JSON Schema（完整）

```json
{json.dumps(inferred_schema, ensure_ascii=False, indent=2)}
```

请基于以上信息，从**业务角度**完整分析这个 API：
1. 这个接口在业务上做什么？解决什么问题？
2. 每个返回字段的业务含义是什么？
3. 典型使用场景有哪些？
4. 有哪些字段需要特别关注（敏感信息、关键业务字段）？
5. 作为调用方，拿到这个响应后通常下一步怎么用？"""


class APIAnalyzer:
    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 4096):
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens

    def analyze(
        self,
        url: str,
        method: str,
        input_description: str,
        probe_results: list[dict],
        inferred_schema: dict,
        schema_summary: str,
    ) -> str:
        prompt = build_analysis_prompt(
            url, method, input_description, probe_results, inferred_schema, schema_summary
        )
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
