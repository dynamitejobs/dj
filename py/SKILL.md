---
name: dj
description: Dynamite Jobs Company API — manage jobs, applications, candidates, analytics, and billing for your company from Claude/Codex/Gemini/Cursor. Self-contained single-file Python client (CLI / library / MCP). Auto-discovered as an Agent Skill via this SKILL.md.
tags: dj, dynamite-jobs, ats, hiring
---

# DJ Company API Skill

Read and act on your own **Dynamite Jobs** company data via the public DJ
Company API at `https://api.dynamitejobs.com` — your company profile, job
posts, applications, candidates (scoped to ones who applied to your jobs),
analytics, and billing. Everything is scoped to the **company** that owns the
API key. It's the same surface as the dashboard, scriptable.

## Two ways to use it

| Path | What it is | Pick it when |
|---|---|---|
| **Hosted MCP** (remote) | The DJ Company API served as a remote Streamable-HTTP MCP server at `https://api.dynamitejobs.com/mcp` — nothing to install, always current | You're an MCP-capable app (Claude, ChatGPT, Cursor) — connect the URL and authenticate with your `dj_` key (Bearer / `X-API-Key` header) or one-click OAuth |
| **Local client** (this file) | One stdlib-only Python file: a CLI (`dj …`), a Python library (`from dynamitejobs import DJ`), and a local stdio MCP server (`dj --mcp`) | You're an agent that can run Python or shell — you get a CLI, scriptable library calls, and a local MCP server you can pin/run offline |
| **Zero-install local MCP** (`uvx`/`pipx`) | The same stdio MCP server, launched on demand by `uvx`/`pipx` | You want the local server auto-launched without managing a clone |

> The hosted endpoint supports **OAuth** (one-click Connect — approve in your DJ
> dashboard) or a `dj_` API key as a Bearer / `X-API-Key` header. The source of
> truth for the current transport is
> `https://api.dynamitejobs.com/.well-known/mcp.json`.

**Rule of thumb:** for chat apps that speak remote MCP, use the **hosted** URL.
If you can execute commands and want offline/pinned use, prefer the local client
(CLI + library + MCP). All paths authenticate with the same `dj_` key.

## Install the local client

```bash
# A) PyPI — quickest. Gives you the `dj` command + the importable library.
pip install dynamitejobs            # CLI + library
pip install 'dynamitejobs[mcp]'     # + local MCP server (dj --mcp)

# B) uvx — no install, auto-updates on every run (great for an MCP config)
uvx --from 'dynamitejobs[mcp]' dj --help

# C) Clone — full repo (MCP config, docs, examples)
git clone https://github.com/dynamitejobs/dj.git && cd dj
```

> **Command form in this doc:** examples use the installed `dj` command. From a
> clone, replace `dj` with `python3 py/dj.py` (e.g. `python3 py/dj.py company`).

## Setup (get + save your key)

Each company needs its own API key. Generate one from the DJ dashboard →
**Settings → API Access → Create new key** (owner/admin role required). Keys
look like `dj_<companyID>_<random>` and are revocable from the same screen.

```bash
# Save it (writes ~/.env.dj, chmod 600, gitignored)
dj setup --api-key dj_<companyID>_<random>

# Verify env, key shape, a live /company call, and the rate-limit tier
dj self-test
```

Alternatively set `DJ_API_KEY` in the environment instead of running `setup` —
an explicit env var always wins over `~/.env.dj`. This is how `uvx`/`pipx` and
MCP server configs receive the key (the `env` block of the server config).

## Discovering endpoints

You don't need to memorize the surface — discover it live:

```bash
# Every command + a one-line description
dj --help

# Detail for one command (flags, args)
dj jobs --help

# Machine-readable recipes: ordered {method, path} steps for common goals.
# No API key needed (it's on the unauthenticated discovery surface).
dj workflows
```

Authoritative references:

