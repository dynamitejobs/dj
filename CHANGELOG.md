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

## [1.2.5] – 2026-06-17

Aligned with DJ Company API server `1.2.5`, a fix-forward release for hosted MCP auth and connector discovery.

### Fixed

- Hosted MCP connector setup now aligns with the server's OAuth/resource challenge and unauthenticated discovery behavior. No Python API method or response-shape changes.

## [1.2.2] – 2026-06-17

Aligned with DJ Company API server `1.2.2`, which adds a hosted MCP server and OAuth.

### Added

- Hosted remote MCP is now live — `server.json` advertises the `streamable-http` endpoint at `https://api.dynamitejobs.com/mcp` (use it directly, no install). The bundled stdio server (`dj --mcp`) remains for local/offline use.
- MCP tool annotations (`readOnlyHint`/`destructiveHint`) + structured output on all 17 tools.
- `workflows` command — fetches the server's machine-readable recipe list.
- `tests/` version-sync + annotation-drift guards; `.mcpbignore` for the bundle.

### Changed

- `SKILL.md` expanded (hosted-vs-local guidance, OAuth, discovery, pagination, verb-grouped commands, rate-limit tiers).
- `manifest.json` to MCP-bundle 0.3 (`user_config` prompt for `DJ_API_KEY`, platform/runtime compatibility).
- `pyproject.toml` reads the package version dynamically from `py/dj.py`.

### Fixed

- `candidate` called the wrong path (`/candidates/{uid}` → `/candidate/{uid}`).

## [1.1.0] – 2026-06-13

### Changed

- Version bump tracking server [1.1.0], a large security-hardening + correctness release on the company-api. **No public Python API changes** (same methods, same call signatures), but the server now returns **curated field allowlists** on all read endpoints — `GET /company`, `/jobs`, `/jobs/{id}`, `/jobs/{id}/applications`, `/applications/{id}`, `/billing/status` — so responses no longer include internal/billing/audit fields or request metadata; a derived `featured` boolean replaces the internal flags object on jobs. Reads/writes you already make keep working; if you depended on an undocumented internal field it will now be absent.

No client code changes — bump keeps the client in lockstep with the server `X-API-Version` so the "client behind server" warning stays quiet.

## [1.0.9] – 2026-06-02

### Changed

- Version bump tracking server [1.0.9], which wires up two response fields the 1.0.8 OpenAPI schema advertised but never actually populated: `candidateID` on every row of `GET /jobs/{jobID}/applications` (was `null`, now the candidate UID — same value as `application.id`, surfaced explicitly so the docs' "Triage today's applicants → fetch /candidate/{candidateID}" workflow recipe actually works), and `applicationsCount` on `GET /jobs/{jobID}` + every row of `GET /jobs` (was `null`, now read from `jobsMeta/{jid}.analytics.applications.total` — same number the dashboard shows).

No public Python API changes — this is a server-side data-wiring release that brings the live response shape into line with what 1.0.8's docs promised.

## [1.0.8] – 2026-06-01

### Changed

- Version bump tracking server [1.0.8], which adds a richer OpenAPI surface (typed parameter enums, JSON schemas with `properties`/`required[]`/`enum`/`default`, named multi-example maps on requests and responses, the `x-tier-required` vendor extension, rate-limit notes appended to descriptions) and a long-form Markdown `info.description` with 8 end-to-end workflow recipes plus discoverability hints for LLM agents. The server changes are purely additive — request/response shapes are unchanged, so this client release is a no-op behavioural bump that keeps the version-mismatch warning silent.

The `--mcp` schema and the CLI help still match what 1.0.6 produced. Agents reading `/openapi.json` (which the dashboard's "Developer docs" link surfaces) will now see typed enums for `status` filters, named examples for "Triage today's unreviewed applicants" / "Mark applicant as interested after interview", and the canonical `statusOrder` field on application rows so they don't hardcode an ATS-status order in their client.

No public Python API changes.

## [1.0.6] – 2026-05-31

### Fixed

- **Removed the non-existent `rating` field from `update_application`.** The DJ dashboard's ATS only tracks status (`not-reviewed` / `good-fit` / `interested` / `declined` / `filtered`) and candidate notes — there is no 1-5 rating. Server 1.0.6 already rejects `rating` with `field_not_editable`, so calls from this client that passed `rating=…` were failing. Removed from the library method, the CLI's `update-application --rating` arg, the MCP `update_application` tool schema and dispatcher, and the manifest. Watching agents (Claude, Codex, Cursor, etc.) hitting this build will see the same surface the dashboard does.
- The MCP `update_application` tool now also surfaces `candidate_notes_text` / `candidate_notes_html` (was previously a single non-existent `note` field), and the `status` enum is explicit so completions show the 5 valid values.

Tracks server [1.0.7] which stopped persisting raw bearer tokens and fixed the stale `X-API-Version` response header (the version-mismatch warning in this client will now fire correctly when the server runs ahead).

## [1.0.5] – 2026-05-27

### Changed

- Version bump only to verify the DJ Company API release flow keeps the server, docs, and PyPI client on the same public semver. No public Python API changes.

## [1.0.4] – 2026-05-21

### Changed

- **Version-mismatch warning rewritten to match DC's `_VersionTracker` pattern.** When the server's `X-API-Version` reports a newer major or minor than this client, stderr now emits a multi-line, agent-friendly warning that names both `pip install --upgrade dynamitejobs` and `pipx upgrade dynamitejobs` (pipx is how most agents install standalone CLI tools), links to the PyPI release page, and explicitly tells watching agents to run the upgrade before continuing. Patch-only diffs stay silent (semver patch = bug fix).
- `_version_warned` flag moved to **class level** so one process only emits the warning once, even across multiple `DJ()` instances (CLI + library + MCP all share). Mirrors `_VersionTracker._warned` in the DC client.
- Header read is now case-insensitive (`X-API-Version` OR `x-api-version`).

No public Python API changes — `dynamitejobs.DJ`, `DJError`, `VERSION`, `main` all identical.

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
