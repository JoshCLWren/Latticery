"""Resolve the repository operated on by the Factory runtime."""
from __future__ import annotations

import os
import re
import subprocess

_GITHUB_REMOTE_RE = re.compile(
    r"(?:github\.com[:/])(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)


def repository_name() -> str:
    """Return the host repository without assuming ComicPile.

    GitHub Actions supplies ``GITHUB_REPOSITORY``. Local runners may set the
    more explicit ``FACTORY_REPOSITORY``. Otherwise resolve ``origin`` so the
    copied Factory continues to work from a normal repository checkout.
    """
    configured = (
        os.environ.get("FACTORY_REPOSITORY")
        or os.environ.get("GITHUB_REPOSITORY")
        or ""
    ).strip()
    if configured:
        return configured

    try:
        proc = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            "unable to resolve Factory repository; set FACTORY_REPOSITORY or GITHUB_REPOSITORY"
        ) from exc

    remote = proc.stdout.strip()
    match = _GITHUB_REMOTE_RE.search(remote)
    if proc.returncode or not match:
        raise RuntimeError(
            "unable to resolve Factory repository from origin; set FACTORY_REPOSITORY or GITHUB_REPOSITORY"
        )
    return f"{match.group('owner')}/{match.group('repo')}"
