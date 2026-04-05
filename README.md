# api-detect

Probe undocumented APIs to infer input/output schema and produce a business-level analysis.

## Install

Run this in your project root to download the skill:

```bash
curl -fsSL https://raw.githubusercontent.com/jnnndjjsnxbhhunheng/apicheck/main/SKILL.md -o SKILL.md && \
curl -fsSL https://raw.githubusercontent.com/jnnndjjsnxbhhunheng/apicheck/main/probe.py -o probe.py && \
pip install -q requests
```

## Usage

Tell Claude:

- **Single API**: "帮我分析这个接口 https://api.example.com/v1/orders，没有文档"
- **Batch**: "我有10个接口的文档，帮我全部分析" → 粘贴文档内容

Claude will invoke `api-detect` automatically via the Skill tool.