- **`https://dynamitejobs.com/developers/`** — full human reference, every endpoint/param/response, regenerated on every deploy (always current)
- **`https://api.dynamitejobs.com/openapi.json`** — the OpenAPI 3 spec (machine-readable)
- **`https://api.dynamitejobs.com/.well-known/mcp.json`** — MCP discovery descriptor (transport, auth, install)

### Read vs. write (MCP annotations)

Every MCP tool is annotated: reads carry `readOnlyHint: true`; writes carry
`readOnlyHint: false` (and `destructiveHint: true` for `delete_job`), plus a
"⚠️ Write operation" note in the description. Reads (`get_company`, `list_jobs`,
`analytics_funnel`, …) are safe to run freely; writes (`update_company`,
`create_job`, `update_application`, …) mutate **your** company data. Clients
that honor annotations can auto-approve reads and prompt on writes.

## Pagination

List-returning commands (`jobs`, `applications`) take cursor pagination flags:

```bash
<command> [--limit N] [--cursor TOKEN]
```

- `--limit N` — page size (default 25)
- `--cursor TOKEN` — opaque continuation token from the previous response

## Output formats

```bash
dj company             # pretty JSON (default)
dj company --format raw # print without JSON re-encoding
```

## Version warnings

Every API response carries an `X-API-Version` header. The client compares it
against its own `VERSION` constant. When the **server's major or minor** is
ahead of the client, you'll see a one-shot stderr warning prompting an upgrade:

```
⚠  DJ Company API has new features available (server 1.2.0, this client built for 1.1.0).
   Update the client:  pip install --upgrade dynamitejobs
```

Patch differences (e.g. server 1.1.5 vs client 1.1.0) are silent — bug fixes
only. The warning fires once per process so it doesn't spam script users.

## Local development

Override the API base URL to test against a local server:

```bash
# CLI
dj setup --api-key dj_... --base-url http://localhost:8087

# or per-process env var
DJ_API_BASE_URL=http://localhost:8087 dj company

# Python
DJ(base_url="http://localhost:8087")
```

## Commands

### Setup & diagnostics

```bash
dj setup --api-key dj_<companyID>_<random>   # save your key
dj self-test                                  # validate env + a live /company call
dj workflows                                  # machine-readable recipes (no key)
```

### Company

```bash
dj company                                    # your company profile
dj update-company '{"description": "We hire remote-first."}'
```

### Jobs

`JobStatus` values mirror the dashboard. Newly-created jobs are `unpublished`
(not `draft`).

```bash
dj jobs                                        # all your jobs
dj jobs --status published                     # filter by status
#   unpublished | pending | published | expired | finished | fulfilled | deleted | rejected
dj job <jobID>                                 # one job

dj post-job '{"title": "Senior Go Engineer", "description": "..."}'  # creates an unpublished job
dj update-job <jobID> '{"title": "Staff Go Engineer"}'              # edit unpublished / restricted published fields
dj delete-job <jobID>                          # delete unpublished / unpublish published
dj trial-post '{"title": "...", "description": "..."}'             # 1 per company, awaits admin approval
```

> **Publishing is dashboard-only in v1.** `publish` / `repromote` (charge the
> card on file) are server-gated today; companies post paid jobs via the
> dashboard's Stripe Checkout flow.

### Applications

```bash
dj applications <jobID>                         # default list (hides the filtered pile, like the UI)
dj applications <jobID> --status good-fit,interested   # CSV of statuses
dj applications <jobID> --only filtered                # just the auto-filtered pile ("Not Matching")
dj applications <jobID> --include filtered             # default list PLUS filtered
dj applications <jobID> --sort applied_desc            # status (default) | applied_desc | applied_asc | salary_desc | salary_asc
dj applications <jobID> --location us,gb --text alice  # filters
#   Valid statuses: not-reviewed, good-fit, interested, declined, filtered

dj application <applicationID> --job-id <jobID>        # one application + answers

dj update-application <appID> --job-id <jid> --status good-fit --notes-text "Strong Go background"
dj note <appID> --job-id <jid> --notes-text "Followed up by email"   # notes-only convenience
dj export-applications <jobID>                          # trigger CSV export to email
```

