# DJ Official — AI Tool Guide

This repo ships **`dynamitejobs`** — a self-contained, single-file Python client for the public **DJ Company API** (`https://api.dynamitejobs.com`). It works the same from Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, and any other Agent Skills- or MCP-compatible tool.

## At a glance

- **One file**: `py/dj.py`
- **Three modes**: CLI, Python import, MCP server (`--mcp` flag)
- **Stdlib only** for CLI/import. The `mcp` package is **lazy-imported** — only required for `--mcp` mode
- **Full coverage** — every public Company API endpoint is wrapped (run `help` for the live list)
- **Pre-configured `.mcp.json`** at the repo root — Claude Code auto-loads the server when you `cd` in
- **Zero internal-only knowhow** — public-grade design with no telemetry, no usage tracking, no error capture, no extension hooks

## What this is

`py/dj.py` contains:

- A small HTTP client (urllib-based, stdlib only) — `DJ` class with one method per endpoint
- A CLI dispatcher with subcommands for every verb
- An optional MCP server mode (`--mcp`) that exposes the read + safe write surface as MCP tools

The full reference for the underlying API is at https://dynamitejobs.com/developers/.

## First-time setup

```bash
pip install dynamitejobs
python3 -m dynamitejobs setup --api-key dj_<companyID>_<random>
python3 -m dynamitejobs self-test
```

Get your API key from the DJ dashboard: **Settings → API Access → Create new key** (owner/admin role required).

## Two-skill pattern

This is the **public** client. There's also an internal **Hive skill** at `~/Workbench/dc/dc-team/.claude/skills/dj-company/` that wraps the same API for team use during dj-platform development.

When you change the API surface (server side), update BOTH the public client AND the internal skill in the same commit. Otherwise customers hit "command not found" in `dynamitejobs` OR the team hits it in `dj-company` — both look like our bug.

| | Public (this repo) | Internal Hive skill |
|---|---|---|
| Audience | DJ customers | The team |
| Versioning | Pinned semver, CHANGELOG, GitHub Release, PyPI tag | Always latest |
| Env var | `DJ_API_KEY` | `DJ_COMPANY_SKILL_KEY` |

## Releasing

The full release flow lives in the **server-side SOP** at
[`plans/plans/dj-web/docs/dj-company-api-release-sop.md`](https://github.com/dynamite-ventures/dc-team/blob/main/plans/team/Simon/plans/dj-web/docs/dj-company-api-release-sop.md)
in the Hive (dc-team repo). The short version for this repo:

1. Server release shipped first — `dj.CompanyAPIVersion` is now `X.Y.Z` on `api.dynamitejobs.com`.
2. Bump `version` in `manifest.json`, `pyproject.toml`, and `py/dj.py` (`VERSION` constant) — **all three must match** the server.
3. Add a `## [X.Y.Z] – YYYY-MM-DD` section to `CHANGELOG.md` (Keep-a-Changelog format; the GitHub Release notes are extracted from this section by the workflow).
4. Commit and push to `main` — CI runs `build` + `smoke-install` across ubuntu/macos/windows × Python 3.10/3.12 on every push.
5. Tag: `git tag vX.Y.Z && git push origin vX.Y.Z` — triggers `.github/workflows/publish.yml`:
   - re-runs build + smoke-install,
   - publishes wheel + sdist to PyPI via **OIDC trusted publishing** (no API tokens in the repo — configured at https://pypi.org/manage/account/publishing/),
   - auto-creates a GitHub Release with notes pulled from the matching `## [X.Y.Z]` CHANGELOG section.
6. Verify: `https://pypi.org/project/dynamitejobs/` shows the new version; `pip install -U dynamitejobs && python -c "import dynamitejobs; print(dynamitejobs.VERSION)"` matches.

Trusted publisher configuration on PyPI:

| Field | Value |
|---|---|
| PyPI Project Name | `dynamitejobs` |
| Owner | `dynamitejobs` |
| Repository name | `dj` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |
