"""Explicit host settings required by operational Factory machinery."""
from __future__ import annotations

import os


def factory_registry_issue() -> int:
    raw = os.environ.get("FACTORY_REGISTRY_ISSUE", "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        raise RuntimeError("FACTORY_REGISTRY_ISSUE must name the host repository's Factory registry issue")
    return int(raw)
