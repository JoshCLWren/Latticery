#!/usr/bin/env python3
"""Finish the regression-test side of the Factory extraction.

The working Factory's tests are part of the specification. Copy their durable
fixtures/state and retarget source-inspection assertions from the old script
locations to the extracted ``latticery`` modules. ComicPile-specific registry
values are supplied only inside the compatibility test environment.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected extraction-test seam not found in {path}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--destination", type=Path, default=Path.cwd())
    args = parser.parse_args()
    source = args.source.resolve()
    root = args.destination.resolve()

    fixtures = source / "tests/fixtures/opencode-catalog"
    fixture_dest = root / "tests/fixtures/opencode-catalog"
    if fixture_dest.exists():
        shutil.rmtree(fixture_dest)
    shutil.copytree(fixtures, fixture_dest)

    expected_workers = source / ".github/factory-expected-workers.json"
    shutil.copy2(expected_workers, root / ".github/factory-expected-workers.json")

    # Preserve the source host's historical registry/exclusion semantics only
    # while running its copied regression suite. Runtime defaults remain generic.
    (root / "tests/conftest.py").write_text(
        '"""Compatibility settings for regression tests copied from ComicPile."""\n'
        'from __future__ import annotations\n\n'
        'import os\n\n'
        'os.environ.setdefault("FACTORY_REGISTRY_ISSUE", "1093")\n'
        'os.environ.setdefault("FACTORY_NON_EXECUTABLE_ISSUES", "679,1093,1109")\n',
        encoding="utf-8",
    )

    completion = root / "tests/test_factory_completion_controller.py"
    replace(
        completion,
        'SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "factory_completion_controller.py"\n'
        'CONTROLLER_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "factory-work-controller.py"\n'
        'SPEC = importlib.util.spec_from_file_location("factory_completion_controller", SCRIPT)\n'
        'assert SPEC is not None and SPEC.loader is not None\n'
        'controller = importlib.util.module_from_spec(SPEC)\n'
        'sys.modules[SPEC.name] = controller\n'
        'SPEC.loader.exec_module(controller)\n',
        'ROOT = Path(__file__).resolve().parents[1]\n'
        'SCRIPT = ROOT / "latticery" / "factory_completion_controller.py"\n'
        'CONTROLLER_PATH = ROOT / "latticery" / "factory_work_controller.py"\n'
        'from latticery import factory_completion_controller as controller\n',
    )

    retirement = root / "tests/test_factory_model_discovery_retirement.py"
    replace(retirement, 'import importlib.util\n', 'import importlib\nimport importlib.util\n')
    replace(retirement, 'SCRIPTS = ROOT / ".github" / "scripts"\n', 'SCRIPTS = ROOT / "latticery"\n')
    replace(
        retirement,
        'def _load(name: str, filename: str) -> ModuleType:\n'
        '    """Load a ``.github/scripts`` module without packaging that tree."""\n'
        '    sys.path.insert(0, str(SCRIPTS))\n'
        '    path = SCRIPTS / filename\n'
        '    spec = importlib.util.spec_from_file_location(name, path)\n'
        '    assert spec is not None\n'
        '    assert spec.loader is not None\n'
        '    module = importlib.util.module_from_spec(spec)\n'
        '    sys.modules[name] = module\n'
        '    spec.loader.exec_module(module)\n'
        '    return module\n',
        'def _load(name: str, filename: str) -> ModuleType:\n'
        '    """Load the extracted package module while preserving test call sites."""\n'
        '    del name\n'
        '    module = filename.removesuffix(".py").replace("-", "_")\n'
        '    return importlib.import_module(f"latticery.{module}")\n',
    )

    capacity = root / "tests/test_factory_capacity_refill_workflow.py"
    replace(
        capacity,
        '"repos/${GITHUB_REPOSITORY}/issues/1093/comments?per_page=100"',
        '"repos/${GITHUB_REPOSITORY}/issues/${FACTORY_REGISTRY_ISSUE:?FACTORY_REGISTRY_ISSUE is required}/comments?per_page=100"',
    )

    discovery = root / "tests/test_factory_model_discovery_workflow.py"
    replace(
        discovery,
        'assert "issues/1093/comments" in workflow',
        'assert "issues/${FACTORY_REGISTRY_ISSUE:?FACTORY_REGISTRY_ISSUE is required}/comments" in workflow',
    )
    replace(
        discovery,
        'assert \'gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/1093/comments?per_page=100"\' in runner',
        'assert \'gh api --paginate "repos/${GITHUB_REPOSITORY}/issues/${FACTORY_REGISTRY_ISSUE:?FACTORY_REGISTRY_ISSUE is required}/comments?per_page=100"\' in runner',
    )

    print("Copied Factory regression fixtures/state and retargeted package source assertions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
