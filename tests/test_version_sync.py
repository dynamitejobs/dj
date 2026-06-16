"""Guard against version drift across the repo.

``VERSION`` in ``py/dj.py`` is the single source of truth — the wheel reads it
dynamically at build time (see ``pyproject.toml`` ``[tool.hatch.version]``).
Three other files carry a hand-maintained copy of the same version:

- ``manifest.json`` — the MCPB manifest ``version`` field
- ``server.json``   — the MCP Registry metadata ``version`` field
- ``py/config.json``— the skill metadata ``version`` field

None is wired to the constant, so bumping ``VERSION`` without updating them
would ship a mismatched manifest / metadata. These tests fail the build in that
case, forcing all of them to stay in lockstep.
"""
import json
import os
import re

import dj  # noqa: E402 (sys.path is set up by conftest.py)

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read_json_version(*relative_path):
    with open(os.path.join(_REPO_ROOT, *relative_path), encoding="utf-8") as fh:
        return json.load(fh)["version"]


def test_version_is_a_valid_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", dj.VERSION), dj.VERSION


def test_manifest_version_matches_constant():
    manifest = _read_json_version("manifest.json")
    assert manifest == dj.VERSION, (
        f"manifest.json version {manifest!r} != VERSION {dj.VERSION!r}. "
        "Bump manifest.json to match py/dj.py."
    )


def test_server_json_version_matches_constant():
    server = _read_json_version("server.json")
    assert server == dj.VERSION, (
        f"server.json version {server!r} != VERSION {dj.VERSION!r}. "
        "Bump server.json to match py/dj.py."
    )


def test_server_json_package_version_matches_constant():
    with open(os.path.join(_REPO_ROOT, "server.json"), encoding="utf-8") as fh:
        server = json.load(fh)
    for pkg in server.get("packages", []):
        assert pkg.get("version") == dj.VERSION, (
            f"server.json package version {pkg.get('version')!r} != VERSION "
            f"{dj.VERSION!r}."
        )


def test_config_version_matches_constant():
    config = _read_json_version("py", "config.json")
    assert config == dj.VERSION, (
        f"py/config.json version {config!r} != VERSION {dj.VERSION!r}. "
        "Bump py/config.json to match py/dj.py."
    )
