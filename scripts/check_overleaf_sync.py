#!/usr/bin/env python3
"""Read-only check that live Overleaf sync commits belong to proposed main."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_REF = "refs/heads/main"
OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
TIMEOUT_SECONDS = 45


class SyncCheckError(RuntimeError):
    pass


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "never",
        "GIT_OPTIONAL_LOCKS": "0",
    })
    try:
        return subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo), *args],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        # Exception text and Git stderr may contain credentials from a URL.
        raise SyncCheckError("Git check failed or timed out; no push was authorized.") from exc


def proposed_main(updates: str) -> str | None:
    candidate = None
    for line in updates.splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise SyncCheckError("Malformed pre-push ref update; refusing the push.")
        _local_ref, local_oid, remote_ref, _remote_oid = fields
        if remote_ref != MAIN_REF:
            continue
        if candidate is not None:
            raise SyncCheckError("Multiple updates to main; refusing the push.")
        if not OBJECT_ID.fullmatch(local_oid):
            raise SyncCheckError("Invalid proposed main object ID; refusing the push.")
        if set(local_oid) == {"0"}:
            raise SyncCheckError("Deleting main is blocked by the Overleaf sync guard.")
        candidate = local_oid
    return candidate


def resolve_commit(repo: Path, ref: str) -> str:
    result = git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    oid = result.stdout.strip()
    if result.returncode or not OBJECT_ID.fullmatch(oid):
        raise SyncCheckError("The proposed main commit is unavailable locally.")
    return oid


def check_sync(repo: Path, remote: str, main: str) -> list[str]:
    main_oid = resolve_commit(repo, main)
    live = git(repo, "ls-remote", "--heads", "--", remote, "refs/heads/overleaf-*")
    if live.returncode:
        raise SyncCheckError(
            "Could not query live Overleaf branches. Check connectivity/authentication and retry."
        )
    branches: list[tuple[str, str]] = []
    for line in live.stdout.splitlines():
        fields = line.split("\t")
        if (len(fields) != 2 or not OBJECT_ID.fullmatch(fields[0])
                or not fields[1].startswith("refs/heads/overleaf-")):
            raise SyncCheckError("Unexpected remote branch response; refusing the push.")
        branches.append((fields[0], fields[1]))
    blocked: list[str] = []
    for oid, ref in sorted(branches, key=lambda item: item[1]):
        present = git(repo, "cat-file", "-e", oid + "^{commit}")
        if present.returncode:
            blocked.append(ref + " (live commit is not available locally)")
            continue
        ancestor = git(repo, "merge-base", "--is-ancestor", oid, main_oid)
        if ancestor.returncode == 1:
            blocked.append(ref + " (not merged into the proposed main)")
        elif ancestor.returncode:
            raise SyncCheckError("Could not verify Overleaf ancestry; refusing the push.")
    if blocked:
        raise SyncCheckError(
            "Pending Overleaf history blocks this main update:\n  "
            + "\n  ".join(blocked)
            + "\nFetch the remote, review and merge the named branch(es), then retry. "
              "Do not discard source edits or delete a branch to bypass this check."
        )
    return [ref for _oid, ref in branches]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--remote", default="origin", help="Remote name for a manual read-only check.")
    parser.add_argument("--main-ref", default="HEAD", help="Proposed main commit for a manual check.")
    parser.add_argument("--pre-push", nargs=2, metavar=("REMOTE_NAME", "REMOTE_LOCATION"),
                        help="Git pre-push mode; reads ref updates from standard input.")
    args = parser.parse_args(argv)
    try:
        if args.pre_push is not None:
            candidate = proposed_main(sys.stdin.read())
            if candidate is None:
                return 0  # Non-main pushes do not perform remote queries.
            remote = args.pre_push[1]
        else:
            candidate, remote = args.main_ref, args.remote
        branches = check_sync(args.repo, remote, candidate)
    except SyncCheckError as exc:
        print("Overleaf sync guard: " + str(exc), file=sys.stderr)
        return 1
    print(f"Overleaf sync guard: main includes all {len(branches)} live Overleaf branch(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
