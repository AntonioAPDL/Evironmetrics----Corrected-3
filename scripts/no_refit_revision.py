#!/usr/bin/env python3
"""Validate the saved-output revision and generate only its new TeX tables.

No fitting, posterior simulation, downloads or legacy asset refresh is called.
Use --check for a read-only release check, --seal after a reviewed input update.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'artifacts/no_refit_revision'
ORIGINS = ('2021-01-23', '2021-11-12', '2021-12-21', '2022-05-11', '2022-12-25')
MODELS = ('N-U-T1', 'N-M-T0', 'N-M-T1', 'AL-U-T1', 'AL-M-T0', 'AL-M-T1',
          'exAL-U-T1', 'exAL-M-T0', 'exAL-M-T1', 'RAW-GLOFAS', 'RAW-NWS',
          'CLIM-SEASONAL', 'PERSISTENCE', 'EMOS-GLOFAS')
SCALES = ('log1p_cms', 'discharge_cms')
PROBS = (.05, .20, .35, .50, .65, .80, .95)
COUNTS = {'observations': 140, 'representations': 70, 'forecast_cases': 1860,
          'scores_per_case': 3720, 'quantiles_per_case': 26040,
          'intervals_per_case': 3720, 'summary_by_origin_horizon': 270,
          'summary_pooled': 54, 'calibration_summary': 2268,
          'interval_summary': 324, 'source_lead_diagnostics': 360,
          'source_lead_summary': 72, 'support_audit': 70, 'legacy_parity': 1860}
OUTPUTS = ('no_refit_score_comparison_table.tex', 'no_refit_calibration_summary_table.tex',
           'no_refit_reference_settings_table.tex', 'no_refit_score_sensitivity_table.tex',
           'no_refit_origin_diagnostics_table.tex')


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(root: Path, rel: str) -> Path:
    path = root / rel
    require(path.is_file() and not path.is_symlink() and
            path.resolve().is_relative_to(root.resolve()), f'Missing or unsafe input: {rel}')
    return path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def close(actual: float | str, expected: float | str, context: str, scale: str = '') -> None:
    a, b = float(actual), float(expected)
    require(math.isfinite(a) and math.isfinite(b) and math.isclose(
        a, b, rel_tol=1e-12, abs_tol=1e-10 if scale == 'discharge_cms' else 1e-12),
        f'Numerical mismatch: {context}: {a} != {b}')


def mean(values) -> float:
    values = list(values)
    require(bool(values), 'Empty comparison')
    return math.fsum(float(x) for x in values) / len(values)


def case_key(r: dict, scaled: bool = True) -> tuple:
    key = (r['model_id'], r['origin_date'], int(r['lead_day']))
    return key + (r['score_scale'],) if scaled else key


def index(data: list[dict], key, description: str) -> dict:
    out = {key(r): r for r in data}
    require(len(out) == len(data), f'Duplicate {description}')
    return out


def validate(root: Path, check_manifest: bool = True) -> dict:
    base = root / BASE
    if check_manifest:
        manifest = json.loads(safe(root, BASE + '/manifest.json').read_text())
        require(manifest['schema'] == 'no_refit_revision_v1' and
                manifest['release_status'] == 'validated', 'Unvalidated revision manifest')
        for rel, expected in manifest['files'].items():
            require(digest(safe(root, rel)) == expected, f'Revision hash changed: {rel}')
    # Preserve the previous release contract independently of the new manifest.
    old = json.loads(safe(root, 'artifacts/comment2_revision/manifest.json').read_text())
    for rel, expected in {**old['files'], **old['preserved_files']}.items():
        require(digest(safe(root, rel)) == expected, f'Protected publication file changed: {rel}')
    data = {}
    for name, expected in COUNTS.items():
        data[name] = rows(safe(root, BASE + '/results/' + name + '.csv'))
        require(len(data[name]) == expected, f'Wrong {name} row count')
    obs = index(data['observations'], lambda r: r['observation_case_id'], 'observation')
    require({(r['origin_date'], int(r['lead_day'])) for r in obs.values()} ==
            {(o, lead) for o in ORIGINS for lead in range(1, 29)}, 'Incomplete observation registry')
    for r in obs.values():
        require(r['target_date'] == (date.fromisoformat(r['origin_date']) +
                timedelta(days=int(r['lead_day']))).isoformat(), 'Observation target date mismatch')
        close(r['observed_discharge_cms'], math.expm1(float(r['observed_log1p_cms'])),
              'Observation transform', 'discharge_cms')
    reps = index(data['representations'], lambda r: r['representation_id'], 'representation')
    require({(r['model_id'], r['origin_date']) for r in reps.values()} ==
            {(m, o) for m in MODELS for o in ORIGINS}, 'Wrong model/origin representation registry')
    for r in reps.values():
        require(digest(safe(root, BASE + '/' + r['input_snapshot_relpath'])) == r['source_sha256'],
                'Frozen prediction hash mismatch')
        require(int(r['available_leads']) == (8 if r['model_id'] == 'RAW-NWS' else 28),
                'Unexpected source availability')
    cases = index(data['forecast_cases'], lambda r: case_key(r, False), 'forecast case')
    expected_cases = {(m, o, lead) for m in MODELS for o in ORIGINS
                      for lead in range(1, 9 if m == 'RAW-NWS' else 29)}
    require(set(cases) == expected_cases, 'Incomplete forecast cases or unexpected NWS lead')
    for key, r in cases.items():
        truth, rep = obs[r['observation_case_id']], reps[r['representation_id']]
        require(all(r[k] == truth[k] for k in ('origin_date', 'lead_day', 'target_date')) and
                r['model_id'] == rep['model_id'] and r['origin_date'] == rep['origin_date'],
                f'Case identity mismatch: {key}')
        require(r['n_values_finite'] == r['n_values_nominal'] == rep['n_values_nominal'] and
                r['availability_status'] == 'AVAILABLE', f'Incomplete saved representation: {key}')
    scores = index(data['scores_per_case'], case_key, 'scaled score case')
    scaled_keys = {key + (scale,) for key in expected_cases for scale in SCALES}
    require(set(scores) == scaled_keys, 'Incomplete score scales')
    for key, r in scores.items():
        original = cases[key[:3]]
        require(all(r[k] == original[k] for k in original), f'Score/case registry mismatch: {key}')
        y = obs[r['observation_case_id']]['observed_log1p_cms' if key[3] == 'log1p_cms'
                                          else 'observed_discharge_cms']
        close(r['observed'], y, 'Score observation', key[3])
        ecdf, legacy, m = float(r['exact_ecdf_crps']), float(r['original_grid_formula_score']), int(r['n_values_nominal'])
        require(ecdf >= 0 and legacy >= 0, 'Negative distribution score')
        # The declared pairwise sensitivity is algebraically recoverable from the two distinct scores.
        if r['adjustment_status'].startswith('not_applicable'):
            require(r['iid_adjusted_crps'] in ('', 'NA'), 'Adjusted deterministic score must be unavailable')
        else:
            require(m > 1, 'Invalid iid adjustment sample size')
            close(r['iid_adjusted_crps'], ecdf - (legacy-ecdf)*(m+1)/(m-1),
                  'Pairwise adjustment identity', key[3])
        if r['model_id'] == 'PERSISTENCE':
            close(ecdf, abs(float(y)-float(r['predictive_mean'])), 'Persistence identity', key[3])
    for name, pooled in (('summary_by_origin_horizon', False), ('summary_pooled', True)):
        seen = set()
        for r in data[name]:
            model, scale, h = r['model_id'], r['score_scale'], int(r['horizon_days'])
            origin = 'POOL' if pooled else r['origin_date']
            key = (model, origin, scale, h)
            require(key not in seen, 'Duplicate score summary'); seen.add(key)
            origins = ORIGINS if pooled else (origin,)
            selected = [scores[model, o, lead, scale] for o in origins for lead in range(1, h+1)]
            n = len(origins)*h
            require(int(r['n_expected_cases']) == int(r['n_valid_cases']) == n, 'Wrong score denominator')
            for summary, field in (('mean_original_grid_score', 'original_grid_formula_score'),
                                   ('mean_exact_ecdf_crps', 'exact_ecdf_crps'),
                                   ('mean_median_absolute_error', 'median_absolute_error')):
                close(r[summary], mean(x[field] for x in selected), summary, scale)
            if not r['adjustment_status'].startswith('not_applicable'):
                close(r['mean_iid_adjusted_crps'], mean(x['iid_adjusted_crps'] for x in selected),
                      'Mean iid sensitivity', scale)
            else:
                require(r['mean_iid_adjusted_crps'] in ('', 'NA'), 'Adjusted summary must be unavailable')
            ref = mean(scores['CLIM-SEASONAL', o, lead, scale]['exact_ecdf_crps']
                       for o in origins for lead in range(1, h+1))
            close(r['mean_climatology_exact_ecdf_crps'], ref, 'Matching climatology', scale)
            close(r['ecdf_crpss'], 1-float(r['mean_exact_ecdf_crps'])/ref, 'Exact-ECDF skill')
    quantiles = index(data['quantiles_per_case'], lambda r: case_key(r)+(round(float(r['tau']), 2),), 'targeted quantile')
    require(set(quantiles) == {key+(p,) for key in scaled_keys for p in PROBS}, 'Incomplete targeted quantiles')
    for key, r in quantiles.items():
        y, q, tau = float(scores[key[:4]]['observed']), float(r['quantile_value']), float(r['tau'])
        event_y = float(scores[key[:3]+('log1p_cms',)]['observed'])
        event_q = float(quantiles[key[:3]+('log1p_cms',key[4])]['quantile_value'])
        require((int(r['hit_strict']), int(r['hit_weak']), int(r['is_exact_tie'])) ==
                (int(event_y < event_q), int(event_y <= event_q), int(event_y == event_q)),
                'Incorrect strict/weak/tie event in declared event scale')
        close(r['check_loss'], (y-q)*(tau-int(y-q < 0)), 'Quantile check loss', key[3])
        if key[3] == 'discharge_cms':
            close(q, math.expm1(float(quantiles[key[:3]+('log1p_cms', key[4])]['quantile_value'])),
                  'Inverse-transformed declared quantile', key[3])
    intervals = index(data['intervals_per_case'], case_key, '95 percent interval')
    require(set(intervals) == scaled_keys, 'Incomplete predictive intervals')
    for key, r in intervals.items():
        y, lo, hi = float(scores[key]['observed']), float(r['lower']), float(r['upper'])
        require(lo <= hi and math.isfinite(lo) and math.isfinite(hi), 'Invalid predictive limits')
        event_y = float(scores[key[:3]+('log1p_cms',)]['observed'])
        event_r = intervals[key[:3]+('log1p_cms',)]
        event_lo, event_hi = float(event_r['lower']), float(event_r['upper'])
        events = (int(event_y < event_lo), int(event_lo <= event_y <= event_hi), int(event_y > event_hi))
        require(tuple(int(r[x]) for x in ('lower_miss','inside','upper_miss')) == events,
                'Incorrect closed interval event')
        close(r['width'], hi-lo, 'Interval width', key[3])
        close(r['interval_score'], hi-lo+40*(lo-y)*events[0]+40*(y-hi)*events[2],
              '95 percent proper interval score', key[3])
        if key[3] == 'discharge_cms':
            for bound in ('lower', 'upper'):
                close(r[bound], math.expm1(float(intervals[key[:3]+('log1p_cms',)][bound])),
                      'Inverse-transformed predictive bound', key[3])
    for name, caseset, fields, summaries in (
        ('calibration_summary', quantiles, ('hit_strict','hit_weak','is_exact_tie'),
         ('n_strict','n_weak','n_tie')),
        ('interval_summary', intervals, ('lower_miss','inside','upper_miss'),
         ('n_lower_miss','n_inside','n_upper_miss'))):
        seen = set()
        for r in data[name]:
            model, scale, h = r['model_id'], r['score_scale'], int(r['horizon_days'])
            origins = ORIGINS if r['origin_or_pool'] == 'POOL' else (r['origin_or_pool'],)
            p = (round(float(r['tau']),2),) if name == 'calibration_summary' else ()
            k = (model, r['origin_or_pool'], scale, h)+p
            require(k not in seen, 'Duplicate calibration summary'); seen.add(k)
            selected = [caseset[(model,o,lead,scale)+p] for o in origins for lead in range(1,h+1)]
            n = h*len(origins)
            require(int(r['n_valid']) == int(r['n_expected']) == n, 'Calibration denominator mismatch')
            for field, summary in zip(fields, summaries):
                require(int(r[summary]) == sum(int(x[field]) for x in selected), 'Calibration count mismatch')
            if p:
                for field, count in (('rate_strict','n_strict'), ('rate_weak','n_weak')):
                    close(r[field], int(r[count])/n, 'Hit rate')
                close(r['mean_check_loss'], mean(x['check_loss'] for x in selected), 'Mean quantile loss', scale)
            else:
                close(r['empirical_coverage'], int(r['n_inside'])/n, 'Interval coverage')
                for field, raw in (('mean_width','width'), ('mean_interval_score','interval_score')):
                    close(r[field], mean(x[raw] for x in selected), field, scale)
    for r in data['legacy_parity']:
        require(float(r['absolute_error']) <= 1e-12, 'Legacy published-score replay failed')
    reporting = base / 'reporting'
    for rel, expected in json.loads((reporting/'reporting_manifest.json').read_text())['files'].items():
        require(digest(safe(root, BASE+'/reporting/'+rel)) == expected, 'Reporting source hash changed')
    for file, n in (('configured_settings',45), ('reference_settings',5),
                    ('feature_state_dictionary',12), ('corrected_endpoint_summaries',27)):
        data[file] = rows(reporting/(file+'.csv'))
        require(len(data[file]) == n, f'Incorrect {file} count')
    gates = json.loads((reporting/'source_gates.json').read_text())
    require(gates['original_numeric_strings_preserved'] and gates['displayed_base_rows_unchanged'] and
            not gates['new_fits'] and not gates['new_simulations'], 'Reporting scope changed')
    scope = json.loads((base/'inference_scope/scope_audit.json').read_text())
    require(bool(scope), 'Missing conditional inference scope record')
    for subtree, name in (('inference_scope','SOURCE_MANIFEST.json'),
                          ('synthesis_diagnostics','manifest.json')):
        sub = base/subtree
        record=json.loads((sub/name).read_text())
        # Inference source manifest has structured records; its independent check is retained separately.
        if subtree=='synthesis_diagnostics':
            for rel, expected in record['files'].items():
                require(digest(safe(root,BASE+'/'+subtree+'/'+rel))==expected,
                        'Synthesis-stage source hash changed')
            for filename,n in (('per_case.csv',35280),('crossings_per_case.csv',2520),
                               ('crossing_summary.csv',18),('summary_pooled.csv',504),
                               ('summary_by_origin_horizon.csv',2520),('inputs/anchors.csv',5880)):
                require(len(rows(sub/filename))==n,'Synthesis-stage row count mismatch')
            stages=rows(sub/'per_case.csv')
            for r in stages:
                if r['role']=='final_synthesized':
                    key=(r['model_id'],r['origin_date'],int(r['lead_day']),r['score_scale'],
                         round(float(r['tau']),2))
                    close(r['quantile_value'],quantiles[key]['quantile_value'],
                          'Final stage differs from authoritative quantile',r['score_scale'])
    return data


def table(caption: str, label: str, header: str, body: list[str], note: str, columns: str) -> str:
    return '\n'.join(['% Generated by scripts/no_refit_revision.py; do not edit.',
        r'\begin{table}[!htbp]', r'\centering', r'\begin{threeparttable}',
        r'\caption{'+caption+'}', r'\label{'+label+'}', r'\fontsize{8.5}{10.5}\selectfont',
        r'\setlength{\tabcolsep}{4pt}', r'\begin{tabular}{'+columns+'}', r'\hline',
        header+r' \\', r'\hline', *body, r'\hline', r'\end{tabular}',
        r'\begin{tablenotes}', r'\fontsize{8}{10}\selectfont', r'\item \textit{Note:} '+note,
        r'\end{tablenotes}', r'\end{threeparttable}', r'\end{table}', ''])


def number(value: str | float) -> str:
    if value in ('', 'NA'):
        return '---'
    v = float(value)
    if abs(v) >= 1e5:
        mantissa, exponent = f'{v:.5e}'.split('e')
        return '$'+mantissa+r'\times 10^{'+str(int(exponent))+'}$'
    return f'{v:.5f}'


def render(data: dict) -> dict[str, str]:
    pooled = {(r['model_id'],r['score_scale'],int(r['horizon_days'])):r for r in data['summary_pooled']}
    principal = ('exAL-M-T1','AL-M-T1','exAL-U-T1','AL-U-T1','RAW-GLOFAS','RAW-NWS',
                 'CLIM-SEASONAL','PERSISTENCE','EMOS-GLOFAS')
    def scorebody(models, scale, sensitivity=False):
        body = []
        for model in models:
            values = []
            for h in (28,8):
                r = pooled.get((model,scale,h))
                fields = ('mean_exact_ecdf_crps','mean_iid_adjusted_crps') if sensitivity else ('mean_exact_ecdf_crps','ecdf_crpss')
                values += [number(r[f]) for f in fields] if r else ['---','---']
            body.append(model+' & '+' & '.join(values)+r' \\')
        return body
    common = (r'Exact ECDF CRPS scores the equally weighted saved representation. CRPSS uses the '
        r'frozen seasonal-climatology representation on the same cases and scale. Means pool '
        r'140 cases at 28 days and 40 cases at eight days. Raw NWS is available only through lead eight. '
        r'The earlier tables retain the quantile-grid approximation.')
    output = {OUTPUTS[0]:table('Distribution scores of the saved predictive representations on the transformed scale.',
        'tab:no_refit_scores','Method & 28-day CRPS & 28-day CRPSS & 8-day CRPS & 8-day CRPSS',
        scorebody(principal,'log1p_cms'),common,'lrrrr')}
    intervals = {(r['model_id'],r['origin_or_pool'],r['score_scale'],int(r['horizon_days'])):r
                 for r in data['interval_summary']}
    body=[]
    for model in principal:
        values=[]
        for h in (28,8):
            r=intervals.get((model,'POOL','log1p_cms',h))
            values += [r['n_inside']+'/'+r['n_valid'],number(r['mean_width']),number(r['mean_interval_score'])] if r else ['---']*3
        body.append(model+' & '+' & '.join(values)+r' \\')
    output[OUTPUTS[1]]=table('Coverage, width and interval score of central 95\% predictive intervals.',
        'tab:no_refit_calibration',r'Method & \multicolumn{3}{c}{28 days} & \multicolumn{3}{c}{8 days} \\ '+
        r' & Covered & Width & Interval score & Covered & Width & Interval score',body,
        r'Coverage is the count within the closed 2.5th--97.5th percentile interval divided by '
        r'the complete case count. Width and proper interval score are on the $\log(1+x)$ scale; '
        r'lower interval score is better. Model limits use sample type-8 quantiles; raw ensembles '
        r'and deterministic grids use the empirical inverse CDF. Persistence has zero width. '
        r'Discharge-scale coverage is identical under the stated inverse-transformation convention.', 'lrrrrrr')
    body=[]
    for r in data['reference_settings']:
        origin=date.fromisoformat(r['origin'][:4]+'-'+r['origin'][4:6]+'-'+r['origin'][6:]).strftime('%b %Y')
        values=[r[x+'_tex'] for x in ('df_t','df_s1','df_s67','df_discrep','df_trans','df_covs','epsilon_effective')]
        body.append(origin+' & '+' & '.join('$'+v+'$' for v in values)+r' \\')
    output[OUTPUTS[2]]=table('Exact discount and initialization settings for the exAL-M-T1 reference fits.',
        'tab:no_refit_settings',r'Origin & Trend & Annual & Slow & Discrepancy & Transfer & Loading & $\epsilon$',body,
        r'Both annual pairs have the annual discount shown. Discrepancy entries are multipliers '
        r'applied to the corresponding trend/seasonal discounts. Transfer and loading columns refer '
        r'to the autoregressive transfer state and feature-loading states. All rows use '
        r'$\lambda=1-3\times10^{-2}$ and $c=1$. Exact settings, priors, resolved defaults and run '
        r'identities for all 45 benchmark configurations are in the companion bundle.', 'lrrrrrrr')
    output[OUTPUTS[3]]=table('Finite-sample score sensitivity for all saved predictive representations.',
        'tab:no_refit_sensitivity','Method & 28-day ECDF & 28-day adjusted & 8-day ECDF & 8-day adjusted',
        scorebody(MODELS,'log1p_cms',True),
        r'All scores use $\log(1+x)$. The adjusted pairwise score assumes independent, identically '
        r'distributed draws from a predictive distribution. For physical members this is only a '
        r'sensitivity assumption. Model sample counts are 2,000 for AL/exAL, 64 for N-U-T1 and 48 '
        r'for N-M-T0/T1; raw GloFAS and NWS contain 51 and seven members. The adjustment is '
        r'not applicable to deterministic climatology/EMOS grids or the persistence point mass. '
        r'No adjusted skill score is reported.', 'lrrrr')
    text=table('Distribution scores on the original discharge scale, in m$^3$/s.',
        'tab:no_refit_original_scale','Method & 28-day CRPS & 28-day CRPSS & 8-day CRPS & 8-day CRPSS',
        scorebody(MODELS,'discharge_cms'),
        r'Each stored predictive value is inverse-transformed with $\exp(y)-1$ before scoring; '
        r'transformed-scale scores are not exponentiated. '+common, 'lrrrr')
    body=[]
    for h in (28,8):
        body.append(r'\multicolumn{6}{l}{\textit{'+str(h)+r'-day horizon}} \\')
        for model in MODELS:
            if model=='RAW-NWS' and h==28:
                continue
            values=[intervals[model,o,'log1p_cms',h] for o in ORIGINS]
            body.append(model+' & '+' & '.join(r['n_inside']+'/'+r['n_valid'] for r in values)+r' \\')
    text+=table('Predictive 95\% interval coverage by origin and horizon.',
        'tab:no_refit_origin_coverage','Method & Jan 2021 & Nov 2021 & Dec 2021 & May 2022 & Dec 2022',body,
        r'Entries give covered observations divided by available cases using the same limits and '
        r'closed-interval rule as Table~\ref{tab:no_refit_calibration}. This descriptive check '
        r'does not treat successive daily cases as independent replicates. Full per-origin '
        r'distribution scores, targeted-quantile counts and interval scores accompany the article.', 'lrrrrr')
    output[OUTPUTS[4]]=text
    return output


def seal(root: Path) -> None:
    paths = [p for p in (root/BASE).rglob('*') if p.is_file() and p != root/BASE/'manifest.json'
             and '__pycache__' not in p.parts]
    paths += [root/'tables/generated_tex'/name for name in OUTPUTS]
    paths += [root/'Figures/manuscript/no_refit_quantile_reliability.png',
              root/'scripts/no_refit_revision.py', root/'scripts/refresh_no_refit_revision.py',
              root/'docs/no_refit_revision.txt', root/'docs/no_refit_inference_scope.txt']
    manifest={'schema':'no_refit_revision_v1','release_status':'validated',
        'scope':'Existing predictions and reporting; no fitting or new posterior simulation.',
        'required_row_counts':COUNTS,
        'files':{str(p.relative_to(root)):digest(p) for p in sorted(set(paths))}}
    (root/BASE/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root',type=Path,default=ROOT)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--check',action='store_true')
    group.add_argument('--seal',action='store_true',help='Validate, regenerate new tables and bind reviewed inputs')
    args=parser.parse_args()
    root=args.article_root.resolve()
    try:
        data=validate(root,check_manifest=not args.seal)
        outputs=render(data)
        for name,expected in outputs.items():
            path=root/'tables/generated_tex'/name
            if args.check:
                require(path.read_text()==expected,f'Stale revision table: {name}')
            else:
                path.write_text(expected)
        if args.seal:
            seal(root)
            validate(root)
    except (OSError,ValueError,KeyError,OverflowError) as exc:
        print(f'Saved-output revision check failed: {exc}',file=sys.stderr)
        return 1
    print('Saved-output revision validated: 70 representations; 1,860 cases; two scales; '
          'quantile/interval counts, matching skill, settings and protected files; five table files '+
          ('match.' if args.check else 'generated.'))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
