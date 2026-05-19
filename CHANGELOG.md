# Changelog

## 1.0.0 — 2026-05-17

Initial public release.

- Full Company API surface: company, jobs (CRUD + trial + publish + repromote), applications (list + patch + notes + export), candidates, analytics (jobs / funnel / sources), billing status, limits.
- Four invocation modes: Agent Skill, CLI, Python library, MCP server.
- Zero runtime dependencies (stdlib only). MCP mode is an optional extra: `pip install dynamitejobs[mcp]`.
- `--format=json` (default) and `--format=raw`.
- Server version-warning on `X-API-Version` mismatch.
