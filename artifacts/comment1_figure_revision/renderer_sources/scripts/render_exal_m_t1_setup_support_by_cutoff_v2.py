#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from canonical_climate_indices_lib import (
    canonical_paths as canonical_gdpc_paths,
    gdpc_factor_output_path,
    gdpc_metadata_output_path,
    load_config as load_yaml_config,
)

FIGURE_NAMES = [
    'usgs.png',
    'precip_soilmoisture_climatePC1_faceted_labeled.png',
    'retrospective_log_discharge_plot_faceted.png',
    'forecats.png',
]

HISTORY_DATE_KEYS = ('Date', 'date', 'time')
GDPC_CANONICAL_CONFIG = Path(__file__).resolve().parents[1] / 'config' / 'canonical_gdpc_master_covariate.yaml'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('w') as log:
        log.write('+ ' + ' '.join(cmd) + '\n')
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def canonical_gdpc_factor_csv() -> Path:
    cfg = load_yaml_config(GDPC_CANONICAL_CONFIG)
    paths = canonical_gdpc_paths(cfg)
    factor_path = gdpc_factor_output_path(cfg, paths)
    if not factor_path.exists():
        raise FileNotFoundError(
            f"Canonical GDPC factor is missing: {factor_path}. Run run_canonical_gdpc_master_pipeline.py first."
        )
    return factor_path


def canonical_gdpc_metadata_json() -> Path:
    cfg = load_yaml_config(GDPC_CANONICAL_CONFIG)
    paths = canonical_gdpc_paths(cfg)
    metadata_path = gdpc_metadata_output_path(cfg, paths)
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Canonical GDPC metadata is missing: {metadata_path}. Run run_canonical_gdpc_master_pipeline.py first."
        )
    return metadata_path


def axis_label_for_scale(plot_scale: str) -> str:
    if plot_scale == 'raw_cms':
        return 'River flow [m^3 s^-1]'
    if plot_scale == 'log1p_cms':
        return 'River flow [log(1 + x); x in m^3 s^-1]'
    if plot_scale == 'log_log1p_cms':
        raise ValueError('log_log1p_cms is not allowed in the current workflow; use log1p_cms.')
    return f'River flow [{plot_scale}]'


def choose_date_key(fieldnames: list[str]) -> str:
    for key in HISTORY_DATE_KEYS:
        if key in fieldnames:
            return key
    raise RuntimeError(f'Could not find a date column in {fieldnames}')


def first_last_retros_dates(path: Path) -> tuple[str, str]:
    rows = list(csv.DictReader(path.open(newline='')))
    if not rows:
        raise RuntimeError(f'No rows found in {path}')
    date_key = choose_date_key(list(rows[0].keys()))
    return rows[0][date_key], rows[-1][date_key]


def read_unique_dates(path: Path) -> list[dt.date]:
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f'No header found in {path}')
        date_key = choose_date_key(list(reader.fieldnames))
        values = sorted({dt.date.fromisoformat(row[date_key]) for row in reader if row.get(date_key)})
    if not values:
        raise RuntimeError(f'No valid dates found in {path}')
    return values


def daily_coverage(path: Path, requested_start: dt.date, requested_end: dt.date) -> dict:
    dates = read_unique_dates(path)
    observed = {d for d in dates if requested_start <= d <= requested_end}
    if not observed:
        raise RuntimeError(f'No dates from {requested_start} to {requested_end} found in {path}')
    available_start = min(observed)
    available_end = max(observed)
    expected_requested = {
        requested_start + dt.timedelta(days=offset)
        for offset in range((requested_end - requested_start).days + 1)
    }
    expected_available = {
        available_start + dt.timedelta(days=offset)
        for offset in range((available_end - available_start).days + 1)
    }
    missing_requested = sorted(expected_requested - observed)
    missing_available = sorted(expected_available - observed)
    return {
        'requested_start': requested_start.isoformat(),
        'requested_end': requested_end.isoformat(),
        'available_start': available_start.isoformat(),
        'available_end': available_end.isoformat(),
        'requested_window_days': len(expected_requested),
        'available_window_days': len(expected_available),
        'missing_days_requested_window': len(missing_requested),
        'missing_days_available_window': len(missing_available),
        'full_history_available': available_start <= requested_start and len(missing_requested) == 0,
    }


