#!/usr/bin/env python3
"""Compatibility entry point for :mod:`latticery.factory_capacity_policy`."""
from __future__ import annotations

import sys
from pathlib import Path

# Trusted controllers are sometimes copied to a temporary directory before a
# PR checkout. The process still runs from the repository root, so make that
# checkout importable without duplicating the implementation in this wrapper.
root = Path.cwd()
if (root / "latticery").is_dir() and str(root) not in sys.path:
    sys.path.insert(0, str(root))

from latticery.factory_capacity_policy import *  # noqa: F401,F403

try:
    from latticery.factory_capacity_policy import main as _main
except ImportError:
    _main = None

if __name__ == "__main__":
    if _main is None:
        raise SystemExit("latticery.factory_capacity_policy has no CLI entry point")
    raise SystemExit(_main())
