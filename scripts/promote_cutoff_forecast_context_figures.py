#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from article_repo_layout import build_layout, CUTOFF_FORECAST_CONTEXT_FILENAMES


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_simple_yaml(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, value = line.split(':', 1)
        out[key.strip()] = value.strip().strip("'").strip('"')
    return out


def write_readme(out_dir: Path) -> None:
    text = """# Forecast Context By Cutoff

This directory contains advisor-facing copies of the five cutoff-specific
forecast-context figures generated from the canonical setup/support bundles.

These files are not the primary manuscript figure path. The manuscript uses the
representative December 25, 2022 figure in `Figures/manuscript/`, while this
folder preserves the corresponding `forecats.png` view for every validated
cutoff in a consistent, readable naming scheme.

Primary sources:
- `artifacts/five_cutoff_setup_support/<cutoff>/figures/forecats.png`
- `manifest.csv` in this same directory for the source/target mapping
"""
    (out_dir / 'README.md').write_text(text, encoding='utf-8')


def mirror_to_lowercase(article_root: Path, uppercase_dir: Path) -> None:
    lowercase_dir = article_root / 'figures' / uppercase_dir.name
    lowercase_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(path for path in uppercase_dir.iterdir() if path.is_file()):
        target = lowercase_dir / source.name
        if source.name == 'manifest.csv':
            text = source.read_text(encoding='utf-8').replace('Figures/', 'figures/')
            target.write_text(text, encoding='utf-8')
        else:
            shutil.copy2(source, target)


def main() -> None:
    parser = argparse.ArgumentParser(description='Promote cutoff-specific forecast-context figures into advisor-facing figure paths.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    layout = build_layout(args.article_root.resolve())
    layout.ensure_base_dirs()
    out_dir = layout.cutoff_forecast_context_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str | int]] = []
    expected_targets = set(CUTOFF_FORECAST_CONTEXT_FILENAMES.values()) | {'README.md', 'manifest.csv'}

    for slug, target_name in sorted(CUTOFF_FORECAST_CONTEXT_FILENAMES.items()):
        source = layout.five_cutoff_setup_support_dir / slug / 'figures' / 'forecats.png'
        if not source.exists():
            raise FileNotFoundError(f'Missing source forecast-context figure: {source}')

        cutoff_entry_path = layout.five_cutoff_setup_support_dir / slug / 'metadata' / 'cutoff_entry.json'
        support_window_path = layout.five_cutoff_setup_support_dir / slug / 'metadata' / 'support_window.yaml'
        cutoff_entry = json.loads(cutoff_entry_path.read_text(encoding='utf-8')) if cutoff_entry_path.exists() else {}
        support_window = parse_simple_yaml(support_window_path) if support_window_path.exists() else {}

        target = out_dir / target_name
        shutil.copy2(source, target)
        rows.append({
            'slug': slug,
            'cutoff_date': cutoff_entry.get('cutoff_date', ''),
            'bundle_class': cutoff_entry.get('bundle_class', ''),
            'forecast_start_date': support_window.get('forecast_start_date', ''),
            'plot_start': support_window.get('plot_start', ''),
            'plot_end': support_window.get('plot_end', ''),
            'source_path': str(source.relative_to(layout.root)),
            'target_path': str(target.relative_to(layout.root)),
            'sha256': sha256sum(target),
            'bytes': target.stat().st_size,
        })

    for child in out_dir.iterdir():
        if child.name not in expected_targets:
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)

    manifest_path = out_dir / 'manifest.csv'
    with manifest_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                'slug',
                'cutoff_date',
                'bundle_class',
                'forecast_start_date',
                'plot_start',
                'plot_end',
                'source_path',
                'target_path',
                'sha256',
                'bytes',
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    write_readme(out_dir)
    mirror_to_lowercase(layout.root, out_dir)
    print(f'Promoted {len(rows)} cutoff forecast-context figures into {out_dir}')


if __name__ == '__main__':
    main()
