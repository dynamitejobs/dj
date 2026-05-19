---
name: dj
description: Dynamite Jobs Company API — manage jobs, applications, candidates, analytics, and billing for your company from Claude/Codex/Gemini. Auto-discovered as a skill; works in CLI / Python library / MCP modes.
---

# dj — Dynamite Jobs Company API

Programmatic access to Dynamite Jobs for the company you have an API key for. The same surface as the dashboard, scriptable.

## Setup (3 commands)

```bash
pip install dynamitejobs
python3 -m dynamitejobs setup --api-key dj_<companyID>_<random>
python3 -m dynamitejobs self-test
```

Get your API key from the DJ dashboard: **Settings → API Access → Create new key** (owner/admin role required).

## Verbs

### Read
- `dj company` — your company profile (description, website, plan, team)
- `dj jobs [--status=draft|published|expired]` — list your jobs
- `dj job <jobID>` — one job
- `dj applications <jobID>` — applications to one job. Mirrors the dashboard's filters + sorts:
  - Status filter (pick ONE):
    - `--status=good-fit,interested` — CSV of statuses
    - `--only=filtered` — just the auto-filtered pile (= "Not Matching" tag in the UI)
    - `--include=filtered` — default list PLUS filtered
    - (default) hides the filtered pile, matching the UI's default
  - Sort: `--sort=status` (default) | `applied_desc` | `applied_asc` | `salary_desc` | `salary_asc`
  - Filters: `--location=us,gb` | `--salary-range=...` | `--text=alice`
  - Valid statuses: `not-reviewed`, `good-fit`, `interested`, `declined`, `filtered`
- `dj application <applicationID> --job-id=<jobID>` — one application + answers
- `dj candidate <uid>` — candidate profile (only if they applied to one of your jobs)
- `dj analytics-jobs [--from=YYYY-MM-DD --to=YYYY-MM-DD]` — per-job metrics
- `dj analytics-funnel [--from --to]` — views → applies → reviewed → hired
- `dj analytics-sources [--from --to]` — apply source breakdown
- `dj billing` — card on file, plan tier, recent API charges
- `dj limits` — effective rate limits + current usage

### Write (require write scope on the key)
- `dj update-company '{"description": "..."}'` — patch company fields
- `dj post-job '{...}'` — create draft job
- `dj update-job <jobID> '{...}'` — edit draft / restricted published fields
- `dj delete-job <jobID>` — delete draft / unpublish published
- `dj trial-post '{...}'` — submit trial post (1 per company, awaits admin approval)
- `dj publish-job <jobID>` — publish draft (charges card on file)
- `dj repromote-job <jobID> --days=30` — repromote (charges card on file)
- `dj update-application <appID> --job-id=<jid> --status=goodFit --rating=4 --note="..."` — update applicant
- `dj note <appID> --job-id=<jid> --note="..."` — append a note
- `dj export-applications <jobID>` — trigger CSV export to email

## Output

JSON by default. Add `--format=raw` to print without JSON encoding.

## Rate limits

| Tier | Per minute | Per day |
|---|---|---|
| trial | 5 | 100 |
| standard | 30 | 1,500 |
| business-pro | 120 | 10,000 |
| partner | 300 | 30,000 |

Every response carries `X-RateLimit-*` headers. `dj limits` shows your current usage.

## Library

```python
from dynamitejobs import DJ
dj = DJ()  # reads ~/.env.dj
jobs = dj.jobs(status="published")
for j in jobs["jobs"]:
    print(j["id"], j.get("title"))
```

## MCP server

```bash
pip install dynamitejobs[mcp]
python3 -m dynamitejobs --mcp
```

Register in your tool of choice:

**Claude Code** — already in `.mcp.json` of any project that ships `dynamitejobs`:
```json
{"mcpServers": {"dj": {"command": "python3", "args": ["-m", "dynamitejobs", "--mcp"], "env": {"DJ_API_KEY": "dj_..."}}}}
```

**Codex CLI** — add to `~/.codex/skills/` via symlink; auto-discovers this `SKILL.md`.

**Cursor** — Settings → MCP → Add server, command `python3 -m dynamitejobs --mcp`.

## Errors

Every error has `error` (machine-readable slug) and `message` (human). Common slugs:

- `missing_authorization` / `key_not_found` / `key_disabled` / `company_disabled`
- `rate_limit_per_minute` / `rate_limit_per_day` (with `Retry-After` header)
- `no_stripe_customer` — write endpoints with billing-gate failed: no card on file
- `not_your_job` — tried to act on a job that doesn't belong to your company
- `field_locked` — tried to edit a field that's read-only once a job is published

## Versioning

This client prints a stderr warning when the server is on a newer major/minor version. Upgrade with `pip install --upgrade dynamitejobs`.
