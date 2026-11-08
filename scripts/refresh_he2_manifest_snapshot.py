#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

from article_repo_layout import build_layout

MANIFEST_FILES = [
    'he2_bayesian_publication_manifest.md',
    'he2_bayesian_publication_manifest.csv',
    'he2_bayesian_publication_alignment.csv',
    'he2_bayesian_publication_inputs.csv',
    'he2_publication_parity_gate.md',
    'he2_publication_parity_gate.csv',
    'he2_publication_parity_gate_summary.json',
]

AUDIT_FILES = [
    'historical_support_audit.csv',
    'historical_support_audit.md',
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(src: Path, dst: Path) -> tuple[str, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst), sha256(dst)


def refresh_manifest_snapshot(layout, workflow_root: Path) -> None:
    src_root = workflow_root / 'reports' / 'he2_publication_manifest'
    dst_root = layout.he2_publication_freeze_dir
    dst_root.mkdir(parents=True, exist_ok=True)

    rows = []
    sums = []
    for name in MANIFEST_FILES:
        src = src_root / name
        dst = dst_root / name
        _, digest = copy_file(src, dst)
        sums.append(f'{digest}  {name}')
        rows.append([name, str(src), str(dst.relative_to(layout.root)), digest])

    (dst_root / 'README.md').write_text(
        '# HE2 Publication Freeze\n\n'
        'This artifact bundle freezes the workflow-side HE2 Bayesian publication manifest inside the revised article repo.\n\n'
        'Refresh script:\n'
        '- `scripts/refresh_he2_manifest_snapshot.py`\n\n'
        'Canonical workflow source:\n'
        f'- `{src_root}`\n'
    )
    with (dst_root / 'manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['filename', 'source_absolute_path', 'local_snapshot_path', 'sha256'])
        writer.writerows(rows)
    (dst_root / 'SHA256SUMS.txt').write_text('\n'.join(sorted(sums)) + '\n')


def refresh_historical_support_audit(layout, workflow_root: Path) -> None:
    src_root = workflow_root / 'reports' / 'he2_publication_manifest' / 'historical_support_audit_20260507'
    dst_root = layout.he2_historical_support_audit_dir
    dst_root.mkdir(parents=True, exist_ok=True)

    rows = []
    sums = []
    for name in AUDIT_FILES:
        src = src_root / name
        dst = dst_root / name
        _, digest = copy_file(src, dst)
        sums.append(f'{digest}  {name}')
        rows.append([name, str(src), str(dst.relative_to(layout.root)), digest])

    (dst_root / 'README.md').write_text(
        '# HE2 Historical Support Audit\n\n'
        'This artifact bundle mirrors the workflow-side HE2 historical-support audit used to document which publication rows use full historical support versus short-window support.\n\n'
        'Refresh script:\n'
        '- `scripts/refresh_he2_manifest_snapshot.py`\n\n'
        'Canonical workflow source:\n'
        f'- `{src_root}`\n'
    )
    with (dst_root / 'manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['filename', 'source_absolute_path', 'local_snapshot_path', 'sha256'])
        writer.writerows(rows)
    (dst_root / 'SHA256SUMS.txt').write_text('\n'.join(sorted(sums)) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh the local HE2 publication freeze and audit artifacts.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--workflow-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    workflow_root = args.workflow_root.resolve()
    layout = build_layout(article_root)
    layout.ensure_base_dirs()

    refresh_manifest_snapshot(layout, workflow_root)
    refresh_historical_support_audit(layout, workflow_root)
    print('Refreshed HE2 publication artifacts successfully.')


if __name__ == '__main__':
    main()
