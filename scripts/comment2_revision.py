#!/usr/bin/env python3
"""Validate frozen point-2 evidence and regenerate only its three TeX tables.

The check is self-contained in the article repository. Existing publication
assets and imported scores must agree before a table can be written. No fitting,
downloads, figure refreshes or changes to the original tables are performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'artifacts/comment2_revision'
CUTOFFS = ('20210123', '20211112', '20211221', '20220511', '20221225')
METHODS = ('CLIM-SEASONAL', 'PERSISTENCE', 'RAW-GLOFAS', 'RAW-NWS',
           'EMOS-GLOFAS', 'AL-M-T1', 'exAL-M-T1')
OUTPUTS = ('comment2_external_comparison_table.tex',
           'comment2_external_by_origin_table.tex', 'comment2_fit_diagnostic_table.tex')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root: Path, relative: str) -> Path:
    candidate = root / relative
    path = candidate.resolve()
    if not path.is_relative_to(root.resolve()) or candidate.is_symlink():
        raise ValueError(f'Unsafe article path: {relative}')
    if not path.is_file():
        raise ValueError(f'Missing article input: {relative}')
    return path


def rows(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix == '.gz' else Path.open
    with opener(path, 'rt', newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def close(a: str | float, b: str | float, detail: str) -> None:
    av, bv = float(a), float(b)
    require(math.isfinite(av) and math.isfinite(bv) and
            math.isclose(av, bv, rel_tol=1e-11, abs_tol=1e-12), detail)


def cutoff(value: str) -> str:
    return value.replace('-', '')


def validate(root: Path) -> dict:
    base = root / REVISION
    manifest = json.loads(local(root, REVISION + '/manifest.json').read_text())
    require(manifest.get('schema') == 'comment2_revision_v1', 'Unknown point-2 schema')
    require(manifest.get('release_status') == 'validated', 'Point-2 evidence is not a validated release')
    for rel, expected in manifest['files'].items():
        require(digest(local(root, rel)) == expected, f'Point-2 input hash changed: {rel}')
    for rel, expected in manifest['preserved_files'].items():
        require(digest(local(root, rel)) == expected, f'Existing publication asset changed: {rel}')

    aggregate = rows(base / 'external_baselines/aggregate.csv')
    origin = rows(base / 'external_baselines/by_origin_horizon.csv')
    per_time = rows(base / 'external_baselines/per_time.csv')
    params = rows(base / 'external_baselines/parameters.csv')
    training = rows(base / 'external_baselines/training_diagnostics.csv')
    lookup = {(cutoff(r['cutoff_date']), r['model'], int(r['horizon_days'])): r for r in origin}
    require(len(lookup) == len(origin), 'Duplicate origin/model/horizon score')
    aggregate_keys = {(r['model'], int(r['horizon_days'])) for r in aggregate}
    require(len(aggregate_keys) == len(aggregate) and
            aggregate_keys == {(r['model'], int(r['horizon_days'])) for r in origin},
            'Missing or duplicate pooled comparison')
    for key, r in lookup.items():
        c, model, horizon = key
        require(c in CUTOFFS and horizon in (8, 28), f'Unexpected score case: {key}')
        require(int(r['n_valid']) == horizon, f'Incomplete verification horizon: {key}')
        reference = lookup[(c, 'CLIM-SEASONAL', horizon)]
        close(r['mean_climatology_crps'], reference['mean_crps'], f'Wrong climatology reference: {key}')
        denominator = float(reference['mean_crps'])
        require(denominator > 0 and float(r['mean_crps']) >= 0, f'Invalid score: {key}')
        close(r['crpss'], 1 - float(r['mean_crps']) / denominator, f'Wrong origin skill: {key}')
    for model in METHODS:
        for c in CUTOFFS:
            for horizon in (8, 28):
                if model != 'RAW-NWS' or horizon == 8:
                    require((c, model, horizon) in lookup, f'Missing comparison: {c}/{model}/{horizon}')

    for r in aggregate:
        model, horizon = r['model'], int(r['horizon_days'])
        selected = [lookup[c, model, horizon] for c in CUTOFFS]
        require(int(r['origins']) == 5 and int(r['n_valid']) == 5*horizon,
                f'Wrong aggregate coverage: {model}/{horizon}')
        close(r['mean_crps'], sum(float(x['mean_crps']) for x in selected)/5,
              f'Wrong pooled score: {model}/{horizon}')
        ref = sum(float(x['mean_climatology_crps']) for x in selected)/5
        close(r['mean_climatology_crps'], ref, f'Wrong pooled reference: {model}/{horizon}')
        close(r['crpss'], 1-float(r['mean_crps'])/ref, f'Wrong pooled skill: {model}/{horizon}')

    daily = {}
    for r in per_time:
        c, model, lead = cutoff(r['cutoff_date']), r['model'], int(r['lead_day'])
        key = (c, model, lead)
        require(key not in daily, f'Duplicate per-time case: {key}')
        daily[key] = r
        expected_date = date.fromisoformat(r['cutoff_date']) + timedelta(days=lead)
        require(r['forecast_date'] == expected_date.isoformat(), f'Misaligned target: {key}')
        require(math.isfinite(float(r['crps'])) and float(r['crps']) >= 0,
                f'Invalid daily score: {key}')
    for (c, model, h), r in lookup.items():
        selected = [daily[c, model, lead] for lead in range(1, h+1)]
        close(r['mean_crps'], sum(float(x['crps']) for x in selected)/h,
              f'Summary disagrees with per-time scores: {c}/{model}/{h}')
    for (c, model, lead), r in daily.items():
        close(r['climatology_crps'], daily[c, 'CLIM-SEASONAL', lead]['crps'],
              f'Wrong daily reference: {c}/{model}/{lead}')
        if model in ('CLIM-SEASONAL', 'PERSISTENCE', 'EMOS-GLOFAS'):
            require(int(r['n_samples_nominal']) == 2000 and
                    r['score_method'] == 'quantile_check_loss_sum' and
                    r['tau_rule'] == 'k_over_m_plus_1' and r['score_scale'] == 'log_cms_plus1',
                    'New baseline changed the evaluation convention')

    original = rows(root / 'tables/generated_tex/benchmark_crps_horizon_summary.csv')
    for r in original:
        key = (r['cutoff'], r['row_label'], int(r['horizon_days']))
        require(key in lookup, f'Original method absent: {key}')
        close(lookup[key]['mean_crps'], r['mean_crps'], f'Imported score changed: {key}')
    require(len(params) == 140 and len(training) == 140, 'Expected 140 lead-specific EMOS fits')
    require(len({(cutoff(r['cutoff_date']), int(r['lead_day'])) for r in params}) == 140,
            'Duplicate EMOS fit')
    for r in params:
        require(float(r['c']) > 0 and float(r['d']) >= 0 and float(r['forecast_sigma']) > 0,
                'Invalid EMOS scale')
        require(all(math.isfinite(float(r[k])) for k in ('a','b','c','d','forecast_mu','forecast_sigma')),
                'Nonfinite EMOS parameter')
    for r in training:
        require(int(r['training_cases']) >= 100 and int(r['converged_starts']) >= 1,
                'Insufficient EMOS training or optimization evidence')
        require(r['last_target_date'] <= r['cutoff_date'] and r['last_issue_date'] < r['cutoff_date'],
                'Ineligible baseline training case')
    predictions = rows(base / 'external_baselines/predictive_summary.csv')
    require(len(predictions) == 420, 'Missing baseline predictive summaries')
    for r in predictions:
        q = [float(r[k]) for k in ('q025','q05','q20','q35','q50','q65','q80','q95','q975')]
        require(all(math.isfinite(v) and v >= 0 for v in q) and q == sorted(q),
                'Invalid baseline predictive quantile ordering or support')
        if r['model'] == 'PERSISTENCE':
            key = (cutoff(r['cutoff_date']), r['model'], int(r['lead_day']))
            close(daily[key]['crps'], abs(float(r['observed']) - float(r['predictive_grid_mean'])),
                  f'Persistence point-mass score differs from absolute error: {key}')
    fits = json.loads((base / 'component_diagnostics/fit_ledger.json').read_text())
    runs = json.loads((base / 'component_diagnostics/run_ledger.json').read_text())
    summary = json.loads((base / 'component_diagnostics/summary.json').read_text())
    require(len(runs) == 70 and len(fits) == 400, 'Incomplete saved-fit evidence ledger')
    expected_runs = {('benchmark', r['cutoff'], r['manuscript_label']):
                     r.get('artifact_run_id') or r['run_id'] for r in rows(
                         root/'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv')}
    expected_runs.update({('component_removal', r['cutoff'], r['manuscript_label']):
                          r['resolved_run_id'] for r in rows(
                              root/'artifacts/he3_exdqlm_ablation_authoritative/he3_ablation_long.csv')
                          if r['variant'] != 'full'})
    actual_runs = {(r['study'], r['cutoff'], r['label']): r['run_id'] for r in runs}
    require(actual_runs == expected_runs, 'Diagnostic run identities differ from publication authority')
    require({(r['study'],r['cutoff'],r['label']) for r in fits} == set(expected_runs),
            'Fit ledger omits a published run')
    require(summary['fit_status_counts'] == dict(Counter(r['stopping_status'] for r in fits)),
            'Diagnostic status summary disagrees with fit ledger')
    return dict(aggregate=aggregate, origin=origin, per_time=per_time, fits=fits, runs=runs,
                summary=summary, manifest=manifest)


def table(caption: str, label: str, header: str, body: list[str], note: str,
          columns: str) -> str:
    return '\n'.join([
        '% Generated by scripts/comment2_revision.py from checked frozen evidence.',
        r'\begin{table}[!htbp]', r'\centering', r'\begin{threeparttable}',
        r'\caption{' + caption + '}', r'\label{' + label + '}',
        r'\fontsize{8.5}{10.5}\selectfont',
        r'\begin{tabular}{' + columns + '}', r'\hline', header + r' \\', r'\hline',
        *body, r'\hline', r'\end{tabular}', r'\begin{tablenotes}',
        r'\fontsize{8}{10}\selectfont',
        r'\item \textit{Note:} ' + note, r'\end{tablenotes}',
        r'\end{threeparttable}', r'\end{table}', '',
    ])


def render(data: dict) -> dict[str, str]:
    lookup = {(r['model'], int(r['horizon_days'])): r for r in data['aggregate']}
    body = []
    for model in METHODS:
        values = []
        for h in (28, 8):
            row = lookup.get((model, h))
            values += [f"{float(row['mean_crps']):.5f}", f"{float(row['crpss']):.5f}"] if row else ['---', '---']
        body.append(model + ' & ' + ' & '.join(values) + r' \\')
    result = {OUTPUTS[0]: table(
        'External-reference comparison and climatology-relative skill across five forecast origins.',
        'tab:comment2_external_comparison',
        'Method & 28-day CRPS & 28-day CRPSS & 8-day CRPS & 8-day CRPSS', body,
        r'Scores use daily USGS verification on the $\log(1+x)$ discharge scale. '
        r'CRPS averages the five complete origin windows; CRPSS is one minus the ratio '
        r'of the aggregated method and seasonal-climatology scores. Higher CRPSS is better. '
        r'PERSISTENCE is a point forecast; EMOS-GLOFAS uses GloFAS alone. '
        r'Raw NWS has eight available leads. Existing method scores are unchanged.', 'lrrrr')}
    lookup = {(cutoff(r['cutoff_date']), r['model'], int(r['horizon_days'])): r for r in data['origin']}
    body = []
    for horizon in (28, 8):
        body.append(r'\multicolumn{6}{l}{\textit{' + str(horizon) + r'-day horizon}} \\')
        for model in METHODS:
            if model == 'RAW-NWS' and horizon == 28:
                continue
            values = [lookup[c, model, horizon] for c in CUTOFFS]
            body.append(model + ' & ' + ' & '.join(
                r'\shortstack[r]{' + f"{float(r['mean_crps']):.5f}" + r'\\'
                + f"({float(r['crpss']):.5f})" + '}' for r in values) + r' \\')
    result[OUTPUTS[1]] = table(
        'External-reference scores by forecast origin and horizon.', 'tab:comment2_external_by_origin',
        'Method & Jan 2021 & Nov 2021 & Dec 2021 & May 2022 & Dec 2022', body,
        r'Each entry gives mean CRPS above climatology-relative CRPSS in parentheses. '
        r'The exact origins are January 23, November 12 and December 21, 2021, '
        r'and May 11 and December 25, 2022. Definitions match Table~\ref{tab:comment2_external_comparison}.', 'lrrrrr')
    groups = {}
    for r in data['fits']:
        groups.setdefault((r['study'], r['label']), Counter()).update([r['stopping_status']])
    body = []
    for (study, label), counts in sorted(groups.items()):
        other = sum(n for status,n in counts.items() if status not in ('converged','budget_limited','unknown'))
        body.append(label + ' & ' + ' & '.join(str(n) for n in (
            sum(counts.values()), counts['converged'], counts['budget_limited'], other, counts['unknown'])) + r' \\')
    result[OUTPUTS[2]] = table(
        'Recorded stopping evidence for the existing benchmark and component-removal fits.',
        'tab:comment2_fit_diagnostics',
        'Specification & Fits & Converged & Budget limit & Other & Unrecorded', body,
        r'Counts refer to individual quantile fits, or one fit per Gaussian run. '
        r'Converged means the saved criteria or explicit summary report convergence; '
        r'it does not certify model validity. Budget limit means recorded criteria were '
        r'unmet at the iteration limit. Other covers guards or criteria-unmet stops; '
        r'unrecorded means sufficient stopping evidence is absent. Pipeline completion '
        r'and a legacy terminal success phrase do not establish convergence.', 'lrrrrr')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true', help='Validate tables without writing')
    args = parser.parse_args()
    root = args.article_root.resolve()
    try:
        data = validate(root)
        outputs = render(data)
        if args.check:
            for name, expected in outputs.items():
                require((root/'tables/generated_tex'/name).read_text() == expected,
                        f'Generated point-2 table is stale: {name}')
        else:
            for name, text in outputs.items():
                (root/'tables/generated_tex'/name).write_text(text)
    except (OSError, ValueError, KeyError) as exc:
        print(f'Point-2 validation failed: {exc}', file=sys.stderr)
        return 1
    print('Validated point-2 source hashes, preserved assets, comparisons, skill and fit evidence; '
          + ('three tables match.' if args.check else 'three tables generated.'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
