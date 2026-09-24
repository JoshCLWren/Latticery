#!/usr/bin/env python3
"""Copy the working Factory from a ComicPile checkout into Latticery.

This tool deliberately starts from the current source implementation. It copies
before refactoring, then applies only the portability edits needed for the code
to live in the ``latticery`` package and operate on a host repository selected
at runtime.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


SPECIAL_PYTHON = {
    "classify-fixed-model-run.py",
    "fixed-model-guard.py",
    "generate_factory_status_dashboard.py",
    "stale_pr_decay.py",
    "validate-free-model-factories.py",
}
SPECIAL_WORKFLOWS = {
    "main-health-gate.yml",
    "fixed-model-pr-repair-guard.yml",
    "fixed-model-runtime-observer.yml",
}
SPECIAL_TESTS = {
    "test_stale_pr_decay.py",
    "test_generate_factory_status_dashboard.py",
}
LOCAL_FACTORY_SCRIPTS = {
    "comic-pile-opencode-factory.sh": "latticery-opencode-factory.sh",
    "comic-pile-opencode-factory-runner.sh": "latticery-opencode-factory-runner.sh",
    "comic-pile-opencode-factory-heartbeat.sh": "latticery-opencode-factory-heartbeat.sh",
    "comic-pile-opencode-factory-overnight.sh": "latticery-opencode-factory-overnight.sh",
    "opencode-model-catalog.sh": "opencode-model-catalog.sh",
    "opencode-model-manifest.sh": "opencode-model-manifest.sh",
    "opencode-model-scout.sh": "opencode-model-scout.sh",
}
DOCS = {
    "AUTONOMOUS_FACTORY_POLICY.md",
    "FACTORY_GITHUB_VISIBILITY.md",
    "CHATGPT_FACTORY_PROMPT.md",
    "ISSUE_EXECUTION_PROTOCOL.md",
}
BEHAVIOR_TESTS = {
    "test_factory_work_policy.py",
    "test_factory_review_gate.py",
    "test_factory_work_controller.py",
    "test_factory_work_controller_runtime.py",
    "test_factory_zombie_run_liveness.py",
    "test_factory_completion_controller.py",
    "test_factory_full_completion_controller.py",
    "test_factory_migration_lane.py",
    "test_factory_candidate_health.py",
    "test_factory_provider_candidates.py",
    "test_factory_native_omniroute_selection.py",
    "test_factory_terminal_handoff_contract.py",
    "test_factory_unified_runtime_policy.py",
    "test_factory_owner_recognition.py",
    "test_factory_lease_recovery.py",
    "test_factory_parallel_assignments.py",
    "test_factory_capacity_refill_workflow.py",
    "test_factory_model_discovery_retirement.py",
    "test_factory_model_discovery_workflow.py",
    "test_factory_exact_head_merge_gate.py",
    "test_factory_recovery.py",
    "test_stale_pr_decay.py",
}


def module_name(filename: str) -> str:
    return Path(filename.replace("-", "_")).stem


def insert_after_future(source: str, line: str) -> str:
    if line in source:
        return source
    marker = "from __future__ import annotations\n"
    if marker in source:
        return source.replace(marker, marker + line + "\n", 1)
    return line + "\n" + source


def transform_python(source: str, modules: set[str]) -> str:
    """Make a copied sibling-script module importable as ``latticery.*``."""
    text = source
    for mod in sorted(modules, key=len, reverse=True):
        escaped = re.escape(mod)
        text = re.sub(
            rf"(?m)^(?P<i>\s*)from {escaped} import ",
            rf"\g<i>from .{mod} import ",
            text,
        )
        text = re.sub(
            rf"(?m)^(?P<i>\s*)import {escaped} as (?P<a>[A-Za-z_]\w*)\s*$",
            rf"\g<i>from . import {mod} as \g<a>",
            text,
        )
        text = re.sub(
            rf"(?m)^(?P<i>\s*)import {escaped}\s*$",
            rf"\g<i>from . import {mod}",
            text,
        )
        text = text.replace(
            f'importlib.import_module("{mod}")',
            f'importlib.import_module("latticery.{mod}")',
        )
        text = text.replace(
            f"importlib.import_module('{mod}')",
            f"importlib.import_module('latticery.{mod}')",
        )

    repo_patterns = (
        'os.environ.get("GITHUB_REPOSITORY", "JoshCLWren/comic-pile")',
        "os.environ.get('GITHUB_REPOSITORY', 'JoshCLWren/comic-pile')",
    )
    if any(pattern in text for pattern in repo_patterns):
        text = insert_after_future(text, "from .repository import repository_name")
        for pattern in repo_patterns:
            text = text.replace(pattern, "repository_name()")

    # The source Factory reserves ComicPile control-plane issues. In a reusable
    # package those exclusions belong to the host and are explicitly supplied.
    text = text.replace(
        "NON_EXECUTABLE_ISSUES = {679, 1093, 1109}",
        "NON_EXECUTABLE_ISSUES = {\n"
        "    int(value)\n"
        "    for value in os.environ.get('FACTORY_NON_EXECUTABLE_ISSUES', '').split(',')\n"
        "    if value.strip().isdigit()\n"
        "}",
    )

    # Registry issue #1093 is durable ComicPile infrastructure, not a universal
    # Factory constant. API-path uses are parameterized through one explicit env
    # setting and fail visibly when a host has not configured the registry.
    if "issues/1093" in text:
        text = insert_after_future(text, "from .runtime_config import factory_registry_issue")
        text = text.replace("issues/1093", "issues/{factory_registry_issue()}")

    # Product names in comments/docstrings/prompts should describe the host,
    # while persisted lowercase protocol markers remain untouched for cutover.
    text = text.replace("for ComicPile factories", "for Latticery factories")
    text = text.replace("for ComicPile.", "for a host repository.")
    text = text.replace("ComicPile completion-stage", "Factory completion-stage")
    return text


def wrapper_for(module: str) -> str:
    return f'''#!/usr/bin/env python3
"""Compatibility entry point for :mod:`latticery.{module}`."""
from __future__ import annotations

import sys
from pathlib import Path

# Trusted controllers are sometimes copied to a temporary directory before a
# PR checkout. The process still runs from the repository root, so make that
# checkout importable without duplicating the implementation in this wrapper.
root = Path.cwd()
if (root / "latticery").is_dir() and str(root) not in sys.path:
    sys.path.insert(0, str(root))

from latticery.{module} import *  # noqa: F401,F403

try:
    from latticery.{module} import main as _main
except ImportError:
    _main = None

if __name__ == "__main__":
    if _main is None:
        raise SystemExit("latticery.{module} has no CLI entry point")
    raise SystemExit(_main())
'''


def transform_shell(source: str) -> str:
    text = source.replace("/tmp/comic-pile-", "/tmp/latticery-")
    text = text.replace("ComicPile Factory", "Latticery Factory")
    # Agent prompts must target the repository the worker is actually operating
    # on rather than the Factory's first host.
    text = text.replace(
        "for JoshCLWren/comic-pile.",
        'for ${FACTORY_REPOSITORY:-${GITHUB_REPOSITORY:-the-current-repository}}.',
    )
    text = text.replace(
        "for JoshCLWren/comic-pile ",
        'for ${FACTORY_REPOSITORY:-${GITHUB_REPOSITORY:-the-current-repository}} ',
    )
    # Registry endpoints are a host setting. A missing value aborts at shell
    # expansion instead of silently reading ComicPile #1093 in another repo.
    text = text.replace(
        "issues/1093",
        "issues/${FACTORY_REGISTRY_ISSUE:?FACTORY_REGISTRY_ISSUE is required}",
    )
    return text


def transform_workflow(source: str) -> str:
    text = source.replace(
        "issues/1093",
        "issues/${FACTORY_REGISTRY_ISSUE:?FACTORY_REGISTRY_ISSUE is required}",
    )
    text = text.replace("#1093", "#${FACTORY_REGISTRY_ISSUE}")
    # Workflows call compatibility wrappers at the established paths. The
    # implementation itself now lives in the package.
    return text


def transform_doc(source: str) -> str:
    text = source.replace("JoshCLWren/comic-pile", "the host repository")
    text = text.replace("ComicPile's", "The host repository's")
    text = text.replace("ComicPile", "the host repository")
    text = text.replace("registry issue #1093", "the configured Factory registry issue")
    text = text.replace("issue #1093", "the configured Factory registry issue")
    return text


def copy_text(src: Path, dst: Path, transform=lambda value: value) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(transform(src.read_text(encoding="utf-8")), encoding="utf-8")
    if os.access(src, os.X_OK):
        dst.chmod(dst.stat().st_mode | 0o111)


def copy_tests(source: Path, destination: Path) -> list[str]:
    copied: list[str] = []
    for name in sorted(BEHAVIOR_TESTS | SPECIAL_TESTS):
        src = source / "tests" / name
        if not src.exists():
            continue
        copy_text(src, destination / "tests" / name)
        copied.append(name)

    # The pure review-policy test lives beside the original controller.
    review_test = source / ".github/scripts/test_factory_review_policy.py"
    if review_test.exists():
        text = review_test.read_text(encoding="utf-8").replace(
            "from factory_review_policy import (",
            "from latticery.factory_review_policy import (",
        )
        (destination / "tests/test_factory_review_policy.py").write_text(text, encoding="utf-8")
        copied.append("test_factory_review_policy.py")

    # Keep next-task selection regression coverage, but point it at the package.
    next_task_test = source / "scripts/test_next_task.py"
    if next_task_test.exists():
        text = next_task_test.read_text(encoding="utf-8")
        text = re.sub(
            r"(?ms)^SPEC = importlib\.util\.spec_from_file_location\(.*?SPEC\.loader\.exec_module\(next_task\)\n",
            "from latticery import next_task\n",
            text,
        )
        copy_path = destination / "tests/test_next_task.py"
        copy_path.write_text(text, encoding="utf-8")
        copied.append("test_next_task.py")
    return copied


def update_readme(destination: Path) -> None:
    path = destination / "README.md"
    text = path.read_text(encoding="utf-8")
    old = (
        "Latticery is being extracted from the autonomous software factory developed inside "
        "[ComicPile](https://github.com/JoshCLWren/comic-pile). The extraction is intentionally "
        "architectural rather than a wholesale code copy: generic coordination primitives belong "
        "here; application-specific policy remains behind adapters."
    )
    new = (
        "Latticery is extracted from the working autonomous software Factory developed inside "
        "[ComicPile](https://github.com/JoshCLWren/comic-pile). The working Factory is the "
        "behavioral specification: orchestration, leases, completion, review, recovery, CI gates, "
        "worker execution, and backpressure are copied first, with only host-specific assumptions "
        "parameterized. Refactoring follows extraction, not the other way around."
    )
    text = text.replace(old, new)
    text = text.replace(
        "**Early extraction.** The existing system is proven inside ComicPile, but the standalone Latticery API and package boundaries are being defined now. Expect interfaces to move while the generic runtime is separated from its first host application.",
        "**Working Factory extraction.** The reusable Factory implementation now lives in the top-level `latticery/` package, with its operational GitHub Actions and shell runtime preserved alongside it. ComicPile remains on its original copy until a separate cutover switches the host to consume Latticery.",
    )
    path.write_text(text, encoding="utf-8")


def ensure_package_files(destination: Path) -> None:
    package = destination / "latticery"
    package.mkdir(parents=True, exist_ok=True)
    init = package / "__init__.py"
    if not init.exists():
        init.write_text('"""Latticery: autonomous software delivery across the work lattice."""\n\n__version__ = "0.0.1"\n', encoding="utf-8")

    (package / "repository.py").write_text('''"""Resolve the repository operated on by the Factory runtime."""
from __future__ import annotations

import os
import re
import subprocess

_GITHUB_REMOTE_RE = re.compile(r"(?:github\\.com[:/])(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\\.git)?$")


def repository_name() -> str:
    configured = (os.environ.get("FACTORY_REPOSITORY") or os.environ.get("GITHUB_REPOSITORY") or "").strip()
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
        raise RuntimeError("unable to resolve Factory repository; set FACTORY_REPOSITORY or GITHUB_REPOSITORY") from exc
    match = _GITHUB_REMOTE_RE.search(proc.stdout.strip())
    if proc.returncode or not match:
        raise RuntimeError("unable to resolve Factory repository from origin; set FACTORY_REPOSITORY or GITHUB_REPOSITORY")
    return f"{match.group('owner')}/{match.group('repo')}"
''', encoding="utf-8")

    (package / "runtime_config.py").write_text('''"""Explicit host settings required by operational Factory machinery."""
from __future__ import annotations

import os


def factory_registry_issue() -> int:
    raw = os.environ.get("FACTORY_REGISTRY_ISSUE", "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        raise RuntimeError("FACTORY_REGISTRY_ISSUE must name the host repository's Factory registry issue")
    return int(raw)
''', encoding="utf-8")


def write_layout_test(destination: Path) -> None:
    path = destination / "tests/test_package_layout.py"
    path.write_text('''from __future__ import annotations

import importlib
from pathlib import Path


def test_one_top_level_latticery_package() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "latticery/__init__.py").is_file()
    assert not (root / "src/latticery").exists()
    package = importlib.import_module("latticery")
    assert Path(package.__file__).resolve().parent == (root / "latticery").resolve()


def test_package_has_operational_factory_spine() -> None:
    root = Path(__file__).resolve().parents[1]
    required = {
        "factory_work_policy.py",
        "factory_review_policy.py",
        "factory_work_controller.py",
        "factory_review_controller.py",
        "factory_completion_controller.py",
        "factory_full_completion_controller.py",
        "factory_capacity_policy.py",
        "stale_pr_decay.py",
        "next_task.py",
    }
    present = {path.name for path in (root / "latticery").glob("*.py")}
    assert required <= present
''', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ComicPile checkout containing the working Factory")
    parser.add_argument("--destination", type=Path, default=Path.cwd())
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    scripts_dir = source / ".github/scripts"
    if not scripts_dir.is_dir():
        raise SystemExit(f"Factory scripts directory not found: {scripts_dir}")

    ensure_package_files(destination)

    python_sources = [
        path
        for path in scripts_dir.glob("*.py")
        if not path.name.startswith("test_")
        and path.name != "factory_work_policy_latticery_ref.py"
        and (path.name.startswith("factory") or path.name in SPECIAL_PYTHON)
    ]
    module_by_source = {path: module_name(path.name) for path in python_sources}
    modules = set(module_by_source.values()) | {"next_task"}

    for src, module in sorted(module_by_source.items(), key=lambda item: item[0].name):
        copied = transform_python(src.read_text(encoding="utf-8"), modules)
        (destination / "latticery" / f"{module}.py").write_text(copied, encoding="utf-8")
        wrapper = destination / ".github/scripts" / src.name
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        wrapper.write_text(wrapper_for(module), encoding="utf-8")
        wrapper.chmod(0o755)

    # Preserve the simpler issue selector as an importable package module.
    next_task = source / "scripts/next_task.py"
    copy_text(next_task, destination / "latticery/next_task.py", lambda value: transform_python(value, modules))

    # Shell/JS operational machinery stays shell/JS. Do not translate it merely
    # for consistency.
    for src in sorted(scripts_dir.iterdir()):
        if src.suffix in {".sh", ".cjs"} and "factory" in src.name:
            copy_text(src, destination / ".github/scripts" / src.name, transform_shell)
    for name in ("free-model-factory-worker-primitives.sh", "factory-semantic-verdict.sh", "factory-gh-rest-shim.sh"):
        src = scripts_dir / name
        if src.exists():
            copy_text(src, destination / ".github/scripts" / name, transform_shell)

    manifest = source / ".github/free-model-factories.tsv"
    if manifest.exists():
        copy_text(manifest, destination / ".github/free-model-factories.tsv")

    # Copy the active Factory workflow/runtime surface but not ComicPile product
    # CI/deploy workflows. Product CI is supplied independently by each host.
    for src in sorted((source / ".github/workflows").glob("*.yml")):
        if "factory" in src.name or src.name in SPECIAL_WORKFLOWS:
            copy_text(src, destination / ".github/workflows" / src.name, transform_workflow)

    # Local runner/heartbeat/overnight machinery is reusable after removing the
    # product-branded filename and prompt text.
    for src_name, dst_name in LOCAL_FACTORY_SCRIPTS.items():
        src = source / "scripts" / src_name
        if src.exists():
            copy_text(src, destination / "scripts" / dst_name, transform_shell)

    for doc in DOCS:
        src = source / "docs" / doc
        if src.exists():
            copy_text(src, destination / "docs" / doc, transform_doc)

    copied_tests = copy_tests(source, destination)
    write_layout_test(destination)
    update_readme(destination)

    # The old bootstrap package must not coexist with the extracted package.
    src_layout = destination / "src"
    if src_layout.exists():
        shutil.rmtree(src_layout)

    print(f"Extracted {len(python_sources) + 1} Python modules into latticery/")
    print(f"Copied {len(copied_tests)} Factory behavior tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
