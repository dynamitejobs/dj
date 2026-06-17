#!/usr/bin/env python3
"""
dj — Dynamite Jobs Company API client.

Single-file, zero runtime dependencies (stdlib only).

Four modes:
  1. Agent Skill — auto-discovered via SKILL.md
  2. CLI         — `python3 dj.py jobs list --status=published`
  3. Library     — `from dj import DJ; DJ().jobs()`
  4. MCP server  — `python3 dj.py --mcp`  (requires optional `mcp` extra)

Setup:
  python3 dj.py setup --api-key dj_<companyID>_<random>
  python3 dj.py self-test
  python3 dj.py company
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

# ──────────────────────────────────────────────────────────────────────────────
# Version + defaults

VERSION = "1.2.5"
DEFAULT_BASE_URL = "https://api.dynamitejobs.com"
ENV_FILE = Path.home() / ".env.dj"
ENV_KEY = "DJ_API_KEY"
ENV_BASE_URL = "DJ_API_BASE_URL"

# ──────────────────────────────────────────────────────────────────────────────
# MCP tool annotations
#
# Every MCP tool carries readOnlyHint / destructiveHint / openWorldHint so
# clients can auto-approve reads and prompt on writes. The read/write split is
# derived from the HTTP verb each command issues (GET = read; POST/PATCH/DELETE
# = write) and guarded by tests/test_annotations.py, which fails on drift.
#
# Command names here use the kebab CLI form; _tool_annotations() accepts either
# kebab (`update-job`) or snake (`update_job`, the MCP tool form).
#
# `setup` is the one local-only write (persists .env.dj, no network) — kept out
# of the network-derived set and added back by the test. `workflows` and `setup`
# are local commands → openWorldHint False.
_WRITE_COMMANDS = frozenset({
    "setup",
    "update-company",
    "post-job", "update-job", "delete-job", "trial-post",
    "update-application", "note", "export-applications",
})
# Irreversible data removal — sets destructiveHint. `delete-job` unpublishes /
# removes a job. (No other DJ write destroys data: status/notes are editable,
# trial-post / post-job create, export is a side-effect-free email trigger.)
_DESTRUCTIVE_COMMANDS = frozenset({"delete-job"})
# Purely local — no outbound network, so openWorldHint is False.
_LOCAL_COMMANDS = frozenset({"setup", "workflows"})


def _tool_annotations(command_name: str) -> dict:
    """MCP annotation hints for a command (accepts snake or kebab name).

    Returns a plain dict so it's unit-testable without the `mcp` package;
    run_mcp() wraps it in mcp.types.ToolAnnotations.
    """
    kebab = command_name.replace("_", "-")
    is_write = kebab in _WRITE_COMMANDS
    return {
        "readOnlyHint":    not is_write,
        "destructiveHint": kebab in _DESTRUCTIVE_COMMANDS,
        "openWorldHint":   kebab not in _LOCAL_COMMANDS,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Core client


class DJError(Exception):
    """Raised on any non-2xx response. .status, .body, .url available."""

    def __init__(self, status: int, body: Any, url: str, message: str = ""):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(message or f"HTTP {status} on {url}: {body}")


class DJ:
    """Thin wrapper around the Company API HTTP surface."""

    # Class-level so a single warning fires across all DJ instances in
    # one process (CLI, MCP server, library use). Mirrors DC's
    # _VersionTracker._warned pattern.
    _version_warned: bool = False

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get(ENV_KEY) or _load_env_value(ENV_KEY)
        self.base_url = (base_url or os.environ.get(ENV_BASE_URL) or _load_env_value(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError(
                f"No API key. Set {ENV_KEY} env var, pass api_key=..., or run: dj setup --api-key dj_<...>"
            )

    # ── HTTP plumbing ──

    def _request(self, method: str, path: str, *, params: dict | None = None, body: Any = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            url += "?" + parse.urlencode({k: v for k, v in params.items() if v is not None})
        data = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"dj-official/{VERSION} python",
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(url, data=data, method=method, headers=headers)
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                self._check_version(resp)
                if not raw:
                    return None
                ct = resp.headers.get("Content-Type", "")
                if ct.startswith("application/json"):
                    return json.loads(raw)
                return raw.decode("utf-8", errors="replace")
        except error.HTTPError as e:
            raw = e.read() if hasattr(e, "read") else b""
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = raw.decode("utf-8", errors="replace")
            raise DJError(e.code, parsed, url) from None

    def _check_version(self, resp) -> None:
        """Compare server X-API-Version to this client's VERSION; warn once.

        Rules (mirrors DC's _VersionTracker):
        - Server major OR minor newer → warn loud, once per process.
        - Patch difference → silent (semver patch = bug fix only).
        - Server older than client → silent (newer client is fine).

        Warning text is structured so a watching agent (Claude / Codex /
        Cursor / Gemini CLI / GitHub Copilot) can act on it without
        guessing — it names the upgrade commands for both `pip` and
        `pipx` (the latter is how most agents install standalone CLI
        tools). The PyPI page is included so the agent can verify the
        latest version before running the upgrade.
        """
        if DJ._version_warned:
            return
        srv = resp.headers.get("X-API-Version") or resp.headers.get("x-api-version") or ""
        if not srv or srv == VERSION:
            return
        srv_t = _semver(srv)
        cli_t = _semver(VERSION)
        if not srv_t or not cli_t:
            return
        if srv_t[:2] <= cli_t[:2]:
            return  # patch-only diff or client ahead — stay silent
        DJ._version_warned = True
        sys.stderr.write(
            f"\n⚠  DJ Company API has new features available "
            f"(server {srv}, this client built for {VERSION}).\n"
            f"   Update the client:  pip install --upgrade dynamitejobs\n"
            f"   (or for pipx installs: pipx upgrade dynamitejobs)\n"
            f"   Release notes:      https://pypi.org/project/dynamitejobs/\n"
            f"\n"
            f"   Agents: please run the upgrade above before continuing — "
            f"newer server endpoints / params may not be wrapped in this build.\n\n"
        )

    # ── Read endpoints ──

    def company(self) -> dict: return self._request("GET", "/company")
    def limits(self) -> dict: return self._request("GET", "/limits")
    def billing_status(self) -> dict: return self._request("GET", "/billing/status")

    def jobs(self, *, status: str | None = None, cursor: str | None = None, limit: int = 25) -> dict:
        return self._request("GET", "/jobs", params={"status": status, "cursor": cursor, "limit": limit})

    def job(self, job_id: str) -> dict:
        return self._request("GET", f"/jobs/{parse.quote(job_id)}")

    def applications(
        self,
        job_id: str,
        *,
        status: str | None = None,
        only: str | None = None,
        include: str | None = None,
        sort: str | None = None,
        location: str | None = None,
        salary_range: str | None = None,
        text: str | None = None,
        cursor: str | None = None,
        limit: int = 25,
    ) -> dict:
        """List applications for a job. Mirrors the dashboard's filters + sorts.

        Status filter (pick one):
          - status="good-fit,interested"   exactly those (CSV)
          - only="filtered"                 just the filtered pile
          - include="filtered"              default list PLUS filtered
          - (none)                          default: hide `filtered` (matches UI)

        Sort: status (default) | applied_desc | applied_asc | salary_desc | salary_asc
        """
        return self._request("GET", f"/jobs/{parse.quote(job_id)}/applications", params={
            "status": status, "only": only, "include": include, "sort": sort,
            "location": location, "salary_range": salary_range, "text": text,
            "cursor": cursor, "limit": limit,
        })

    def application(self, application_id: str, *, job_id: str) -> dict:
        return self._request("GET", f"/applications/{parse.quote(application_id)}", params={"jobId": job_id})

    def candidate(self, uid: str) -> dict:
        return self._request("GET", f"/candidate/{parse.quote(uid)}")

    def workflows(self) -> Any:
        """Machine-readable list of common Company API recipes — each with a
        goal, an ordered list of {method, path} steps, and notes. A good first
        call for an agent new to the API. Served on the public unauthenticated
        discovery surface (alongside `/` and `/openapi.json`)."""
        return self._request("GET", "/workflows")

    def analytics_jobs(self, *, from_: str | None = None, to: str | None = None) -> dict:
        return self._request("GET", "/analytics/jobs", params={"from": from_, "to": to})

    def analytics_funnel(self, *, from_: str | None = None, to: str | None = None) -> dict:
        return self._request("GET", "/analytics/funnel", params={"from": from_, "to": to})

    def analytics_sources(self, *, from_: str | None = None, to: str | None = None) -> dict:
        return self._request("GET", "/analytics/sources", params={"from": from_, "to": to})

    # ── Write endpoints ──

    def update_company(self, **fields) -> dict:
        return self._request("PATCH", "/company", body=fields)

    def create_job(self, **fields) -> dict:
        return self._request("POST", "/jobs", body=fields)

    def update_job(self, job_id: str, **fields) -> dict:
        return self._request("PATCH", f"/jobs/{parse.quote(job_id)}", body=fields)

    def delete_job(self, job_id: str) -> dict:
        return self._request("DELETE", f"/jobs/{parse.quote(job_id)}")

    def trial_post(self, **fields) -> dict:
        return self._request("POST", "/jobs/trial", body=fields)

    # ── Disabled in v1 ─────────────────────────────────────────────────
    # publish_job + repromote_job are gated on the server by a code constant
    # (billingEndpointsEnabled in routes/jobs.go) — calling them today returns
    # 404. Companies post paid jobs via the dashboard's Stripe Checkout flow.
    # Uncomment here ALONG WITH flipping the server constant when the
    # programmatic-charge-on-file UX has had its product review.
    #
    # def publish_job(self, job_id: str) -> dict:
    #     return self._request("POST", f"/jobs/{parse.quote(job_id)}/publish", body={})
    #
    # def repromote_job(self, job_id: str, *, days: int = 30) -> dict:
    #     return self._request("POST", f"/jobs/{parse.quote(job_id)}/repromote", params={"days": days}, body={})

    def update_application(
        self,
        application_id: str,
        *,
        job_id: str,
        status: str | None = None,
        candidate_notes_text: str | None = None,
        candidate_notes_html: str | None = None,
    ) -> dict:
        """Update an application's status or notes (ATS).

        There is no 1-5 candidate rating in DJ — only the 5 dashboard statuses
        (not-reviewed / good-fit / interested / declined / filtered) and the
        candidate-notes pair below.

        Notes are a single field pair (matches the dashboard's editor):
          candidate_notes_text — plain-text version
          candidate_notes_html — HTML version (overwrites; not appended)
        Pass both together when you have rich content; plain-text alone is fine.
        """
        body: dict = {}
        if status is not None: body["status"] = status
        if candidate_notes_text is not None: body["candidateNotesText"] = candidate_notes_text
        if candidate_notes_html is not None: body["candidateNotesHTML"] = candidate_notes_html
        return self._request("PATCH", f"/applications/{parse.quote(application_id)}", params={"jobId": job_id}, body=body)

    def note(
        self,
        application_id: str,
        *,
        job_id: str,
        candidate_notes_text: str | None = None,
        candidate_notes_html: str | None = None,
    ) -> dict:
        """Convenience wrapper over update_application for notes only.

        Notes overwrite (they are not appended) — pass the full desired note
        text. Mirrors the dashboard's candidate-notes editor.
        """
        return self.update_application(
            application_id,
            job_id=job_id,
            candidate_notes_text=candidate_notes_text,
            candidate_notes_html=candidate_notes_html,
        )

    def export_applications(self, job_id: str) -> dict:
        return self._request("POST", f"/jobs/{parse.quote(job_id)}/applications/export", body={})


# ──────────────────────────────────────────────────────────────────────────────
# .env.dj helpers


def _load_env_value(key: str) -> str | None:
    if not ENV_FILE.exists():
        return None
    try:
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def _save_env_value(key: str, value: str) -> None:
    lines: list[str] = []
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.strip().startswith(f"{key}="):
                continue
            lines.append(line)
    lines.append(f'{key}="{value}"')
    ENV_FILE.write_text("\n".join(lines) + "\n")
    try:
        ENV_FILE.chmod(0o600)
    except Exception:
        pass


def _semver(s: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(x) for x in s.split(".")[:3])
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# CLI


def cmd_setup(args: argparse.Namespace) -> int:
    if not args.api_key:
        print("Usage: dj setup --api-key dj_<companyID>_<random>", file=sys.stderr)
        return 2
    if not args.api_key.startswith("dj_"):
        print("ERROR: API key must start with 'dj_'", file=sys.stderr)
        return 2
    _save_env_value(ENV_KEY, args.api_key)
    if args.base_url:
        _save_env_value(ENV_BASE_URL, args.base_url)
    print(f"Saved key to {ENV_FILE}. Run `dj self-test` to verify.")
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    try:
        dj = DJ()
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"Base URL : {dj.base_url}")
    print(f"Key      : {dj.api_key[:8]}…{dj.api_key[-4:]}")
    try:
        c = dj.company()
        company = c.get("company", {}) if isinstance(c, dict) else {}
        name = company.get("name") or company.get("companyName") or "(unnamed)"
        print(f"Company  : {name}")
        l = dj.limits()
        print(f"Tier     : {l.get('tier')} ({l.get('per_minute_limit')} req/min, {l.get('per_day_limit')} req/day)")
        print("OK")
        return 0
    except DJError as e:
        print(f"FAIL: HTTP {e.status} {e.body}", file=sys.stderr)
        return 1


def _print(obj: Any, fmt: str = "json") -> None:
    if fmt == "json":
        print(json.dumps(obj, indent=2, default=str))
        return
    if fmt == "raw":
        print(obj)
        return
    print(json.dumps(obj, default=str))


def cmd_workflows(args: argparse.Namespace) -> int:
    """Fetch the public /workflows discovery payload.

    No API key required — /workflows is on the unauthenticated discovery
    surface. We still construct a DJ() (it only needs a base URL) but tolerate
    a missing key so an unfamiliar agent can discover recipes before setup.
    """
    base = os.environ.get(ENV_BASE_URL) or _load_env_value(ENV_BASE_URL) or DEFAULT_BASE_URL
    try:
        dj = DJ(api_key="discovery", base_url=base)  # key unused by /workflows
        out = dj.workflows()
    except DJError as e:
        if e.status == 404:
            print(
                "FAIL: this server does not expose /workflows yet "
                "(404). Use `dj help` and https://api.dynamitejobs.com/openapi.json instead.",
                file=sys.stderr,
            )
            return 1
        print(f"HTTP {e.status}: {json.dumps(e.body, default=str)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    _print(out, fmt=args.format)
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    """Generic CLI dispatcher — maps verbs to DJ method calls."""
    try:
        dj = DJ()
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    verb = args.verb
    fmt = args.format
    try:
        if verb == "company":      out = dj.company()
        elif verb == "limits":     out = dj.limits()
        elif verb == "billing":    out = dj.billing_status()
        elif verb == "jobs":       out = dj.jobs(status=args.status, cursor=args.cursor, limit=args.limit)
        elif verb == "job":        out = dj.job(args.id)
        elif verb == "applications":
            out = dj.applications(
                args.job_id,
                status=args.status, only=args.only, include=args.include, sort=args.sort,
                location=args.location, salary_range=args.salary_range, text=args.text,
                cursor=args.cursor, limit=args.limit,
            )
        elif verb == "application": out = dj.application(args.id, job_id=args.job_id)
        elif verb == "candidate":  out = dj.candidate(args.uid)
        elif verb == "analytics-jobs":    out = dj.analytics_jobs(from_=args.from_, to=args.to)
        elif verb == "analytics-funnel":  out = dj.analytics_funnel(from_=args.from_, to=args.to)
        elif verb == "analytics-sources": out = dj.analytics_sources(from_=args.from_, to=args.to)
        elif verb == "update-company":
            fields = json.loads(args.json_body or "{}")
            out = dj.update_company(**fields)
        elif verb == "post-job":
            fields = json.loads(args.json_body or "{}")
            out = dj.create_job(**fields)
        elif verb == "update-job":
            fields = json.loads(args.json_body or "{}")
            out = dj.update_job(args.id, **fields)
        elif verb == "delete-job": out = dj.delete_job(args.id)
        elif verb == "trial-post":
            fields = json.loads(args.json_body or "{}")
            out = dj.trial_post(**fields)
        # Disabled in v1 (paired with the commented-out methods above):
        # elif verb == "publish-job": out = dj.publish_job(args.id)
        # elif verb == "repromote-job": out = dj.repromote_job(args.id, days=args.days)
        elif verb == "update-application":
            out = dj.update_application(
                args.id, job_id=args.job_id,
                status=args.status,
                candidate_notes_text=args.notes_text,
                candidate_notes_html=args.notes_html,
            )
        elif verb == "note":
            out = dj.note(
                args.id, job_id=args.job_id,
                candidate_notes_text=args.notes_text,
                candidate_notes_html=args.notes_html,
            )
        elif verb == "export-applications": out = dj.export_applications(args.job_id)
        else:
            print(f"Unknown verb: {verb}", file=sys.stderr); return 2
        _print(out, fmt=fmt)
        return 0
    except DJError as e:
        print(f"HTTP {e.status}: {json.dumps(e.body, default=str)}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dj", description="Dynamite Jobs Company API client")
    p.add_argument("--mcp", action="store_true", help="Run as MCP server (stdio)")
    p.add_argument("--format", choices=["json", "raw"], default="json", help="Output format")
    sub = p.add_subparsers(dest="verb")

    setup = sub.add_parser("setup", help="Save API key to ~/.env.dj")
    setup.add_argument("--api-key", required=True)
    setup.add_argument("--base-url", default=None)

    sub.add_parser("self-test", help="Verify connection")
    sub.add_parser("workflows", help="Machine-readable API recipes (no key needed)")
    sub.add_parser("company", help="Read company profile")
    sub.add_parser("limits", help="Show effective rate limits + usage")
    sub.add_parser("billing", help="Card on file, plan tier, recent charges")

    jobs = sub.add_parser("jobs", help="List jobs")
    jobs.add_argument("--status")
    jobs.add_argument("--cursor")
    jobs.add_argument("--limit", type=int, default=25)

    job = sub.add_parser("job", help="Read one job"); job.add_argument("id")

    apps = sub.add_parser("applications", help="List applications for a job")
    apps.add_argument("job_id")
    apps.add_argument("--status", help="CSV: not-reviewed,good-fit,interested,declined,filtered")
    apps.add_argument("--only", help="Just one status (e.g. --only=filtered)")
    apps.add_argument("--include", help="Include the filtered pile (e.g. --include=filtered)")
    apps.add_argument("--sort", choices=["status", "applied_desc", "applied_asc", "salary_desc", "salary_asc"], help="Default: status")
    apps.add_argument("--location", help="CSV of location slugs")
    apps.add_argument("--salary-range", dest="salary_range", help="CSV of salary range flags")
    apps.add_argument("--text", help="Search applicant name")
    apps.add_argument("--cursor")
    apps.add_argument("--limit", type=int, default=25)

    app = sub.add_parser("application", help="Read one application")
    app.add_argument("id"); app.add_argument("--job-id", required=True, dest="job_id")

    cand = sub.add_parser("candidate", help="Read a candidate (must have applied)"); cand.add_argument("uid")

    for name in ("analytics-jobs", "analytics-funnel", "analytics-sources"):
        a = sub.add_parser(name)
        a.add_argument("--from", dest="from_")
        a.add_argument("--to")

    uc = sub.add_parser("update-company"); uc.add_argument("json_body", help="JSON object of fields to update")
    pj = sub.add_parser("post-job", help="Create an unpublished job"); pj.add_argument("json_body")
    uj = sub.add_parser("update-job"); uj.add_argument("id"); uj.add_argument("json_body")
    dj_ = sub.add_parser("delete-job"); dj_.add_argument("id")
    tp = sub.add_parser("trial-post"); tp.add_argument("json_body")
    # Disabled in v1 (server-gated):
    # pub = sub.add_parser("publish-job"); pub.add_argument("id")
    # rep = sub.add_parser("repromote-job"); rep.add_argument("id"); rep.add_argument("--days", type=int, default=30)

    ua = sub.add_parser("update-application")
    ua.add_argument("id"); ua.add_argument("--job-id", required=True, dest="job_id")
    ua.add_argument("--status")
    ua.add_argument("--notes-text", dest="notes_text", help="Plain-text candidate notes (overwrites)")
    ua.add_argument("--notes-html", dest="notes_html", help="HTML candidate notes (overwrites)")

    nt = sub.add_parser("note", help="Append/overwrite candidate notes on an application")
    nt.add_argument("id"); nt.add_argument("--job-id", required=True, dest="job_id")
    nt.add_argument("--notes-text", dest="notes_text", help="Plain-text candidate notes (overwrites)")
    nt.add_argument("--notes-html", dest="notes_html", help="HTML candidate notes (overwrites)")

    ex = sub.add_parser("export-applications"); ex.add_argument("job_id")

    return p


# ──────────────────────────────────────────────────────────────────────────────
# MCP server (stdio)
#
# MCP tool names mirror the verb-grouped names the hosted DJ Company API MCP
# exposes (get_company, update_company, list_jobs, …) so a tool registered from
# this local stdio server and one registered from the hosted endpoint look the
# same to an agent. Each entry carries:
#   command — the kebab CLI command name, used to derive read/write annotations
#             (see _tool_annotations / _WRITE_COMMANDS) — the single drift guard.
#   schema  — the MCP inputSchema.
#   handler — (DJ, args) -> result.
#
# Defined at module scope (not inside run_mcp) so tests/test_annotations.py can
# introspect the read/write split without importing the optional `mcp` package.

def _mcp_tool_specs() -> dict:
    """Return {mcp_tool_name: {"command", "description", "schema", "handler"}}.

    The 17 tools the hosted DJ Company API MCP exposes. publish/repromote are
    intentionally absent — they're server-gated in v1 (see the commented-out
    methods on DJ).
    """
    _date = {"from": {"type": "string", "description": "YYYY-MM-DD"},
             "to": {"type": "string", "description": "YYYY-MM-DD"}}
    _status_enum = ["not-reviewed", "good-fit", "interested", "declined", "filtered"]
    return {
        # ── Company ──
        "get_company": {
            "command": "company", "description": "Read your company profile (description, website, plan, team).",
            "schema": {"type": "object", "properties": {}},
            "handler": lambda dj, a: dj.company(),
        },
        "update_company": {
            "command": "update-company", "description": "Patch company profile fields. Pass a JSON object of fields.",
            "schema": {"type": "object", "properties": {"fields": {"type": "object", "description": "Fields to update, e.g. {\"description\": \"...\"}"}}, "required": ["fields"]},
            "handler": lambda dj, a: dj.update_company(**(a.get("fields") or {})),
        },
        # ── Jobs ──
        "list_jobs": {
            "command": "jobs", "description": "List your jobs (optional status filter; cursor-paginated).",
            "schema": {"type": "object", "properties": {"status": {"type": "string", "description": "unpublished|pending|published|expired|finished|fulfilled|deleted|rejected"}, "cursor": {"type": "string"}, "limit": {"type": "integer"}}},
            "handler": lambda dj, a: dj.jobs(status=a.get("status"), cursor=a.get("cursor"), limit=a.get("limit", 25)),
        },
        "get_job": {
            "command": "job", "description": "Read one job by ID.",
            "schema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
            "handler": lambda dj, a: dj.job(a["job_id"]),
        },
        "create_job": {
            "command": "post-job", "description": "Create an unpublished job. Pass a JSON object of fields.",
            "schema": {"type": "object", "properties": {"fields": {"type": "object", "description": "Job fields (title, description, ...)"}}, "required": ["fields"]},
            "handler": lambda dj, a: dj.create_job(**(a.get("fields") or {})),
        },
        "create_trial_job": {
            "command": "trial-post", "description": "Submit a trial post (1 per company, awaits admin approval).",
            "schema": {"type": "object", "properties": {"fields": {"type": "object", "description": "Job fields"}}, "required": ["fields"]},
            "handler": lambda dj, a: dj.trial_post(**(a.get("fields") or {})),
        },
        "update_job": {
            "command": "update-job", "description": "Edit an unpublished job / restricted published fields.",
            "schema": {"type": "object", "properties": {"job_id": {"type": "string"}, "fields": {"type": "object"}}, "required": ["job_id", "fields"]},
            "handler": lambda dj, a: dj.update_job(a["job_id"], **(a.get("fields") or {})),
        },
        "delete_job": {
            "command": "delete-job", "description": "Delete an unpublished job / unpublish a published one.",
            "schema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
            "handler": lambda dj, a: dj.delete_job(a["job_id"]),
        },
        # ── Applications ──
        "list_applications": {
            "command": "applications", "description": "List applications for a job. Mirrors the dashboard filters/sorts.",
            "schema": {"type": "object", "properties": {
                "job_id": {"type": "string"}, "status": {"type": "string", "description": "CSV of statuses"},
                "only": {"type": "string"}, "include": {"type": "string"},
                "sort": {"type": "string", "enum": ["status", "applied_desc", "applied_asc", "salary_desc", "salary_asc"]},
                "location": {"type": "string"}, "salary_range": {"type": "string"}, "text": {"type": "string"},
                "cursor": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["job_id"]},
            "handler": lambda dj, a: dj.applications(
                a["job_id"], status=a.get("status"), only=a.get("only"), include=a.get("include"),
                sort=a.get("sort"), location=a.get("location"), salary_range=a.get("salary_range"),
                text=a.get("text"), cursor=a.get("cursor"), limit=a.get("limit", 25)),
        },
        "get_application": {
            "command": "application", "description": "Read one application + its answers (requires job_id).",
            "schema": {"type": "object", "properties": {"application_id": {"type": "string"}, "job_id": {"type": "string"}}, "required": ["application_id", "job_id"]},
            "handler": lambda dj, a: dj.application(a["application_id"], job_id=a["job_id"]),
        },
        "update_application": {
            "command": "update-application", "description": "Update an application's status or notes (ATS). No 'rating' field — only the 5 dashboard statuses.",
            "schema": {"type": "object", "properties": {
                "application_id": {"type": "string"}, "job_id": {"type": "string"},
                "status": {"type": "string", "enum": _status_enum},
                "candidate_notes_text": {"type": "string"}, "candidate_notes_html": {"type": "string"}},
                "required": ["application_id", "job_id"]},
            "handler": lambda dj, a: dj.update_application(
                a["application_id"], job_id=a["job_id"], status=a.get("status"),
                candidate_notes_text=a.get("candidate_notes_text"),
                candidate_notes_html=a.get("candidate_notes_html")),
        },
        "export_applications": {
            "command": "export-applications", "description": "Trigger a CSV export of a job's applications to email.",
            "schema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
            "handler": lambda dj, a: dj.export_applications(a["job_id"]),
        },
        # ── Candidates ──
        "get_candidate": {
            "command": "candidate", "description": "Read a candidate profile (only if they applied to one of your jobs).",
            "schema": {"type": "object", "properties": {"uid": {"type": "string"}}, "required": ["uid"]},
            "handler": lambda dj, a: dj.candidate(a["uid"]),
        },
        # ── Analytics ──
        "analytics_jobs": {
            "command": "analytics-jobs", "description": "Per-job analytics (views, applies, …).",
            "schema": {"type": "object", "properties": dict(_date)},
            "handler": lambda dj, a: dj.analytics_jobs(from_=a.get("from"), to=a.get("to")),
        },
        "analytics_funnel": {
            "command": "analytics-funnel", "description": "Company-wide funnel: views → applies → reviewed → hired.",
            "schema": {"type": "object", "properties": dict(_date)},
            "handler": lambda dj, a: dj.analytics_funnel(from_=a.get("from"), to=a.get("to")),
        },
        # ── Billing / limits ──
        "billing_status": {
            "command": "billing", "description": "Card on file, plan tier, recent API charges.",
            "schema": {"type": "object", "properties": {}},
            "handler": lambda dj, a: dj.billing_status(),
        },
        "get_limits": {
            "command": "limits", "description": "Effective rate limits + current usage.",
            "schema": {"type": "object", "properties": {}},
            "handler": lambda dj, a: dj.limits(),
        },
    }


def run_mcp() -> int:
    """MCP stdio server. Exposes the 17 Company API tools with read/write
    annotations and structured output for object results."""
    try:
        from mcp.server import Server  # type: ignore
        from mcp.server.stdio import stdio_server  # type: ignore
        from mcp.types import Tool, TextContent, ToolAnnotations  # type: ignore
    except ImportError:
        print(
            "MCP mode requires the optional 'mcp' package: pip install 'dynamitejobs[mcp]'",
            file=sys.stderr,
        )
        return 1
    import asyncio

    server = Server("dj-company")
    specs = _mcp_tool_specs()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        for name, spec in specs.items():
            desc = spec["description"]
            if spec["command"] in _WRITE_COMMANDS:
                desc += "\n\n⚠️ Write operation: mutates your DJ company data."
            tools.append(Tool(
                name=name,
                description=desc,
                inputSchema=spec["schema"],
                annotations=ToolAnnotations(**_tool_annotations(spec["command"])),
            ))
        return tools

    @server.call_tool()
    async def call_tool(name: str, args: dict):
        spec = specs.get(name)
        if not spec:
            return [TextContent(type="text", text=json.dumps({"error": f"unknown tool {name}"}))]
        try:
            dj = DJ()
            result = spec["handler"](dj, dict(args or {}))
        except DJError as e:
            return [TextContent(type="text", text=json.dumps(
                {"error": "http_error", "status": e.status, "body": e.body}, default=str))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, default=str))]

        payload = json.dumps(result, indent=2, default=str) if isinstance(result, (dict, list)) \
            else (str(result) if result is not None else "")
        content = [TextContent(type="text", text=payload)]
        # Object results are also returned as structuredContent so
        # structure-aware clients can consume them without re-parsing the text.
        # (Lists/scalars stay text-only — the SDK's structured channel expects
        # an object.) Returning a 2-tuple is the SDK's combined-content contract.
        if isinstance(result, dict):
            return content, result
        return content

    async def _main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# Entry point


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.mcp:
        return run_mcp()
    if args.verb is None:
        parser.print_help()
        return 0
    if args.verb == "setup": return cmd_setup(args)
    if args.verb == "self-test": return cmd_self_test(args)
    if args.verb == "workflows": return cmd_workflows(args)
    return cmd_call(args)


if __name__ == "__main__":
    sys.exit(main())
