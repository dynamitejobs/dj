"""Shared fixtures + import shim for the offline test suite.

These tests never touch the network. They exercise the version mirrors, MCP
tool specs, and read/write annotations directly.

The client ships as a package (``py/__init__.py``), so we must NOT put ``py/``
on ``sys.path`` — a directory literally named ``py`` would shadow pytest's own
legacy ``py`` dependency at import time. Instead we load ``py/dj.py`` by file
path under the module name ``dj`` and register it in ``sys.modules`` so the test
files' ``import dj`` resolves to it.

Run with the ``pytest`` console script, NOT ``python -m pytest``:

    pytest tests/            # ✅  works from the repo root
    python -m pytest tests/  # ❌  puts cwd on sys.path[0] → ./py shadows `py`

``-m pytest`` works fine when invoked from inside ``tests/``.
"""
import importlib.util
import os
import sys

_DJ_PATH = os.path.join(os.path.dirname(__file__), "..", "py", "dj.py")

if "dj" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("dj", _DJ_PATH)
    _dj = importlib.util.module_from_spec(_spec)
    sys.modules["dj"] = _dj
    _spec.loader.exec_module(_dj)
