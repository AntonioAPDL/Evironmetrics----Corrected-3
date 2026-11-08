#!/usr/bin/env python3
"""Refresh only the checked saved-output tables and article inventory guides."""
import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = args.article_root.resolve()
    command = [sys.executable, '-B', str(root/'scripts/no_refit_revision.py'),
               '--article-root', str(root)]
    if args.check:
        command.append('--check')
    subprocess.run(command, cwd=root, check=True)
    if not args.check:
        subprocess.run([sys.executable, '-B', str(root/'scripts/build_generated_asset_index.py'),
                        '--article-root', str(root)], cwd=root, check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
