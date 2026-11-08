#!/usr/bin/env python3
"""Preserve reviewed presentation assets across refreshes of frozen run outputs.

Numerical caches/CSVs and frozen selected run IDs must still match the revision.
All checks finish before any restoration. A changed or missing source requires a
new render/review; this module never substitutes the previous run's pictures.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

REGISTRY = Path('artifacts/comment1_figure_revision/registry.json')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Presentation path escapes article root: {relative}')
    return path


def verify_comment1_figure_revision(article_root: Path) -> dict | None:
    path = article_root / REGISTRY
    if not path.exists():
        return None
    registry = json.loads(path.read_text())
    freeze = article_root / 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv'
    with freeze.open(newline='') as f:
        selected = {(r['cutoff'].replace('-', ''), r['manuscript_label']): r.get('artifact_run_id') or r['run_id'] for r in csv.DictReader(f)}
    for row in registry['selected_runs']:
        key = (row['cutoff'], row['label'])
        if selected.get(key) != row['run_id']:
            raise ValueError(f'Presentation revision does not match current selected run: {key}')
    for row in registry['numeric_inputs']:
        source = Path(row['source'])
        if not source.is_file() or sha256(source) != row['sha256']:
            raise ValueError(f'Presentation revision input changed or is missing: {source}')
    for row in registry.get('article_numeric_inputs', []):
        source = contained(article_root, row['path'])
        if not source.is_file() or sha256(source) != row['sha256']:
            raise ValueError(f'Article numerical input changed or is missing: {source}')
    for row in registry['restore']:
        source = contained(article_root / REGISTRY.parent, row['stored'])
        target = contained(article_root, row['target'])
        if source.is_symlink() or not source.is_file() or sha256(source) != row['sha256']:
            raise ValueError(f'Reviewed presentation archive changed: {source}')
        if target.is_symlink():
            raise ValueError(f'Refusing symlink presentation target: {target}')
    return registry


def reapply_comment1_figure_revision(article_root: Path) -> int:
    registry = verify_comment1_figure_revision(article_root)
    if registry is None:
        return 0
    for row in registry['restore']:
        source = contained(article_root / REGISTRY.parent, row['stored'])
        target = contained(article_root, row['target'])
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='.comment1-', dir=target.parent)
        os.close(fd)
        try:
            shutil.copy2(source, temp)
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    return len(registry['restore'])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    root = args.article_root.resolve()
    if args.check:
        registry = verify_comment1_figure_revision(root)
        print('No presentation revision registered.' if registry is None else f'Presentation revision validated: {len(registry["restore"])} assets/metadata files.')
    else:
        print(f'Reapplied {reapply_comment1_figure_revision(root)} reviewed presentation assets/metadata files.')


if __name__ == '__main__':
    main()
