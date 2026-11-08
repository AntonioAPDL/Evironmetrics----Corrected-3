#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PROTECTED_GENERATED_PREFIXES = (
    "artifacts/",
    "figures/",
    "Figures/",
    "tables/generated_tex/",
    "reports/",
)
OVERLEAF_SOURCE_SUFFIXES = (
    ".tex",
    ".bib",
    ".bst",
    ".cls",
    ".sty",
)


@dataclass(frozen=True)
class Change:
    status: str
    path: str
    old_path: str | None = None
    content_delta: tuple[int | None, int | None] | None = None


def run_git(args: list[str], *, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def git_success(args: list[str]) -> bool:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode == 0


def parse_name_status(text: str) -> list[Change]:
    changes: list[Change] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            if len(parts) < 3:
                raise ValueError(f"Cannot parse name-status row: {line!r}")
            changes.append(Change(status=status[0], old_path=parts[1], path=parts[2]))
        else:
            if len(parts) < 2:
                raise ValueError(f"Cannot parse name-status row: {line!r}")
            changes.append(Change(status=status[0], path=parts[1]))
    return changes


def parse_numstat(text: str) -> dict[str, tuple[int | None, int | None]]:
    out: dict[str, tuple[int | None, int | None]] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        added, deleted, path = line.split("\t", 2)
        add_val = None if added == "-" else int(added)
        del_val = None if deleted == "-" else int(deleted)
        out[path] = (add_val, del_val)
    return out


def with_content_delta(changes: list[Change], numstat: dict[str, tuple[int | None, int | None]]) -> list[Change]:
    return [
        Change(
            status=change.status,
            path=change.path,
            old_path=change.old_path,
            content_delta=numstat.get(change.path),
        )
        for change in changes
    ]


def protected_generated(path: str) -> bool:
    return path.startswith(PROTECTED_GENERATED_PREFIXES)


def overleaf_source(path: str) -> bool:
    return path.endswith(OVERLEAF_SOURCE_SUFFIXES)


def mode_only(change: Change) -> bool:
    return change.status == "M" and change.content_delta == (0, 0)


def classify(changes: list[Change]) -> dict[str, list[Change]]:
    buckets = {
        "protected_generated": [],
        "overleaf_source": [],
        "mode_only": [],
        "unexpected": [],
    }
    for change in changes:
        paths = [change.path]
        if change.old_path:
            paths.append(change.old_path)
        if any(protected_generated(path) for path in paths):
            buckets["protected_generated"].append(change)
        elif mode_only(change):
            buckets["mode_only"].append(change)
        elif overleaf_source(change.path):
            buckets["overleaf_source"].append(change)
        else:
            buckets["unexpected"].append(change)
    return buckets


def print_bucket(name: str, rows: list[Change]) -> None:
    print(f"{name}: {len(rows)}")
    for row in rows[:30]:
        old = f"{row.old_path} -> " if row.old_path else ""
        delta = "" if row.content_delta is None else f" delta={row.content_delta}"
        print(f"  {row.status}\t{old}{row.path}{delta}")
    if len(rows) > 30:
        print(f"  ... {len(rows) - 30} more")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and optionally merge an Overleaf sync branch without accepting "
            "deletion-only changes to generated article assets."
        )
    )
    parser.add_argument("branch", help="Branch/ref to merge, e.g. origin/overleaf-2026-06-11-0850")
    parser.add_argument("--fetch", action="store_true", help="Run git fetch origin --prune before auditing.")
    parser.add_argument(
        "--merge-generated-deletions-only",
        action="store_true",
        help="If the branch has no TeX/Bib source edits and only protected generated-asset changes, merge with -s ours.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.fetch:
        run_git(["fetch", "origin", "--prune"])
    status = run_git(["status", "--porcelain"])
    if status:
        print("Refusing to run with a dirty working tree:", file=sys.stderr)
        print(status, file=sys.stderr)
        return 2

    branch = args.branch
    if git_success(["merge-base", "--is-ancestor", branch, "HEAD"]):
        print(f"{branch} is already merged into HEAD.")
        return 0

    base = run_git(["merge-base", "HEAD", branch])
    changes = parse_name_status(run_git(["diff", "--name-status", f"{base}..{branch}"]))
    numstat = parse_numstat(run_git(["diff", "--numstat", f"{base}..{branch}"]))
    changes = with_content_delta(changes, numstat)
    buckets = classify(changes)

    print(f"merge base: {base}")
    for name in ["overleaf_source", "protected_generated", "mode_only", "unexpected"]:
        print_bucket(name, buckets[name])

    if buckets["unexpected"]:
        print("Unexpected non-generated, non-TeX changes found. Inspect manually before merging.", file=sys.stderr)
        return 3
    if buckets["overleaf_source"]:
        print("Overleaf source edits found. Run a normal merge and resolve conflicts while preserving generated assets.")
        return 0
    if args.merge_generated_deletions_only:
        run_git(
            [
                "merge",
                "-s",
                "ours",
                "--no-ff",
                branch,
                "-m",
                f"Merge {Path(branch).name} preserving generated assets",
            ]
        )
        print(f"Merged {branch} with the ours strategy; generated assets preserved.")
    else:
        print("No source edits found. Recommended command:")
        print(f"  git merge -s ours --no-ff {branch} -m 'Merge {Path(branch).name} preserving generated assets'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
