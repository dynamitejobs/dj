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

VERSION = "1.0.0"
DEFAULT_BASE_URL = "https://api.dynamitejobs.com"
ENV_FILE = Path.home() / ".env.dj"
ENV_KEY = "DJ_API_KEY"
ENV_BASE_URL = "DJ_API_BASE_URL"

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

    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get(ENV_KEY) or _load_env_value(ENV_KEY)
        self.base_url = (base_url or os.environ.get(ENV_BASE_URL) or _load_env_value(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError(
                f"No API key. Set {ENV_KEY} env var, pass api_key=..., or run: dj setup --api-key dj_<...>"
            )
        self._version_warned = False

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
        if self._version_warned:
            return
        srv = resp.headers.get("X-API-Version", "")
        if srv and srv != VERSION:
            srv_t = _semver(srv)
            cli_t = _semver(VERSION)
            # If server major/minor newer, warn loud. Patch difference: silent.
            if srv_t and cli_t and srv_t[:2] > cli_t[:2]:
                sys.stderr.write(f"[dj] Server is {srv} but client is {VERSION}. Consider: pip install --upgrade dynamitejobs\n")
                self._version_warned = True

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
        return self._request("GET", f"/candidates/{parse.quote(uid)}")

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

    def publish_job(self, job_id: str) -> dict:
        return self._request("POST", f"/jobs/{parse.quote(job_id)}/publish", body={})

    def repromote_job(self, job_id: str, *, days: int = 30) -> dict:
        return self._request("POST", f"/jobs/{parse.quote(job_id)}/repromote", params={"days": days}, body={})

    def update_application(self, application_id: str, *, job_id: str, status: str | None = None, rating: float | None = None, note: str | None = None) -> dict:
        body = {}
        if status is not None: body["status"] = status
        if rating is not None: body["rating"] = rating
        if note is not None: body["note"] = note
        return self._request("PATCH", f"/applications/{parse.quote(application_id)}", params={"jobId": job_id}, body=body)

    def add_application_note(self, application_id: str, *, job_id: str, note: str) -> dict:
        return self._request("POST", f"/applications/{parse.quote(application_id)}/notes", params={"jobId": job_id}, body={"note": note})

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
        elif verb == "publish-job": out = dj.publish_job(args.id)
        elif verb == "repromote-job": out = dj.repromote_job(args.id, days=args.days)
        elif verb == "update-application":
            out = dj.update_application(args.id, job_id=args.job_id, status=args.status, rating=args.rating, note=args.note)
        elif verb == "note":       out = dj.add_application_note(args.id, job_id=args.job_id, note=args.note)
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
    pj = sub.add_parser("post-job", help="Create a draft job"); pj.add_argument("json_body")
    uj = sub.add_parser("update-job"); uj.add_argument("id"); uj.add_argument("json_body")
    dj_ = sub.add_parser("delete-job"); dj_.add_argument("id")
    tp = sub.add_parser("trial-post"); tp.add_argument("json_body")
    pub = sub.add_parser("publish-job"); pub.add_argument("id")
    rep = sub.add_parser("repromote-job"); rep.add_argument("id"); rep.add_argument("--days", type=int, default=30)

    ua = sub.add_parser("update-application")
    ua.add_argument("id"); ua.add_argument("--job-id", required=True, dest="job_id")
    ua.add_argument("--status"); ua.add_argument("--rating", type=float); ua.add_argument("--note")

    n = sub.add_parser("note"); n.add_argument("id"); n.add_argument("--job-id", required=True, dest="job_id"); n.add_argument("--note", required=True)
    ex = sub.add_parser("export-applications"); ex.add_argument("job_id")

    return p


# ──────────────────────────────────────────────────────────────────────────────
# MCP server (stdio)


def run_mcp() -> int:
    """Tiny MCP stdio server. Exposes a tool per verb."""
    try:
        from mcp.server import Server  # type: ignore
        from mcp.server.stdio import stdio_server  # type: ignore
        from mcp.types import Tool, TextContent  # type: ignore
    except ImportError:
        print("MCP mode requires the 'mcp' package: pip install mcp", file=sys.stderr)
        return 1
    import asyncio

    server = Server("dj-company")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name="company", description="Read company profile", inputSchema={"type": "object", "properties": {}}),
            Tool(name="jobs", description="List jobs (optional status filter)", inputSchema={"type": "object", "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}}}),
            Tool(name="job", description="Read one job", inputSchema={"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}),
            Tool(name="applications", description="List applications for a job", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["job_id"]}),
            Tool(name="application", description="Read one application", inputSchema={"type": "object", "properties": {"id": {"type": "string"}, "job_id": {"type": "string"}}, "required": ["id", "job_id"]}),
            Tool(name="candidate", description="Read a candidate (must have applied)", inputSchema={"type": "object", "properties": {"uid": {"type": "string"}}, "required": ["uid"]}),
            Tool(name="analytics_funnel", description="Company-wide funnel", inputSchema={"type": "object", "properties": {"from": {"type": "string"}, "to": {"type": "string"}}}),
            Tool(name="billing_status", description="Card on file + plan tier", inputSchema={"type": "object", "properties": {}}),
            Tool(name="limits", description="Effective rate limits + usage", inputSchema={"type": "object", "properties": {}}),
            Tool(name="update_application", description="Update an application's status/rating/note", inputSchema={"type": "object", "properties": {"id": {"type": "string"}, "job_id": {"type": "string"}, "status": {"type": "string"}, "rating": {"type": "number"}, "note": {"type": "string"}}, "required": ["id", "job_id"]}),
        ]

    @server.call_tool()
    async def call_tool(name: str, args: dict) -> list[TextContent]:
        dj = DJ()
        result: Any
        if name == "company": result = dj.company()
        elif name == "jobs": result = dj.jobs(status=args.get("status"), limit=args.get("limit", 25))
        elif name == "job": result = dj.job(args["id"])
        elif name == "applications": result = dj.applications(args["job_id"], status=args.get("status"))
        elif name == "application": result = dj.application(args["id"], job_id=args["job_id"])
        elif name == "candidate": result = dj.candidate(args["uid"])
        elif name == "analytics_funnel": result = dj.analytics_funnel(from_=args.get("from"), to=args.get("to"))
        elif name == "billing_status": result = dj.billing_status()
        elif name == "limits": result = dj.limits()
        elif name == "update_application":
            result = dj.update_application(args["id"], job_id=args["job_id"], status=args.get("status"), rating=args.get("rating"), note=args.get("note"))
        else:
            result = {"error": f"unknown tool {name}"}
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    async def main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(main())
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
    return cmd_call(args)


if __name__ == "__main__":
    sys.exit(main())