def build_policy_summary(entry: dict, bundle_meta: dict) -> dict:
    notes: list[str] = []
    gapfix = bundle_meta.get('processing', {}).get('gapfix')
    if gapfix and gapfix.get('applied'):
        notes.append(f"gapfix applied to {gapfix.get('source_id')} on {', '.join(gapfix.get('dates_filled', []))}")
    if entry['bundle_class'] == 'histfix_long_history_bundle':
        notes.append('histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff')
    return {
        'bundle_class': entry['bundle_class'],
        'nws_policy_summary': entry['nws_policy_summary'],
        'glofas_policy_summary': entry['glofas_policy_summary'],
        'notes': '; '.join(notes),
        'bundle_run_id': bundle_meta.get('run', {}).get('run_id') or bundle_meta.get('run', {}).get('bundle_kind', ''),
    }


def build_input_hash_rows(entry: dict, gdpc_factor_path: Path, gdpc_metadata_path: Path) -> list[dict]:
    selected = Path(entry['selected_run_root'])
    bundle = Path(entry['figure_bundle_root'])
    rows: list[dict] = []

    def add(label: str, path: Path) -> None:
        rows.append({
            'label': label,
            'path': str(path),
            'sha256': sha256(path),
            'bytes': path.stat().st_size,
        })

    add('selected_run_usgs_daily', selected / 'inputs/shared/usgs/usgs_daily.csv')
    add('selected_run_retros', selected / 'inputs/shared/retros/retros.csv')
    add('selected_run_nws_forecast', selected / 'inputs/shared/forecasts/nws_forecast.csv')
    add('selected_run_glofas_forecast', selected / 'inputs/shared/forecasts/glofas_forecast.csv')
    add('selected_run_cov_ppt', selected / 'inputs/shared/covariates/cov_01_PPT.csv')
    add('selected_run_cov_soil', selected / 'inputs/shared/covariates/cov_02_SOIL.csv')
    add('canonical_gdpc_factor', gdpc_factor_path)
    add('canonical_gdpc_build_metadata', gdpc_metadata_path)
    add('canonical_gdpc_config', GDPC_CANONICAL_CONFIG)
    add('selected_run_cov_features', selected / 'inputs/shared/covariates/covariate_features.csv')
    add('figure_bundle_meta', bundle / 'meta.yaml')
    if (bundle / 'snapshot_source_map.txt').exists():
        add('figure_bundle_snapshot_source_map', bundle / 'snapshot_source_map.txt')
    add('figure_bundle_retros_daily', bundle / 'inputs/retros_daily.csv')
    if (bundle / 'inputs/retros_source_lineage.csv').exists():
        add('figure_bundle_retros_source_lineage', bundle / 'inputs/retros_source_lineage.csv')
    add('figure_bundle_glofas_weighted_daily', bundle / 'inputs/glofas_weighted_daily.csv')
    add('figure_bundle_nws_weighted_daily', bundle / 'inputs/nws_weighted_daily.csv')
    add('figure_bundle_glofas_members', bundle / 'inputs/glofas_members.csv')
    add('figure_bundle_nws_members', bundle / 'inputs/nws_members.csv')
    if (bundle / 'retros.csv').exists():
        add('figure_bundle_retros_wide', bundle / 'retros.csv')
    if (bundle / 'glofas_forecast.csv').exists():
        add('figure_bundle_glofas_forecast', bundle / 'glofas_forecast.csv')
    if (bundle / 'nws_forecast.csv').exists():
        add('figure_bundle_nws_forecast', bundle / 'nws_forecast.csv')
    return rows


def build_retrospective_coverage(entry: dict, history_start: dt.date) -> dict:
    bundle = Path(entry['figure_bundle_root'])
    cutoff_date = dt.date.fromisoformat(entry['cutoff_date'])
    if entry['bundle_class'] == 'histfix_long_history_bundle':
        lineage_path = bundle / 'inputs' / 'retros_source_lineage.csv'
        return daily_coverage(lineage_path, history_start, cutoff_date)
    return daily_coverage(Path(entry['selected_run_root']) / 'inputs/shared/retros/retros.csv', history_start, cutoff_date)


def build_coverage_audit(entry: dict, history_start: dt.date, gdpc_factor_path: Path) -> dict:
    selected = Path(entry['selected_run_root'])
    cutoff_date = dt.date.fromisoformat(entry['cutoff_date'])
    usgs = daily_coverage(selected / 'inputs/shared/usgs/usgs_daily.csv', history_start, cutoff_date)
    ppt = daily_coverage(selected / 'inputs/shared/covariates/cov_01_PPT.csv', history_start, cutoff_date)
    soil = daily_coverage(selected / 'inputs/shared/covariates/cov_02_SOIL.csv', history_start, cutoff_date)
    gdpc = daily_coverage(gdpc_factor_path, history_start, cutoff_date)
    retros = build_retrospective_coverage(entry, history_start)
    return {
        'history_start_requested': history_start.isoformat(),
        'cutoff_date': cutoff_date.isoformat(),
        'usgs': usgs,
        'ppt': ppt,
        'soil': soil,
        'gdpc': gdpc,
        'retrospective': retros,
    }


