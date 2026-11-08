#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from article_runtime_bindings import binding_as_path, load_runtime_bindings
from article_repo_layout import build_layout
from exal_m_t1_authoritative import load_authoritative_five_run_specs

REPRESENTATIVE_FILES = [
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.pdf',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.pdf',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png',
    'exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv',
    'exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv',
    'figure_manifest.csv',
    'publication_figure_manifest.csv',
    'publication_style_used.yaml',
    'tables/covariate_effects_summary.csv',
    'tables/covariate_effects_summary.tex',
    'tables/crps_forecast_per_time.csv',
    'tables/crps_forecast_summary.csv',
    'tables/gamma_summary.csv',
    'tables/gamma_summary.tex',
    'tables/posterior_table_exports_manifest.csv',
    'tables/posterior_table_exports_README.md',
    'tables/sigma_summary.csv',
    'tables/sigma_summary.tex',
]

ALIAS_FIGURES = {
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png': 'representative_synthesis_multivariate.png',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png': 'representative_synthesis_multivariate_with_reference_ensembles.png',
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return sha256(dst)


def resolve_output_root(runtime_root: Path, run_id: str, cutoff_code: str) -> Path:
    output_root = runtime_root / 'runs' / run_id / 'post' / 'outputs' / run_id
    if output_root.exists():
        return output_root

    runs_root = runtime_root / 'runs'
    if not runs_root.exists():
        return output_root

    matches = []
    for run_root in sorted(runs_root.glob(f'multimodel_{cutoff_code}_*exdqlm_multivar_keep*')):
        candidate = run_root / 'post' / 'outputs' / run_root.name
        if candidate.exists():
            matches.append(candidate)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = '\n  '.join(str(path) for path in matches)
        raise RuntimeError(f'Ambiguous retained output roots for cutoff {cutoff_code} under {runtime_root}:\n  {joined}')
    return output_root


def run_root_from_output_root(output_root: Path) -> Path:
    return output_root.parents[2]


def read_mean_crps(path: Path) -> str:
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    target = next((r for r in rows if r.get('model_id') == 'exdqlm_multivar_synth_keep'), rows[0])
    return target['mean_crps']


def refresh_five_run_sources(layout, runtime_root: Path, five_run_specs: list[dict[str, str]]) -> None:
    bundle_root = layout.five_cutoff_crps_validation_dir
    bundle_root.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    sums = []

    for spec in five_run_specs:
        output_root_raw = str(spec.get('runtime_output_root') or '').strip()
        output_root = Path(output_root_raw) if output_root_raw else Path('__missing_runtime_output_root__')
        if not output_root_raw or not output_root.exists():
            output_root = resolve_output_root(runtime_root, spec['run_id'], spec['cutoff'].replace('-', ''))
        run_root = run_root_from_output_root(output_root)
        resolved_run_id = output_root.name
        target_dir = bundle_root / spec['slug']
        target_dir.mkdir(parents=True, exist_ok=True)

        src_summary = run_root / 'report' / 'summary.json'
        src_compare = run_root / 'validate' / 'compare_report.json'
        src_crps = output_root / 'tables' / 'crps_forecast_summary.csv'
        src_crps_per_time = output_root / 'tables' / 'crps_forecast_per_time.csv'

        out_summary = target_dir / 'summary.json'
        out_compare = target_dir / 'compare_report.json'
        out_crps = target_dir / 'crps_forecast_summary.csv'
        out_crps_per_time = target_dir / 'crps_forecast_per_time.csv'

        for src, dst in (
            (src_summary, out_summary),
            (src_compare, out_compare),
            (src_crps, out_crps),
            (src_crps_per_time, out_crps_per_time),
        ):
            digest = copy_file(src, dst)
            sums.append(f'{digest}  {spec["slug"]}/{dst.name}')

        manifest_rows.append([
            spec['slug'],
            spec['cutoff'],
            resolved_run_id,
            spec['published_crps'],
            read_mean_crps(out_crps),
            str(run_root),
            str(src_summary),
            str(src_compare),
            str(src_crps),
            str(src_crps_per_time),
            str(out_summary.relative_to(layout.root)),
            str(out_compare.relative_to(layout.root)),
            str(out_crps.relative_to(layout.root)),
            str(out_crps_per_time.relative_to(layout.root)),
        ])

    (bundle_root / 'README.md').write_text(
        '# Five-Cutoff CRPS Validation Sources\n\n'
        'This artifact bundle freezes the five current publication-authority `exAL-M-T1` run roots used by the revised article benchmark table refresh.\n\n'
        'Refresh script:\n'
        '- `scripts/refresh_exal_m_t1_generated_assets.py`\n\n'
        'For each cutoff, the local freeze contains:\n'
        '- `summary.json`\n'
        '- `compare_report.json`\n'
        '- `crps_forecast_summary.csv`\n\n'
        '- `crps_forecast_per_time.csv`\n\n'
        'These files are copied from the current HE2 publication freeze. Some cutoffs may remain on the original canonical-grid roots, while promoted cutoffs point to clean replay roots.\n'
    )

    with (bundle_root / 'manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([
            'slug', 'cutoff', 'run_id', 'published_crps', 'replay_mean_crps', 'runtime_run_root',
            'source_summary_json', 'source_compare_report', 'source_crps_summary', 'source_crps_per_time',
            'local_summary_json', 'local_compare_report', 'local_crps_summary', 'local_crps_per_time'
        ])
        writer.writerows(manifest_rows)
    (bundle_root / 'SHA256SUMS.txt').write_text('\n'.join(sorted(sums)) + '\n')


