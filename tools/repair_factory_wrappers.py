#!/usr/bin/env python3
"""Rewrite extracted Factory compatibility wrappers without hiding private seams.

The source Factory's regression tests load controller files directly and
monkeypatch private helpers in those module namespaces. A star-import wrapper
breaks that contract because underscore-prefixed names are omitted and imported
functions retain the package module's globals. Execute the package source in the
wrapper namespace instead. This keeps one implementation on disk while
preserving the source module's observable behavior and monkeypatch seams.
"""
from __future__ import annotations

import argparse
from pathlib import Path


HEADER = """#!/usr/bin/env python3
\"\"\"Compatibility entry point backed by :mod:`latticery.{module}`.\"\"\"
from __future__ import annotations

import sys
from pathlib import Path

# Trusted controllers are sometimes copied to a temporary directory before a
# PR checkout. Factory jobs still execute from the repository checkout, so the
# current working directory is the stable anchor for the packaged implementation.
_root = Path.cwd()
if not (_root / \"latticery\").is_dir():
    raise RuntimeError(
        \"Factory compatibility wrapper must run from a repository containing latticery/\"
    )
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Execute, rather than star-import, so private helpers and monkeypatching behave
# exactly as they did when this file contained the implementation itself.
__package__ = \"latticery\"
_impl = _root / \"latticery\" / \"{module}.py\"
exec(compile(_impl.read_bytes(), str(_impl), \"exec\"), globals(), globals())
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.destination.resolve()
    scripts = root / ".github/scripts"
    package = root / "latticery"

    rewritten = 0
    for wrapper in sorted(scripts.glob("*.py")):
        text = wrapper.read_text(encoding="utf-8")
        marker = "Compatibility entry point for :mod:`latticery."
        if marker not in text:
            continue
        module = wrapper.stem.replace("-", "_")
        implementation = package / f"{module}.py"
        if not implementation.is_file():
            raise RuntimeError(f"missing packaged implementation for {wrapper}: {implementation}")
        wrapper.write_text(HEADER.format(module=module), encoding="utf-8")
        wrapper.chmod(0o755)
        rewritten += 1

    if not rewritten:
        raise RuntimeError("no extracted Factory compatibility wrappers were found")
    print(f"Rewrote {rewritten} Factory compatibility wrappers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