def build_scale_contract(entry: dict, bundle_meta: dict, display_plot_scale: str, gdpc_factor_path: Path) -> dict:
    bundle_root = Path(entry['figure_bundle_root'])
    selected_root = Path(entry['selected_run_root'])
    selected_resolved = selected_root / 'resolved_config.yaml'
    selected_internal_scale = None
    if selected_resolved.exists():
        selected_meta = yaml.safe_load(selected_resolved.read_text())
        selected_internal_scale = (
            selected_meta.get('scale_contract', {}).get('analysis_scale_fit_internal')
            or selected_meta.get('scale_contract', {}).get('analysis_scale_post_internal')
        )
    contract = {
        'display_scale': display_plot_scale,
        'display_axis_label': axis_label_for_scale(display_plot_scale),
        'display_scale_basis': 'workflow_support_display_contract',
        'selected_run_internal_analysis_scale': selected_internal_scale,
        'figure_inputs': {
            'usgs_daily': {
                'path': str(selected_root / 'inputs/shared/usgs/usgs_daily.csv'),
                'storage_scale': 'raw_cms',
            },
            'covariate_ppt': {
                'path': str(selected_root / 'inputs/shared/covariates/cov_01_PPT.csv'),
                'storage_scale': 'native_covariate_scale',
            },
            'covariate_soil': {
                'path': str(selected_root / 'inputs/shared/covariates/cov_02_SOIL.csv'),
                'storage_scale': 'native_covariate_scale',
            },
            'covariate_gdpc': {
                'path': str(gdpc_factor_path),
                'storage_scale': 'dimensionless_canonical_gdpc_score',
                'note': 'Rendered from the canonical GDPC1 master factor and sliced to the cutoff-specific support window; workflow-facing cov_03_PCA.csv remains a compatibility alias for downstream fit consumers.',
            },
            'forecast_glofas_weighted': {
                'path': str(bundle_root / 'inputs/glofas_weighted_daily.csv'),
                'storage_scale': 'raw_cms',
            },
            'forecast_nws_weighted': {
                'path': str(bundle_root / 'inputs/nws_weighted_daily.csv'),
                'storage_scale': 'raw_cms',
            },
        },
        'current_rating_stage_references': {
            'interpretation': (
                'Approximate current-rating discharge equivalents of current NWS BTEC1 stage categories, '
                'computed from USGS 11160500 rating 40.0. These are operational magnitude references, '
                'not historical flood-stage classifications of daily-mean observations.'
            ),
            'rating_url': 'https://waterdata.usgs.gov/nwisweb/get_ratings?file_type=exsa&site_no=11160500',
            'nws_stage_url': 'https://www.cnrfc.noaa.gov/obsRiver_hc.php?id=BTEC1',
            'rating_id': '40.0',
            'rating_effective_begin': '2025-11-13 13:15 PST',
            'cfs_to_cms': 0.028316846592,
            'plotted_levels': [
                {'label': 'Minor reference', 'stage_ft': 16.50, 'discharge_cfs': 7402.38, 'log1p_cms': 5.350017858},
                {'label': 'Major reference', 'stage_ft': 21.76, 'discharge_cfs': 14895.73, 'log1p_cms': 6.046899494},
            ],
        },
    }
    if entry['bundle_class'] == 'histfix_long_history_bundle':
        contract['figure_inputs']['retrospective_history'] = {
            'path': str(bundle_root / 'inputs/retros_source_lineage.csv'),
            'storage_scale': 'raw_cms',
            'note': 'inputs/retros_daily.csv remains a legacy log1p bundle artifact and is not used directly for the rendered retrospective or staged forecast-context plots.',
        }
    else:
        contract['figure_inputs']['retrospective_history'] = {
            'path': str(bundle_root / 'inputs/retros_daily.csv'),
            'storage_scale': 'raw_cms',
            'note': 'selected source coverage follows the bundle selection policy recorded in meta.yaml.',
        }
    return contract


