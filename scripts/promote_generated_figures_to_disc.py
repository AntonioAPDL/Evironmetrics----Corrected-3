#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from article_asset_manifest import load_manifest, manifest_path
from article_repo_layout import build_layout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description='Promote manuscript figures into the advisor-facing manuscript figure directory from the source-controlled manifest.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    layout.ensure_base_dirs()
    manifest = load_manifest(article_root)
    manuscript_root = layout.manuscript_figures_dir
    out_root = layout.manuscript_figure_selection_dir
    out_root.mkdir(parents=True, exist_ok=True)

    expected = {Path(fig['manuscript_path']).name for fig in manifest['figures']}
    for stale in sorted(manuscript_root.iterdir()):
        if stale.is_file() and stale.name not in expected:
            stale.unlink()

    rows: list[dict[str, object]] = []
    for fig in manifest['figures']:
        src = article_root / fig['source_path']
        if not src.exists():
            raise FileNotFoundError(f'Missing generated source for {fig["label"]}: {src}')
        dst = article_root / fig['manuscript_path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({
            'label': fig['label'],
            'manuscript_path': fig['manuscript_path'],
            'category': fig['category'],
            'role': fig['role'],
            'source_class': fig['source_class'],
            'current_model_output_wired': bool(fig['current_model_output_wired']),
            'source_path': fig['source_path'],
            'sha256': sha256(dst),
            'note': fig['note'],
        })

    selection = {
        'manifest_path': str(manifest_path(article_root).relative_to(article_root)),
        'manuscript_figures_dir': str(manuscript_root.relative_to(article_root)),
        'figures': rows,
    }
    (out_root / 'selection_manifest.json').write_text(json.dumps(selection, indent=2) + '\n')
    (out_root / 'README.md').write_text(
        '# Manuscript Figure Selection\n\n'
        'This report records the exact artifact-bundle sources currently promoted into the manuscript-facing figure directory.\n\n'
        'Refresh path:\n'
        '- `scripts/promote_generated_figures_to_disc.py`\n\n'
        'The source-controlled selection rules live in:\n'
        f'- `{manifest_path(article_root).name}`\n'
    )
    print(f'Promoted {len(rows)} manuscript figures into {manuscript_root}')


if __name__ == '__main__':
    main()
