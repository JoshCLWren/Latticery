from __future__ import annotations

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
