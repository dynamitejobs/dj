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

1. Bump `version` in `manifest.json`, `pyproject.toml`, and `py/dj.py` (`VERSION` constant) — all three must match.
2. Update `CHANGELOG.md` with a row at the top.
3. Tag: `git tag v1.x.y && git push origin v1.x.y`
4. GitHub Actions `.github/workflows/publish.yml` publishes to PyPI via OIDC trusted publishing (no API tokens stored).