> There is **no 1-5 rating** in DJ — only the 5 dashboard statuses above plus
> the candidate-notes pair (`--notes-text` / `--notes-html`, which overwrite).

### Candidates

Only candidates who applied to one of your jobs are visible (403 otherwise).

```bash
dj candidate <uid>                              # candidate profile
```

### Analytics

```bash
dj analytics-jobs [--from YYYY-MM-DD --to YYYY-MM-DD]   # per-job metrics
dj analytics-funnel [--from --to]                       # views → applies → reviewed → hired
```

### Billing & limits

```bash
dj billing                                      # card on file, plan tier, recent API charges
dj limits                                       # effective rate limits + current usage
```

## MCP server

Tools are named to match the verb-grouped hosted-server names (`get_company`,
`list_jobs`, `update_application`, …), so a tool registered from this local
stdio server looks the same to an agent as one from the hosted
endpoint. CLI and library users don't need the `mcp` package.

```bash
pip install 'dynamitejobs[mcp]' && dj --mcp     # installed
python3 py/dj.py --mcp                            # from a clone
```

### Auto-updating config (no clone; pulls latest on every launch)

**Claude Code:**

```bash
claude mcp add dj --env DJ_API_KEY=dj_<companyID>_<random> \
  -- uvx --refresh --from 'dynamitejobs[mcp]' dj --mcp
```

**Claude Desktop / Cursor** (`mcpServers` block):

```json
{
  "mcpServers": {
    "dj": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--refresh", "--from", "dynamitejobs[mcp]", "dj", "--mcp"],
      "env": { "DJ_API_KEY": "dj_<companyID>_<random>" }
    }
  }
}
```

### Static path config (from a clone)

```json
{
  "mcpServers": {
    "dj": {
      "command": "python3",
      "args": ["/absolute/path/to/dj/py/dj.py", "--mcp"],
      "env": { "DJ_API_KEY": "dj_<companyID>_<random>" }
    }
  }
}
```

**ChatGPT / other MCP apps:** point them at the stdio launch above
(`uvx --from 'dynamitejobs[mcp]' dj --mcp`) with `DJ_API_KEY` in the env. When
the hosted Streamable HTTP endpoint ships, `.well-known/mcp.json` will advertise
it — prefer that for chat apps that only speak remote MCP.

## Library

```python
from dynamitejobs import DJ          # installed from PyPI
# From a clone:  import sys; sys.path.insert(0, "py"); from dj import DJ

dj = DJ()                             # reads DJ_API_KEY env or ~/.env.dj

# Reads
dj.company()
dj.jobs(status="published")
dj.applications("<jobID>", status="good-fit,interested", sort="applied_desc")
dj.analytics_funnel(from_="2026-01-01", to="2026-03-31")

# Writes
dj.update_company(description="We hire remote-first.")
dj.create_job(title="Senior Go Engineer", description="...")
dj.update_application("<appID>", job_id="<jobID>", status="good-fit",
                      candidate_notes_text="Strong Go background")
```

## Rate limits

| Tier         | Per minute | Per day |
|--------------|------------|---------|
| trial        | 5          | 100     |
| standard     | 30         | 1,500   |
| business-pro | 120        | 10,000  |
| partner      | 300        | 30,000  |

Every response carries `X-RateLimit-*` headers; `dj limits` shows current usage.

## Errors

Every error has `error` (machine-readable slug) and `message` (human). Common
slugs:

- `missing_authorization` / `key_not_found` / `key_disabled` / `company_disabled`
- `rate_limit_per_minute` / `rate_limit_per_day` (with `Retry-After` header)
- `no_stripe_customer` — a billing-gated write failed: no card on file
- `not_your_job` — tried to act on a job that isn't your company's
- `field_locked` — tried to edit a field that's read-only once a job is published
