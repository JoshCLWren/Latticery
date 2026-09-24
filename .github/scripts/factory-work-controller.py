#!/usr/bin/env python3
"""Compatibility entry point backed by :mod:`latticery.factory_work_controller`."""
from __future__ import annotations

import sys
from pathlib import Path

# Trusted controllers are sometimes copied to a temporary directory before a
# PR checkout. Factory jobs still execute from the repository checkout, so the
# current working directory is the stable anchor for the packaged implementation.
_root = Path.cwd()
if not (_root / "latticery").is_dir():
    raise RuntimeError(
        "Factory compatibility wrapper must run from a repository containing latticery/"
    )
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Execute, rather than star-import, so private helpers and monkeypatching behave
# exactly as they did when this file contained the implementation itself.
__package__ = "latticery"
_impl = _root / "latticery" / "factory_work_controller.py"
exec(compile(_impl.read_bytes(), str(_impl), "exec"), globals(), globals())
