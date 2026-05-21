# Changelog

All notable changes to the **`dj` client repo** (PyPI: `dynamitejobs`) are
listed here. The version numbers track `VERSION` in [`py/dj.py`](py/dj.py),
which is deliberately aligned with the DJ Company API server version it
was last verified against. Patch bumps from the server are silent; minor
or major bumps surface a one-shot stderr warning when this client falls
behind.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/) for
the public Python API surface (`dynamitejobs.DJ`, `dynamitejobs.DJError`,
`dynamitejobs.VERSION`, `dynamitejobs.main`).

---

## [1.0.3] – 2026-05-21

### Changed

- PyPI Development Status classifier flipped from `4 - Beta` to `5 - Production/Stable` so the PyPI badge matches `dynamitecircle`. The client has been stable since 1.0.0 — the Beta declaration was a leftover default from initial scaffolding.

No code or API surface changes — client behavior identical to 1.0.2.

## [1.0.2] – 2026-05-20

### Changed

- PyPI metadata polish — rewrote the short `description` and `README.md` to lead with what DJ actually is (the remote-first job board for companies that hire from anywhere) before diving into the four invocation modes. Mirrors the structure of the `dynamitecircle` PyPI page.
- Added an "About Dynamite Jobs" section to the README with marketing copy and UTM-tagged backlinks to dynamitejobs.com, post-a-job, remote-jobs, job-alerts, and the sister recruiting agency.
- Added sidebar links in `[project.urls]` — `Dynamite Jobs`, `Browse Remote Jobs`, `Remote First Recruiting` — to surface CTAs from the PyPI page (alongside the existing `Post a Job`).
- Expanded `keywords` to include `remote-jobs`, `remote-work`, `remote-hiring`, `remote-first`, `dynamite-jobs`, `agent-skills` for better PyPI search discoverability.

No code or API surface changes — client behavior identical to 1.0.1.

## [1.0.1] – 2026-05-20

### Changed

- PyPI package metadata polish — fixed `Repository` / `Homepage` URLs to point at `github.com/dynamitejobs/dj` (was `dynamite-jobs/dj-official`, which doesn't exist) so PyPI's auto-verification flags them as trusted.
- Added `Post a Job` link to `[project.urls]` (mirrors DC's `Apply to DC` pattern) so the PyPI sidebar surfaces the product CTA. UTM-tagged for attribution.
- Added explicit `Changelog` and `Issues` URLs.

No code or API surface changes — client behavior identical to 1.0.0.

## [1.0.0] – 2026-05-20

Initial public release of the Dynamite Jobs Company API client.

### Added

- Full Company API surface — company (read/patch), jobs (list/read/create/patch/delete/trial/publish/repromote), applications (list/read/patch/notes/export), candidates (read scoped to your jobs), analytics (jobs / funnel), billing status, limits.
- Four invocation modes from a single file:
  - **Agent Skill** — auto-discovered via `SKILL.md`, used by Claude / Codex / Cursor / Gemini CLI / GitHub Copilot.
  - **CLI** — `dj company`, `dj jobs list`, `dj applications get`, `dj help`, etc.
  - **Python library** — `from dynamitejobs import DJ; DJ().jobs.list()`.
  - **MCP server** — `dj --mcp` (optional extra: `pip install dynamitejobs[mcp]`).
- Zero runtime dependencies (stdlib only). MCP mode pulls in `mcp` only when requested.
- `--format=json` (default) and `--format=raw`.
- Server version-warning on `X-API-Version` mismatch — one-shot, stderr, never blocks.
- OIDC trusted publishing via GitHub Actions — no PyPI API tokens in the repo.

### Notes

- `publish_job` and `repromote_job` are intentionally commented out in v1; they are gated server-side until billing-from-API is enabled (see `server/company_api/routes/jobs.go` `billingEndpointsEnabled` in the main DJ repo).
- API host: `https://api.dynamitejobs.com`. Developer docs: `https://dynamitejobs.com/developers`.
