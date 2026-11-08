#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from article_repo_layout import build_layout

FIGURE_NAMES = [
    'usgs.png',
    'precip_soilmoisture_climatePC1_faceted_labeled.png',
    'retrospective_log_discharge_plot_faceted.png',
    'forecats.png',
]


def main() -> None:
    parser = argparse.ArgumentParser(description='Record which representative setup/support cutoff is used for the manuscript-facing setup figures.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--slug', default='20221225_exal_m_t1')
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    bundle_root = layout.five_cutoff_setup_support_dir / args.slug
    figures_root = bundle_root / 'figures'
    if not figures_root.exists():
        raise FileNotFoundError(f'Missing setup/support figure bundle: {figures_root}')

    selection_root = layout.representative_setup_selection_dir
    selection_root.mkdir(parents=True, exist_ok=True)
    meta = json.loads((bundle_root / 'metadata' / 'cutoff_entry.json').read_text())
    selection = {
        'selected_slug': args.slug,
        'selected_cutoff_date': meta['cutoff_date'],
        'selected_run_root': meta['selected_run_root'],
        'selected_figure_bundle_root': str(bundle_root.relative_to(article_root)),
        'bundle_class': meta['bundle_class'],
        'representative_figures': FIGURE_NAMES,
    }
    (selection_root / 'selection_manifest.json').write_text(json.dumps(selection, indent=2) + '\n')
    (selection_root / 'README.md').write_text(
        '# Representative Setup Selection\n\n'
        'This report records which cutoff-specific setup/support artifact bundle is currently used as the representative manuscript source for Figures 1-4.\n\n'
        'Refresh path:\n'
        '- `scripts/promote_setup_support_v2_to_disc.py`\n'
    )
    print(f'Recorded representative setup/support selection for {args.slug}')


if __name__ == '__main__':
    main()
