#!/usr/bin/env python3
"""Apply the small host-portability edits required after copying the Factory.

This intentionally operates *after* the faithful source copy. It is not a
redesign pass. It only repairs assumptions whose meaning changed because the
implementation moved from ``.github/scripts`` into ``latticery/`` or because a
value belonged to ComicPile rather than to the Factory protocol itself.
"""
from __future__ import annotations

import argparse
from pathlib import Path


OLD_MANIFEST_PATH = 'Path(__file__).resolve().parents[1] / "free-model-factories.tsv"'
NEW_MANIFEST_PATH = (
    'Path(__file__).resolve().parents[1] / ".github" / "free-model-factories.tsv"'
)
OLD_ISSUE_FILTER = (
    'map(select(.number != 679 and .number != 1093 and .number != 1109))'
)
NEW_ISSUE_FILTER = (
    'map(select(.number as $number | '
    '((env.FACTORY_NON_EXECUTABLE_ISSUES // "" | split(",") | map(tonumber?)) '
    '| index($number) | not)))'
)
OLD_GRAPHQL_REPO = "-F owner='JoshCLWren' -F name='comic-pile'"
NEW_GRAPHQL_REPO = (
    '-F owner="${GITHUB_REPOSITORY%%/*}" -F name="${GITHUB_REPOSITORY#*/}"'
)


def text_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    paths.extend(sorted((root / "latticery").glob("*.py")))
    paths.extend(
        sorted(
            path
            for path in (root / ".github/scripts").glob("*")
            if path.is_file() and path.suffix in {".py", ".sh", ".cjs"}
        )
    )
    paths.extend(
        sorted(
            path
            for path in (root / "scripts").glob("*")
            if path.is_file() and "factory" in path.name
        )
    )
    paths.extend(sorted((root / ".github/workflows").glob("*.yml")))
    return paths


def repair(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    if path.parent.name == "latticery":
        text = text.replace(OLD_MANIFEST_PATH, NEW_MANIFEST_PATH)

    if path.suffix in {".sh", ".cjs"} or path.parent.name == "scripts":
        text = text.replace(OLD_ISSUE_FILTER, NEW_ISSUE_FILTER)
        text = text.replace(OLD_GRAPHQL_REPO, NEW_GRAPHQL_REPO)
        text = text.replace(
            "JoshCLWren/comic-pile",
            "${FACTORY_REPOSITORY:-${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}}",
        )

    if path.parent.name == "workflows":
        text = text.replace("JoshCLWren/comic-pile", "${{ github.repository }}")
        # Runtime-facing names and synthetic smoke-test titles belong to the
        # extracted host, not to ComicPile. Persisted lowercase protocol marker
        # names remain untouched for cutover compatibility.
        text = text.replace("ComicPile", "Latticery")

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def audit(paths: list[Path]) -> None:
    forbidden = {
        "ComicPile repository target": "JoshCLWren/comic-pile",
        "ComicPile GraphQL owner": "owner='JoshCLWren'",
        "ComicPile GraphQL repo": "name='comic-pile'",
        "ComicPile registry endpoint": "issues/1093",
        "ComicPile fixed exclusion set": ".number != 679 and .number != 1093 and .number != 1109",
        "ComicPile Python exclusion set": "NON_EXECUTABLE_ISSUES = {679, 1093, 1109}",
    }
    failures: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        checks = dict(forbidden)
        if path.parent.name == "workflows":
            checks["ComicPile runtime branding"] = "ComicPile"
        for label, needle in checks.items():
            if needle in text:
                failures.append(f"{path}: {label}: {needle}")
    if failures:
        raise RuntimeError(
            "Factory executable surface still contains host assumptions:\n  "
            + "\n  ".join(failures)
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.destination.resolve()
    paths = text_files(root)
    changed = [path for path in paths if repair(path)]
    audit(paths)
    print(f"Repaired {len(changed)} copied Factory files; portability audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
