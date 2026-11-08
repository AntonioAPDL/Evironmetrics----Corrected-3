#!/usr/bin/env python3
"""Render the seven comment-1 figures from copied, frozen publication inputs.

Only output_root is written. The frozen snapshot supplies immutable selection;
no model is fitted, no heavy fit object is restored, and no runtime is modified.
See render_manifest.json for input hashes, commands, and article asset mapping.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot', required=True, type=Path)
    p.add_argument('--output-root', required=True, type=Path)
    p.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--cutoffs', nargs='+', default=['20210123', '20211112', '20211221', '20220511', '20221225'])
    p.add_argument('--skip-context', action='store_true', help='Proof stage only; final family includes the context figure.')
    args = p.parse_args()
    root, out = args.project_root.resolve(), args.output_root.resolve()
    snapshot = json.loads(args.snapshot.read_text())
    expected_inputs = {str(Path(row['path']).resolve()): row['sha256'] for row in snapshot['files'] if row.get('exists') and row.get('sha256')}
    # Validate the complete selected numerical input set before any copy/render.
    selected_rows = [row for row in snapshot['selected_runs'] if row['cutoff'] in args.cutoffs and
                     (row['label'] == 'exAL-M-T1' or row['cutoff'] == '20221225')]
    for row in selected_rows:
        source = Path(row['outputs_dir'])
        post, mid = source.parents[1], row['model_id']
        required = [source / f'{mid}_cutoff_window_{tail}' for tail in ['quantiles.csv', 'sample_subset.csv']]
        required += [post / 'inputs' / name for name in ['nws_post_adapter.csv', 'glofas_post_adapter.csv', 'retros_post_adapter.csv']]
        cache_names = ([f'{mid}__mode-keep__synth_multivar_{segment}_log1p.rds' for segment in ['hist', 'forecast']]
                       if row['label'] == 'exAL-M-T1' else [f'synth_univar_{segment}_log1p.rds' for segment in ['hist', 'forecast']])
        required += [post / 'cache' / name for name in cache_names]
        for source_input in required:
            expected = expected_inputs.get(str(source_input.resolve()))
            if expected is None or not source_input.is_file() or digest(source_input) != expected:
                p.error(f'Selected numeric input is missing or differs from frozen snapshot: {source_input}')
    # Refuse accidental writes below any authoritative research run.
    for r in snapshot['selected_runs']:
        if out.is_relative_to(Path(r['artifact_run_root']).resolve()):
            p.error('output-root must be separate from every authoritative run')
    if out.exists():
        p.error('output-root must be new; use a distinct proof directory')
    out.mkdir(parents=True)
    records, commands, assets = [], [], []
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')

    def copy_input(src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        sha = digest(src)
        expected = expected_inputs.get(str(src.resolve()))
        if expected is not None and sha != expected:
            raise ValueError(f'Input differs from frozen snapshot before copy: {src}')
        shutil.copy2(src, dst)
        assert digest(dst) == sha
        records.append({'source': str(src), 'copy': str(dst), 'sha256': sha, 'bytes': src.stat().st_size})

    def run(cmd: list[str], log: Path) -> None:
        commands.append(cmd)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('w') as f:
            result = subprocess.run(cmd, cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'render failed: see {log}')

    for r in snapshot['selected_runs']:
        if r['cutoff'] not in args.cutoffs or (r['label'] == 'exAL-U-T1' and r['cutoff'] != '20221225'):
            continue
        source = Path(r['outputs_dir'])
        post = source.parents[1]
        dest_post = out / 'runs' / r['run_id'] / 'post'
        dest = dest_post / 'outputs' / r['run_id']
        mid = r['model_id']
        for suffix in ['cutoff_window_quantiles.csv', 'cutoff_window_sample_subset.csv']:
            copy_input(source / f'{mid}_{suffix}', dest / f'{mid}_{suffix}')
        cache_names = ([f'{mid}__mode-keep__synth_multivar_{segment}_log1p.rds' for segment in ['hist', 'forecast']]
                       if r['label'] == 'exAL-M-T1' else [f'synth_univar_{segment}_log1p.rds' for segment in ['hist', 'forecast']])
        for name in cache_names:
            copy_input(post / 'cache' / name, dest_post / 'cache' / name)
        for name in ['nws_post_adapter.csv', 'glofas_post_adapter.csv', 'retros_post_adapter.csv']:
            copy_input(post / 'inputs' / name, dest_post / 'inputs' / name)
        # A minimal rebased manifest cannot accidentally point its writes to runtime.
        with (dest / 'figure_manifest.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['model_id', 'plot_type', 'path', 'source_run', 'note'])
            w.writeheader()
            w.writerow(dict(model_id=mid, plot_type='cutoff_window_posterior_samples',
                            path=str(dest / f'{mid}_cutoff_window_posterior_samples.png'),
                            source_run=r['run_id'], note='copied immutable publication selection; comment-1 display revision'))
        cmd = ['Rscript', '--vanilla', str(root / 'scripts/render_focus_publication_posterior_plot.R'),
               '--outputs-dir', str(dest), '--model-id', mid,
               '--hist-cache', str(dest_post / 'cache' / cache_names[0]),
               '--forecast-cache', str(dest_post / 'cache' / cache_names[1]),
               '--nws-path', str(dest_post / 'inputs/nws_post_adapter.csv'),
               '--glofas-path', str(dest_post / 'inputs/glofas_post_adapter.csv'),
               '--retros-path', str(dest_post / 'inputs/retros_post_adapter.csv')]
        run(cmd, out / 'logs' / f'{r["cutoff"]}_{r["label"]}.log')
        stem = f'{mid}_cutoff_window_posterior_samples'
        if r['label'] == 'exAL-M-T1':
            stem += '_with_raw_ensembles'
            date = f'{r["cutoff"][:4]}_{r["cutoff"][4:6]}_{r["cutoff"][6:]}'
            target = f'Figures/multivariate_synthesis_by_cutoff/cutoff_{date}_multivariate_synthesis_with_reference_ensembles'
        else:
            target = 'Figures/manuscript/reference_synthesis_univariate'
        for ext in ['png', 'pdf']:
            asset = out / 'article_assets' / f'{target}.{ext}'
            asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest / f'{stem}.{ext}', asset)
            assets.append({'article_path': f'{target}.{ext}', 'rendered': str(dest / f'{stem}.{ext}'),
                           'asset': str(asset), 'sha256': digest(asset), 'run_id': r['run_id']})
    if not args.skip_context:
        config = root / 'config/exal_m_t1_setup_support_by_cutoff_v2_20260516.json'
        context_entry = next(x for x in json.loads(config.read_text())['cutoffs'] if x['slug'] == '20221225_exal_m_t1')
        selected_root, bundle_root = Path(context_entry['selected_run_root']), Path(context_entry['figure_bundle_root'])
        context_sources = [config, bundle_root / 'meta.yaml']
        context_sources += list((selected_root / 'inputs/shared').rglob('*.csv'))
        context_sources += list((bundle_root / 'inputs').glob('*.csv'))
        context_sources += [x for x in [bundle_root / 'retros.csv', bundle_root / 'nws_forecast.csv', bundle_root / 'glofas_forecast.csv'] if x.exists()]
        for source in sorted(set(context_sources)):
            records.append({'source': str(source), 'sha256': digest(source), 'bytes': source.stat().st_size, 'read_only': True})
        source_workflow = Path(snapshot['workflow_root'])
        factor_source = source_workflow / 'data/canonical_gdpc_master/v20260509/outputs/gdpc_master_component_01_19870529_20230122.csv'
        metadata_source = source_workflow / 'data/canonical_gdpc_master/v20260509/metadata/gdpc_build_metadata.json'
        factor_copy = out / 'context_inputs/gdpc_component.csv'
        metadata_copy = out / 'context_inputs/gdpc_metadata.json'
        copy_input(factor_source, factor_copy)
        copy_input(metadata_source, metadata_copy)
        # This explicit config retains the current context adapter lineage.
        cmd = ['python3', '-B', str(root / 'scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py'),
               '--project-root', str(root), '--config', str(config), '--output-root', str(out / 'context'),
               '--slugs', '20221225_exal_m_t1', '--skip-review',
               '--canonical-gdpc-factor', str(factor_copy), '--canonical-gdpc-metadata', str(metadata_copy)]
        run(cmd, out / 'logs/context.log')
        rendered = out / 'context/20221225_exal_m_t1/figures/forecats.png'
        for ext in ['png', 'pdf']:
            source = rendered.with_suffix('.' + ext)
            asset = out / f'article_assets/Figures/manuscript/forecast_products_context.{ext}'
            asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, asset)
            assets.append({'article_path': f'Figures/manuscript/forecast_products_context.{ext}',
                           'rendered': str(source), 'asset': str(asset), 'sha256': digest(asset),
                           'context_config': str(config)})
    for record in records:
        assert digest(Path(record['source'])) == record['sha256'], record['source']
        if 'copy' in record:
            assert digest(Path(record['copy'])) == record['sha256'], record['copy']
    report = {'schema': 'comment1-figure-render-v1', 'snapshot': str(args.snapshot.resolve()),
              'snapshot_sha256': digest(args.snapshot), 'project_root': str(root),
              'style': str(root / 'config/post_publication_figures.yaml'),
              'style_sha256': digest(root / 'config/post_publication_figures.yaml'),
              'renderer_sha256': {str(path.relative_to(root)): digest(path) for path in [
                  root / 'R/unified/post_publication_figures.R', root / 'scripts/render_focus_publication_posterior_plot.R',
                  root / 'scripts/forecats_plot_bundle.R', root / 'scripts/render_setup_support_bundle_v2.R',
                  root / 'scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py', Path(__file__).resolve()]},
              'reference_guides': {
                  'synthesis': {'log1p_cms': [5.20948615, 6.06378521], 'source': 'existing focus renderer fixed reference levels'},
                  'context': {'log1p_cms': [math.log1p(x * 0.028316846592) for x in [7402.38, 14895.73]],
                              'discharge_cfs': [7402.38, 14895.73], 'source': 'USGS rating40.0 discharge equivalents in existing figure_style_contract.R'},
                  'labels': ['Lower flow reference', 'Upper flow reference'],
                  'interpretation': 'Existing display-specific reference discharges are retained; labels do not assert equal thresholds across displays.'},
              'inputs_unchanged': True, 'inputs': records, 'commands': commands, 'assets': assets}
    (out / 'render_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Rendered {len(assets)} PNG/PDF assets; source and copied input hashes unchanged. Manifest: {out / "render_manifest.json"}')


if __name__ == '__main__':
    main()
