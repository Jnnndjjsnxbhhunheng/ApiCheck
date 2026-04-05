Probe an undocumented API endpoint to detect its input/output schema and produce a business-level analysis using Claude.

The user invoked: /api-detect $ARGUMENTS

## Your workflow

Make a todo list and work through these steps one by one.

### 1. Parse $ARGUMENTS

If `$ARGUMENTS` starts with `--config`, the user is pointing to a JSON config file.
Run: `python skill.py --config <path>`

Otherwise, parse inline flags from `$ARGUMENTS`:

| Flag | Meaning | Default |
|------|---------|---------|
| First positional arg or `--url` | API endpoint URL (required) | — |
| `--method METHOD` | HTTP method | `GET` |
| `--header "Key: Value"` | Request header, repeatable | — |
| `--base-param "key=value"` | Fixed query/body param, repeatable | — |
| `--variant '{"k":"v"}'` | JSON param override for one probe call, repeatable | — |
| `--input-desc "..."` | Free-text description of known input params | — |
| `--probes N` | Number of probe calls if no `--variant` given | `3` |
| `--timeout N` | Per-request timeout in seconds | `15` |
| `--delay N` | Seconds between requests | `0.5` |
| `--no-ai` | Skip Claude analysis, output schema only | off |
| `--output path.json` | Write full JSON report to file | — |

### 2. Run the skill script

From the project root, run:

```bash
cd /home/user/ApiCheck && python skill.py <assembled flags>
```

Example assembled command:
```bash
python skill.py \
  --url "https://api.example.com/orders" \
  --method GET \
  --header "Authorization: Bearer TOKEN" \
  --variant '{"page":"1"}' \
  --variant '{"page":"2"}' \
  --input-desc "分页查询订单，支持 status 过滤"
```

If the script fails because `requests` or `anthropic` are not installed:
```bash
pip install requests anthropic && python skill.py <flags>
```

### 3. Display results to the user

After the script completes, present the output clearly in three sections:

**Schema Structure** — the inferred output schema tree printed by the script.

**Business Analysis** — the Claude-generated explanation printed by the script.

**Probe Statistics** — total calls, success count, observed HTTP status codes.

### 4. Offer next steps

Ask the user if they want to:
- Save the full JSON report: re-run with `--output report.json`
- Probe with more parameter variants to improve field coverage
- Adjust headers/auth and retry

## Wrap up

In your final message, provide:
- What the API does (one sentence summary from the analysis)
- The inferred output schema in a concise table: `field | type | business meaning`
- Any sensitive or notable fields flagged by the analysis
- Suggested next step for the developer
