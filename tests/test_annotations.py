"""MCP tool annotations are accurate, and the write-set can't silently drift.

Every MCP tool carries `readOnlyHint` / `destructiveHint` / `openWorldHint` so
clients can auto-approve reads and prompt on writes. The read/write split must
match what each command actually does over HTTP — a write mislabelled read-only
would let a client auto-approve a mutation.

`test_write_set_matches_http_verbs` re-derives the network write set straight
from the source: it AST-scans every ``DJ`` method for the HTTP verb passed to
``self._request(...)`` (GET = read, everything else = write), maps each MCP tool
to its underlying method, and fails if ``_WRITE_COMMANDS`` drifts from reality.
"""
import ast
import os

import dj  # noqa: E402 (sys.path set up by conftest.py)

_SRC = os.path.join(os.path.dirname(__file__), "..", "py", "dj.py")

# MCP tool name -> DJ method name it dispatches to (kept in sync with
# _mcp_tool_specs handlers; the lambdas aren't statically introspectable).
_TOOL_TO_METHOD = {
    "get_company": "company",
    "update_company": "update_company",
    "list_jobs": "jobs",
    "get_job": "job",
    "create_job": "create_job",
    "create_trial_job": "trial_post",
    "update_job": "update_job",
    "delete_job": "delete_job",
    "list_applications": "applications",
    "get_application": "application",
    "update_application": "update_application",
    "export_applications": "export_applications",
    "get_candidate": "candidate",
    "analytics_jobs": "analytics_jobs",
    "analytics_funnel": "analytics_funnel",
    "billing_status": "billing_status",
    "get_limits": "limits",
}
_WRITE_VERBS = {"POST", "PATCH", "PUT", "DELETE"}


def _method_http_verbs():
    """Return {method_name: set(HTTP verbs it issues via self._request)}.

    Resolves one level of self-call (e.g. note() -> update_application()).
    """
    tree = ast.parse(open(_SRC, encoding="utf-8").read())
    dj_cls = next(c for c in tree.body
                  if isinstance(c, ast.ClassDef) and c.name == "DJ")

    direct, self_calls = {}, {}
    for fn in dj_cls.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        verbs, calls = set(), set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if n.func.attr == "_request" and n.args:
                    first = n.args[0]
                    if isinstance(first, ast.Constant):
                        verbs.add(first.value)
                # self.<other_method>(...)
                if (isinstance(n.func.value, ast.Name) and n.func.value.id == "self"
                        and n.func.attr != "_request"):
                    calls.add(n.func.attr)
        direct[fn.name] = verbs
        self_calls[fn.name] = calls

    resolved = {}
    for name in direct:
        verbs = set(direct[name])
        for callee in self_calls.get(name, ()):
            verbs |= direct.get(callee, set())
        resolved[name] = verbs
    return resolved


def _is_write(method_name, verbs_by_method):
    return bool(verbs_by_method.get(method_name, set()) & _WRITE_VERBS)


def test_mcp_tool_count_is_seventeen():
    assert len(dj._mcp_tool_specs()) == 17


def test_every_tool_command_is_in_annotation_universe():
    # Each tool's `command` must resolve to a valid annotation (write or read).
    for name, spec in dj._mcp_tool_specs().items():
        ann = dj._tool_annotations(spec["command"])
        assert set(ann) == {"readOnlyHint", "destructiveHint", "openWorldHint"}, name


def test_tool_annotations_match_http_verbs():
    verbs = _method_http_verbs()
    specs = dj._mcp_tool_specs()
    for tool, method in _TOOL_TO_METHOD.items():
        assert tool in specs, f"{tool} missing from _mcp_tool_specs"
        is_write = _is_write(method, verbs)
        ann = dj._tool_annotations(specs[tool]["command"])
        assert ann["readOnlyHint"] is (not is_write), (
            f"{tool} ({method}) readOnlyHint wrong: HTTP write={is_write}"
        )


def test_write_set_matches_http_verbs():
    """_WRITE_COMMANDS (kebab) must equal the network-derived write set plus the
    two local-only writes (setup, note's parent isn't network-distinct)."""
    verbs = _method_http_verbs()
    specs = dj._mcp_tool_specs()
    derived = {
        specs[tool]["command"]
        for tool, method in _TOOL_TO_METHOD.items()
        if _is_write(method, verbs)
    }
    # `note` (CLI-only convenience over update_application) + `setup` (local
    # file write) are not exposed as MCP tools but are still writes.
    derived |= {"setup", "note"}
    assert dj._WRITE_COMMANDS == derived, (
        "_WRITE_COMMANDS drifted from the source HTTP verbs.\n"
        f"missing (writes not marked): {sorted(derived - dj._WRITE_COMMANDS)}\n"
        f"extra (marked but not writes): {sorted(dj._WRITE_COMMANDS - derived)}"
    )


def test_destructive_subset_of_writes():
    assert dj._DESTRUCTIVE_COMMANDS <= dj._WRITE_COMMANDS


def test_delete_is_destructive():
    assert dj._tool_annotations("delete_job")["destructiveHint"] is True


def test_reads_are_read_only_and_not_destructive():
    for n in ("company", "jobs", "job", "applications", "application",
              "candidate", "analytics-jobs", "analytics-funnel", "billing", "limits"):
        ann = dj._tool_annotations(n)
        assert ann["readOnlyHint"] is True, n
        assert ann["destructiveHint"] is False, n


def test_writes_are_not_read_only():
    for n in ("update-company", "post-job", "update-job", "delete-job",
              "trial-post", "update-application", "export-applications"):
        assert dj._tool_annotations(n)["readOnlyHint"] is False, n


def test_local_commands_are_not_open_world():
    assert dj._tool_annotations("setup")["openWorldHint"] is False
    assert dj._tool_annotations("workflows")["openWorldHint"] is False
    assert dj._tool_annotations("company")["openWorldHint"] is True


def test_annotations_accept_snake_or_kebab():
    assert dj._tool_annotations("update_job") == dj._tool_annotations("update-job")