def refresh_representative_bundle(layout, runtime_root: Path, five_run_specs: list[dict[str, str]]) -> None:
    spec = next(s for s in five_run_specs if s['slug'] == '20221225_exal_m_t1')
    output_root_raw = str(spec.get('runtime_output_root') or '').strip()
    output_root = Path(output_root_raw) if output_root_raw else Path('__missing_runtime_output_root__')
    if not output_root_raw or not output_root.exists():
        output_root = resolve_output_root(runtime_root, spec['run_id'], spec['cutoff'].replace('-', ''))
    run_root = run_root_from_output_root(output_root)
    resolved_run_id = output_root.name
    bundle_root = layout.representative_selected_model_dir
    bundle_root.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    sums = []
    for rel in REPRESENTATIVE_FILES:
        src = output_root / rel
        dst = bundle_root / Path(rel).name
        digest = copy_file(src, dst)
        sums.append(f'{digest}  {dst.name}')
        manifest_rows.append([rel, dst.name, str(src), str(dst.relative_to(layout.root)), digest])

    for src_name, alias_name in ALIAS_FIGURES.items():
        src = bundle_root / src_name
        dst = bundle_root / alias_name
        shutil.copy2(src, dst)
        sums.append(f'{sha256(dst)}  {alias_name}')
        manifest_rows.append([src_name, alias_name, str(src), str(dst.relative_to(layout.root)), sha256(dst)])

    for src, dst_name in ((run_root / 'report' / 'summary.json', 'summary.json'), (run_root / 'validate' / 'compare_report.json', 'compare_report.json')):
        digest = copy_file(src, bundle_root / dst_name)
        sums.append(f'{digest}  {dst_name}')
        manifest_rows.append([str(src.relative_to(run_root)), dst_name, str(src), str((bundle_root / dst_name).relative_to(layout.root)), digest])

    metadata = {
        'cutoff': spec['cutoff'],
        'run_id': resolved_run_id,
        'runtime_run_root': str(run_root),
        'runtime_output_root': str(output_root),
        'published_crps': spec['published_crps'],
        'replay_mean_crps': read_mean_crps(bundle_root / 'crps_forecast_summary.csv'),
    }
    (bundle_root / 'bundle_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')

    (bundle_root / 'README.md').write_text(
        '# Representative Selected Model: 2022-12-25\n\n'
        'This artifact bundle freezes the authoritative representative `2022-12-25 exAL-M-T1` outputs used by the revised article.\n\n'
        'Refresh script:\n'
        '- `scripts/refresh_exal_m_t1_generated_assets.py`\n\n'
        'Included content:\n'
        '- corrected selected-model synthesis figures\n'
        '- quantile and sample exports\n'
        '- CRPS summaries\n'
        '- posterior table exports\n'
        '- figure manifests\n'
        '- report and validation summaries\n'
    )
    with (bundle_root / 'manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['source_relative_path', 'local_filename', 'source_absolute_path', 'local_bundle_path', 'sha256'])
        writer.writerows(manifest_rows)
    (bundle_root / 'SHA256SUMS.txt').write_text('\n'.join(sorted(sums)) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh article-side exAL-M-T1 generated asset bundles.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--runtime-root', type=Path)
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    bindings = load_runtime_bindings(article_root)
    runtime_root = (
        args.runtime_root.resolve()
        if args.runtime_root is not None
        else binding_as_path(bindings, 'exal_m_t1', 'keep_runtime_root')
    )
    layout = build_layout(article_root)
    layout.ensure_base_dirs()
    five_run_specs = load_authoritative_five_run_specs(
        article_root,
        args.runtime_root.resolve() if args.runtime_root is not None else None,
    )
    refresh_five_run_sources(layout, runtime_root, five_run_specs)
    refresh_representative_bundle(layout, runtime_root, five_run_specs)
    print('Refreshed exAL-M-T1 generated asset bundles successfully.')


if __name__ == '__main__':
    main()
