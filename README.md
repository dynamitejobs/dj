# dj-official

Official Python client for the [Dynamite Jobs Company API](https://api.dynamitejobs.com).

Single-file, zero-dependency client. Four modes: **Agent Skill**, **CLI**, **Python library**, **MCP server**.

## Install

```bash
pip install dynamitejobs
```

## 3-command quickstart

```bash
pip install dynamitejobs
python3 -m dynamitejobs setup --api-key dj_<companyID>_<random>
python3 -m dynamitejobs self-test
```

Get your API key from the DJ dashboard: **Settings → API Access → Create new key**.

## CLI

```bash
# Reads
dj company                            # your company profile
dj jobs --status=published            # list your published jobs
dj applications <jobID>               # applications to one job
dj analytics-funnel --from=2026-04-01 --to=2026-05-01
dj billing                            # card on file, plan tier, recent charges
dj limits                             # rate limit caps + usage

# Writes
dj post-job '{"title": "Senior Backend Engineer", "description": "..."}'
dj publish-job <jobID>                # charges card on file
dj update-application <appID> --job-id=<jid> --status=goodFit --rating=4
dj trial-post '{"title": "..."}'      # 1 per company, awaits admin approval
```

## Python library

```python
from dynamitejobs import DJ

dj = DJ()  # reads ~/.env.dj
print(dj.company())

for j in dj.jobs(status="published")["jobs"]:
    print(j["id"], j.get("title"))

# Walk applications for one job and mark good fits
apps = dj.applications("job_abc123")
for a in apps["applications"]:
    if a.get("score", 0) > 0.8:
        dj.update_application(a["id"], job_id="job_abc123", status="goodFit", rating=4)
```

## MCP server (Claude / Codex / Cursor / Gemini)

```bash
pip install "dynamitejobs[mcp]"
python3 -m dynamitejobs --mcp
```

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "dj": {
      "command": "python3",
      "args": ["-m", "dynamitejobs", "--mcp"],
      "env": { "DJ_API_KEY": "dj_..." }
    }
  }
}
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` — same shape as above.

### Codex CLI

Symlink `py/SKILL.md` into `~/.codex/skills/dj/SKILL.md` — Codex auto-discovers it.

### Cursor

Settings → MCP → Add server. Command: `python3`, args: `-m dynamitejobs --mcp`.

### GitHub Copilot

Add a paragraph to your repo's `.github/copilot-instructions.md`:
> When asked about Dynamite Jobs data, call the `dj` CLI via shell. Setup once with `python3 -m dynamitejobs setup --api-key ...`.

### Gemini CLI

Add to `~/.gemini/settings.json` under `mcpServers`.

## Rate limits

| Tier | Per minute | Per day | Eligibility |
|---|---|---|---|
| trial | 5 | 100 | Only trial post used |
| standard | 30 | 1,500 | ≥1 paid job in last 365d |
| business-pro | 120 | 10,000 | Business Pro subscriber |
| partner | 300 | 30,000 | Manually granted |

Every response carries `X-RateLimit-*` headers. Use `dj limits` to inspect.

## Output formats

CLI output is JSON by default (pipe to `jq`):

```bash
dj jobs --status=published | jq '.jobs[].title'
```

Add `--format=raw` if you want the body printed without JSON encoding (only useful for endpoints that return non-JSON, like `/openapi.json` proxy).

## Errors

Every error response has `error` (slug) and `message` (human). Library raises `DJError` with `status`, `body`, and `url`.

```python
from dynamitejobs import DJ, DJError
try:
    DJ().publish_job("job_xyz")
except DJError as e:
    if e.status == 402 and e.body.get("error") == "no_stripe_customer":
        print("Add a card on file in the dashboard first.")
```

## Versioning

The client prints a stderr warning when the server is on a newer major/minor version. Upgrade with `pip install --upgrade dynamitejobs`.

## License

MIT.