def write_cutoff_artifacts(
    entry: dict,
    bundle_meta: dict,
    history_start: dt.date,
    support_end: str,
    forecast_plot_pre_days: int,
    forecast_plot_post_days: int,
    display_plot_scale: str,
    gdpc_factor_path: Path,
    gdpc_metadata_path: Path,
    slug_root: Path,
) -> None:
    meta_dir = slug_root / 'metadata'
    review_dir = slug_root / 'review'
    figures_dir = slug_root / 'figures'
    meta_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    (meta_dir / 'source_model_run.txt').write_text(entry['selected_run_root'] + '\n')
    (meta_dir / 'source_figure_bundle.txt').write_text(entry['figure_bundle_root'] + '\n')
    (meta_dir / 'source_canonical_gdpc_factor.txt').write_text(str(gdpc_factor_path) + '\n')
    (meta_dir / 'source_canonical_gdpc_build_metadata.txt').write_text(str(gdpc_metadata_path) + '\n')
    (meta_dir / 'cutoff_entry.json').write_text(json.dumps(entry, indent=2) + '\n')

    forecast_start_date = bundle_meta['dates'].get('forecast_start_date')
    if not forecast_start_date:
        cutoff_date = bundle_meta['dates']['cutoff_date']
        forecast_start_date = str(dt.date.fromisoformat(cutoff_date) + dt.timedelta(days=1))
    cutoff_use = dt.date.fromisoformat(entry['cutoff_date'])
    plot_start = (cutoff_use - dt.timedelta(days=forecast_plot_pre_days)).isoformat()
    plot_end = (cutoff_use + dt.timedelta(days=forecast_plot_post_days)).isoformat()
    coverage_audit = build_coverage_audit(entry, history_start, gdpc_factor_path)

    support_window = {
        'support_start': history_start.isoformat(),
        'support_end': support_end,
        'history_start_requested': history_start.isoformat(),
        'retrospective_available_start': coverage_audit['retrospective']['available_start'],
        'retrospective_available_end': coverage_audit['retrospective']['available_end'],
        'plot_start': plot_start,
        'plot_end': plot_end,
        'forecast_start_date': forecast_start_date,
        'forecast_plot_pre_days': forecast_plot_pre_days,
        'forecast_plot_post_days': forecast_plot_post_days,
    }
    yaml.safe_dump(support_window, (meta_dir / 'support_window.yaml').open('w'), sort_keys=False)
    yaml.safe_dump(build_policy_summary(entry, bundle_meta), (meta_dir / 'policy_summary.yaml').open('w'), sort_keys=False)
    yaml.safe_dump(coverage_audit, (meta_dir / 'coverage_audit.yaml').open('w'), sort_keys=False)
    yaml.safe_dump(build_scale_contract(entry, bundle_meta, display_plot_scale, gdpc_factor_path), (meta_dir / 'scale_contract.yaml').open('w'), sort_keys=False)

    hash_rows = build_input_hash_rows(entry, gdpc_factor_path, gdpc_metadata_path)
    with (meta_dir / 'input_hashes.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['label', 'path', 'sha256', 'bytes'])
        for row in hash_rows:
            writer.writerow([row['label'], row['path'], row['sha256'], row['bytes']])

    with (review_dir / 'figure_manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['figure_name', 'path', 'sha256', 'bytes'])
        for name in FIGURE_NAMES:
            p = figures_dir / name
            writer.writerow([name, str(p), sha256(p), p.stat().st_size])


def main() -> None:
    parser = argparse.ArgumentParser(description='Render the corrected exAL-M-T1 setup/support figures by cutoff.')
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'config' / 'exal_m_t1_setup_support_by_cutoff_v2_20260507.json')
    parser.add_argument('--output-root', type=Path, default=None)
    parser.add_argument('--canonical-gdpc-factor', type=Path, default=None, help='Explicit existing read-only factor for isolated rendering.')
    parser.add_argument('--canonical-gdpc-metadata', type=Path, default=None, help='Explicit matching factor metadata for isolated rendering.')
    parser.add_argument('--slugs', nargs='*', default=None)
    parser.add_argument('--clean', action='store_true')
    parser.add_argument('--skip-review', action='store_true')
    parser.add_argument('--skip-validate', action='store_true')
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config = load_config(args.config.resolve())
    output_root = args.output_root.resolve() if args.output_root else Path(config['runtime_output_root']).resolve()
    wanted = set(args.slugs or [])
    history_start = dt.date.fromisoformat(config['history_start_date'])
    forecast_plot_pre_days = int(config.get('forecast_plot_pre_days', 28))
    forecast_plot_post_days = int(config.get('forecast_plot_post_days', 28))
    display_plot_scale = str(config.get('flow_figure_display_scale', 'log1p_cms'))
    gdpc_factor_path = args.canonical_gdpc_factor.resolve() if args.canonical_gdpc_factor else canonical_gdpc_factor_csv()
    gdpc_metadata_path = args.canonical_gdpc_metadata.resolve() if args.canonical_gdpc_metadata else canonical_gdpc_metadata_json()

    if args.clean and output_root.exists() and not wanted:
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    render_script = project_root / 'scripts' / 'render_setup_support_bundle_v2.R'
    py = sys.executable

    for entry in config['cutoffs']:
        if wanted and entry['slug'] not in wanted:
            continue
        slug_root = output_root / entry['slug']
        if args.clean and slug_root.exists():
            shutil.rmtree(slug_root)
        (slug_root / 'figures').mkdir(parents=True, exist_ok=True)
        (slug_root / 'logs').mkdir(parents=True, exist_ok=True)

        selected_retros = Path(entry['selected_run_root']) / 'inputs' / 'shared' / 'retros' / 'retros.csv'
        selected_support_start, support_end = first_last_retros_dates(selected_retros)
        if entry['bundle_class'] == 'short_window_synth_bundle' and selected_support_start != entry['support_start']:
            raise RuntimeError(
                f"Config support_start mismatch for {entry['slug']}: config={entry['support_start']} selected_run={selected_support_start}"
            )
        if support_end != entry['cutoff_date']:
            raise RuntimeError(
                f"Selected-run cutoff mismatch for {entry['slug']}: config cutoff={entry['cutoff_date']} selected_run retros end={support_end}"
            )

        cmd = [
            'Rscript', '--vanilla', str(render_script),
            '--project-root', str(project_root),
            '--selected-run-root', entry['selected_run_root'],
            '--figure-bundle-root', entry['figure_bundle_root'],
            '--bundle-class', entry['bundle_class'],
            '--output-dir', str((slug_root / 'figures').resolve()),
            '--history-start', history_start.isoformat(),
            '--cutoff-date', entry['cutoff_date'],
            '--forecast-plot-pre-days', str(forecast_plot_pre_days),
            '--forecast-plot-post-days', str(forecast_plot_post_days),
            '--display-plot-scale', display_plot_scale,
            '--canonical-gdpc-path', str(gdpc_factor_path),
        ]
        run(cmd, slug_root / 'logs' / 'render.log')

        bundle_meta = yaml.safe_load((Path(entry['figure_bundle_root']) / 'meta.yaml').read_text())
        write_cutoff_artifacts(
            entry=entry,
            bundle_meta=bundle_meta,
            history_start=history_start,
            support_end=support_end,
            forecast_plot_pre_days=forecast_plot_pre_days,
            forecast_plot_post_days=forecast_plot_post_days,
            display_plot_scale=display_plot_scale,
            gdpc_factor_path=gdpc_factor_path,
            gdpc_metadata_path=gdpc_metadata_path,
            slug_root=slug_root,
        )

    review_script = project_root / 'scripts' / 'build_exal_m_t1_setup_support_v2_review.py'
    validate_script = project_root / 'scripts' / 'validate_exal_m_t1_setup_support_v2.py'
    if not args.skip_review:
        subprocess.run([py, str(review_script), '--output-root', str(output_root)], check=True)
    if not args.skip_validate:
        validate_cmd = [py, str(validate_script), '--config', str(args.config.resolve()), '--output-root', str(output_root)]
        if wanted:
            validate_cmd.extend(['--slugs', *sorted(wanted)])
        subprocess.run(validate_cmd, check=True)

    readme = output_root / 'README.md'
    readme.write_text(
        '# exAL-M-T1 setup/support figures by cutoff (v2)\n\n'
        'This runtime family renders the corrected cutoff-specific setup/input/support figures from the CRPS-linked exAL-M-T1 run roots and the authoritative forecats/histfix bundles.\n\n'
        f'Config: `{args.config.resolve()}`\n\n'
        f'Canonical GDPC factor: `{gdpc_factor_path}`\n\n'
        f'Flow-figure display scale: `{display_plot_scale}`\n\n'
        'Review outputs:\n'
        '- `review/REVIEW.md`\n'
        '- `review/gallery.html`\n'
        '- `review/figure_manifest.csv`\n'
    )
    print(f'Rendered exAL-M-T1 setup/support v2 family at {output_root}')


if __name__ == '__main__':
    main()
