#!/usr/bin/env python3
"""Refresh or check only the editorial table presentation and axis annotation.

Both builders use retained, validated results. This command never launches model
fitting, predictive simulation or scoring, and does not call the broader asset
refresh. --check leaves all tracked manuscript files unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def commands(article_root: Path, check: bool = False) -> list[list[str]]:
    root = article_root.resolve()
    result = [
        [sys.executable, '-B', str(root / 'scripts/editorial_revision.py'),
         '--root', str(root)],
        [sys.executable, '-B', str(root / 'scripts/editorial_long_cycle_figure.py'),
         '--article-root', str(root)],
    ]
    if check:
        for command in result:
            command.append('--check')
    return result


def refresh(article_root: Path, check: bool = False) -> None:
    root = article_root.resolve()
    for command in commands(root, check):
        subprocess.run(command, cwd=root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='Verify retained outputs without replacing them')
    args = parser.parse_args()
    refresh(args.article_root, args.check)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
