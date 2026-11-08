#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

REQUIRED_CANONICAL_DIRS = [
    'manuscript',
    'appendix_cutoff_panels',
    'forecast_context_by_cutoff',
    'multivariate_synthesis_by_cutoff',
    'reference_synthesis_by_cutoff',
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_canonical_tree(src_root: Path) -> None:
    missing = [rel for rel in REQUIRED_CANONICAL_DIRS if not (src_root / rel).exists()]
    if missing:
        joined = ', '.join(missing)
        raise FileNotFoundError(
            f'Cannot mirror incomplete canonical figures tree. Missing lowercase directories under {src_root}: {joined}'
        )


def main() -> None:
    parser = argparse.ArgumentParser(description='Mirror canonical lowercase figures/ into the legacy uppercase Figures/ fallback tree.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    src_root = article_root / 'figures'
    dst_root = article_root / 'Figures'
    if not src_root.exists():
        raise FileNotFoundError(f'Missing canonical figures root: {src_root}')
    validate_canonical_tree(src_root)

    if dst_root.exists():
        for child in dst_root.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                shutil.rmtree(child)
    dst_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int]] = []
    for src in sorted(p for p in src_root.rglob('*') if p.is_file()):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({
            'relative_path': str(rel),
            'lowercase_source': str(src.relative_to(article_root)),
            'uppercase_target': str(dst.relative_to(article_root)),
            'sha256': sha256(dst),
            'bytes': dst.stat().st_size,
        })

    (dst_root / 'README.md').write_text(
        '# Legacy Uppercase Figures Mirror\n\n'
        'This tree mirrors the canonical lowercase `figures/` directory for legacy tooling and compile-time fallback paths.\n\n'
        'Authoritative refresh path:\n'
        '- `scripts/refresh_all_generated_assets.py`\n'
        '- `scripts/sync_legacy_uppercase_figures.py`\n',
        encoding='utf-8',
    )

    with (dst_root / 'mirror_manifest.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    print(f'Mirrored {len(rows)} figure files from {src_root} into {dst_root}')


if __name__ == '__main__':
    main()
