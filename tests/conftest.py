"""Compatibility settings for regression tests copied from ComicPile."""
from __future__ import annotations

import os

os.environ.setdefault("FACTORY_REGISTRY_ISSUE", "1093")
os.environ.setdefault("FACTORY_NON_EXECUTABLE_ISSUES", "679,1093,1109")
