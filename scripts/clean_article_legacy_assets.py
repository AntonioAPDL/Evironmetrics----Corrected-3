#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from article_asset_manifest import load_manifest
from article_repo_layout import build_layout

LEGACY_ROOT_PATHS = [
    'DISC',
    'generated',
    'ARTICLE_GENERATED_ASSET_MANIFEST.json',
    'EXAL_M_T1_ARTIFACT_RUN_MAP.md',
    'EXAL_M_T1_RELAUNCH_CHECKLIST.md',
    'FIGURE_TABLE_PROVENANCE.md',
    'MANUSCRIPT_REVISION_CHECKLIST.md',
    'ARTICLE_REORG_AND_RENAME_PLAN_20260509.md',
    'ARTICLE_REORG_PATH_CROSSWALK_20260509.csv',
]

LEGACY_SCRIPTS = [
    'scripts/refresh_local_provenance_bundles.py',
    'scripts/refresh_setup_support_by_cutoff.py',
    'scripts/build_setup_support_by_cutoff_review.py',
]


def remove_path(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def build_report(layout, removed_paths: list[str]) -> None:
    manifest = load_manifest(layout.root)
    expected_figures = sorted(fig['manuscript_path'] for fig in manifest['figures'])
    retained_artifacts = sorted(p.name for p in layout.artifacts_dir.iterdir() if p.is_dir())
    retained_reports = sorted(p.name for p in layout.reports_dir.iterdir() if p.is_dir())

    report_dir = layout.manuscript_asset_review_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        'article_root': str(layout.root),
        'canonical_manuscript_figures': expected_figures,
        'removed_legacy_paths': removed_paths,
        'retained_artifact_families': retained_artifacts,
        'retained_report_families': retained_reports,
    }
    (report_dir / 'article_repo_cleanup_audit.json').write_text(json.dumps(payload, indent=2) + '\n')

    md: list[str] = []
    md.append('# Article Repo Cleanup Audit\n\n')
    md.append('This report records the cleanup that removes retired article-side figure/table directories and old naming layers after the repository reorganization.\n\n')
    md.append('## Canonical manuscript-facing figures\n\n')
    for rel in expected_figures:
        md.append(f'- `{rel}`\n')
    md.append('\n## Removed legacy paths\n\n')
    if removed_paths:
        for rel in removed_paths:
            md.append(f'- `{rel}`\n')
    else:
        md.append('- None\n')
    md.append('\n## Retained artifact families\n\n')
    for fam in retained_artifacts:
        md.append(f'- `artifacts/{fam}`\n')
    md.append('\n## Retained report families\n\n')
    for fam in retained_reports:
        md.append(f'- `reports/{fam}`\n')
    md.append('\n## Current cleanup contract\n\n')
    md.append('1. `Figures/manuscript/` should contain only the figure files named in `MANUSCRIPT_ASSET_MANIFEST.json`.\n')
    md.append('2. The old `DISC/` and `generated/` directory trees should remain absent.\n')
    md.append('3. Refresh through `scripts/refresh_all_generated_assets.py`, which now re-applies this cleanup automatically.\n')
    (report_dir / 'ARTICLE_REPO_CLEANUP_AUDIT.md').write_text(''.join(md), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Prune stale article-side directories and retired naming layers after the repository reorganization.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)

    removed_paths: list[str] = []
    for rel in LEGACY_ROOT_PATHS:
        if remove_path(article_root / rel):
            removed_paths.append(rel)
    for rel in LEGACY_SCRIPTS:
        if remove_path(article_root / rel):
            removed_paths.append(rel)

    pycache = article_root / 'scripts' / '__pycache__'
    if remove_path(pycache):
        removed_paths.append('scripts/__pycache__')

    build_report(layout, removed_paths)
    print(f'Removed {len(removed_paths)} legacy paths.')


if __name__ == '__main__':
    main()
