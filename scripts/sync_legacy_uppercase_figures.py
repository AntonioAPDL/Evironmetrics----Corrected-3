#!/usr/bin/env python3
"""Copy canonical Figures/ assets to the optional lowercase compatibility tree.

The historical filename is retained for existing callers. Never deletes a tree:
only explicitly selected files (or the complete validated canonical inventory)
are replaced in figures/. Figures/ is always read-only to this helper.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

REQUIRED_CANONICAL_DIRS = [
    'manuscript', 'appendix_cutoff_panels', 'forecast_context_by_cutoff',
    'multivariate_synthesis_by_cutoff', 'reference_synthesis_by_cutoff',
]
METADATA_NAMES = {'README.md', 'mirror_manifest.csv'}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_canonical_tree(src_root: Path) -> None:
    missing = [rel for rel in REQUIRED_CANONICAL_DIRS if not (src_root / rel).is_dir()]
    if missing:
        raise FileNotFoundError(
            f'Cannot mirror incomplete canonical Figures tree under {src_root}: {", ".join(missing)}'
        )


def mirror_figures(article_root: Path, relative_paths: list[str] | None = None) -> list[dict[str, str | int]]:
    article_root = article_root.resolve()
    src_root = article_root / 'Figures'
    dst_root = article_root / 'figures'
    if src_root.is_symlink() or dst_root.is_symlink():
        raise ValueError('Figure roots must be real directories, not symlinks')
    if src_root.resolve() == dst_root.resolve():
        raise ValueError('Canonical and compatibility figure roots must differ')
    if not src_root.is_dir():
        raise FileNotFoundError(f'Missing canonical figures root: {src_root}')
    if relative_paths is None:
        validate_canonical_tree(src_root)
        paths = sorted(p.relative_to(src_root) for p in src_root.rglob('*')
                       if p.is_file() and p.relative_to(src_root).as_posix() not in METADATA_NAMES)
    else:
        paths = sorted({Path(rel) for rel in relative_paths})
    # Metadata is also a write target: a symlink here could redirect a mirror
    # manifest or README into the canonical tree.
    for name in METADATA_NAMES:
        metadata_target = dst_root / name
        if metadata_target.is_symlink() or not metadata_target.resolve().is_relative_to(dst_root.resolve()):
            raise ValueError(f'Compatibility metadata target escapes figures/: {metadata_target}')
    # Validate the entire requested batch before writing any file.
    for rel in paths:
        if rel.is_absolute() or '..' in rel.parts or rel.as_posix() in METADATA_NAMES:
            raise ValueError(f'Invalid compatibility mirror path: {rel}')
        src, dst = src_root / rel, dst_root / rel
        if not src.is_file() or src.is_symlink() or not src.resolve().is_relative_to(src_root.resolve()):
            raise ValueError(f'Invalid canonical source: {src}')
        if dst.is_symlink() or not dst.resolve().is_relative_to(dst_root.resolve()):
            raise ValueError(f'Compatibility target escapes figures/: {dst}')
    dst_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | int]] = []
    for rel in paths:
        src, dst = src_root / rel, dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({'relative_path': rel.as_posix(),
                     'canonical_source': (Path('Figures') / rel).as_posix(),
                     'compatibility_target': (Path('figures') / rel).as_posix(),
                     'sha256': sha256(dst), 'bytes': dst.stat().st_size})
    # A bounded refresh retains the manifest rows for other previously mirrored assets.
    manifest = dst_root / 'mirror_manifest.csv'
    previous: dict[str, dict[str, str | int]] = {}
    if relative_paths is not None and manifest.exists():
        with manifest.open(newline='', encoding='utf-8') as handle:
            previous = {r['relative_path']: r for r in csv.DictReader(handle)}
    previous.update({str(r['relative_path']): r for r in rows})
    fields = ['relative_path', 'canonical_source', 'compatibility_target', 'sha256', 'bytes']
    with manifest.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(previous[key] for key in sorted(previous))
    (dst_root / 'README.md').write_text(
        '# Lowercase Figure Compatibility Copies\n\n'
        'Canonical manuscript assets are in `Figures/`. These optional copies are\n'
        'refreshed one way by `scripts/sync_legacy_uppercase_figures.py`. Unmanaged\n'
        'files are preserved; only files listed in `mirror_manifest.csv` are managed.\n',
        encoding='utf-8')
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--relative-path', action='append', help='Canonical relative file to copy; repeat for a bounded refresh')
    args = parser.parse_args()
    rows = mirror_figures(args.article_root, args.relative_path)
    print(f'Mirrored {len(rows)} canonical Figures/ assets into optional figures/ compatibility copies')


if __name__ == '__main__':
    main()
