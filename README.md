# api-detect

用于探测缺少文档的 API，推断其输入/输出结构，并生成业务层面的分析说明。

## 安装

在你的项目根目录执行以下命令下载这个技能：

```bash
curl -fsSL https://raw.githubusercontent.com/jnnndjjsnxbhhunheng/apicheck/main/SKILL.md -o SKILL.md && \
curl -fsSL https://raw.githubusercontent.com/jnnndjjsnxbhhunheng/apicheck/main/probe.py -o probe.py && \
pip install -q requests
```

## 用法

告诉 Claude：

- **单个接口**：`帮我分析这个接口 https://api.example.com/v1/orders，没有文档`
- **批量接口**：`我有 10 个接口的文档，帮我全部分析` → 直接粘贴文档内容

Claude 会通过技能工具自动调用 `api-detect`。
