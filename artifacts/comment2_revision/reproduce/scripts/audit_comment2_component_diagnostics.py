#!/usr/bin/env python3
"""Audit saved publication fit evidence without fitting or reading RData.

Pipeline completion, numerical safeguards, recorded stopping criteria and forecast
performance are separate evidence. Objective monotonicity is not an acceptance
test here. Missing diagnostics remain missing; historical terminal prose is not a
convergence certificate. All inputs read are hashed and verified unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import statistics
import sys


QUANTILES = (5, 20, 35, 50, 65, 80, 95)
KV = re.compile(r'([A-Za-z_][A-Za-z0-9_.]*)=([^\s]+)')
NUM = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def truth(value):
    return str(value).lower() in ('true', '1')


def kv(text):
    return dict(KV.findall(text))


def clean_json(value):
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


class Evidence:
    def __init__(self):
        self.files = {}
        self.missing = set()

    def text(self, path: Path):
        if not path.is_file():
            self.missing.add(str(path))
            return None
        if path.suffix.lower() in ('.rdata', '.rda', '.rds'):
            raise ValueError('Only saved text diagnostics may be read')
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f'Evidence changed during read: {path}')
        self.files[str(path)] = dict(path=str(path), bytes=len(data),
                                    sha256=hashlib.sha256(data).hexdigest())
        return data.decode('utf-8-sig', errors='replace')

    def rows(self, path: Path):
        text = self.text(path)
        return list(csv.DictReader(io.StringIO(text))) if text else []

    def verify(self):
        for entry in self.files.values():
            path = Path(entry['path'])
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError(f'Evidence changed during audit: {path}')


def tail_metrics(rows, warmup=0, tail_n=20):
    """Describe accepted post-warmup updates; do not impose invented tolerances."""
    eligible = [r for r in rows if (number(r.get('iter')) or 0) > warmup
                and not truth(r.get('frozen'))]
    tail = eligible[-tail_n:]
    result = {'tail_requested_n': tail_n, 'post_warmup_unfrozen_rows': len(eligible),
              'tail_rows': len(tail), 'warmup_excluded_through_iter': warmup}
    for field in ('elbo', 'sigma_exp', 'gamma_exp', 'state_norm_sq'):
        values = [number(r.get(field)) for r in tail]
        values = [v for v in values if v is not None]
        if values:
            denom = max(abs(statistics.median(values)), 1e-12)
            result[field + '_tail_first'] = values[0]
            result[field + '_tail_last'] = values[-1]
            result[field + '_tail_relative_range'] = (max(values) - min(values)) / denom
            result[field + '_tail_relative_drift'] = (values[-1] - values[0]) / denom
    return result


def classify_multivar(policy, progress, holds, terminal):
    """Classify the actual recorded stop separately from historical guard events."""
    last = progress[-1] if progress else {}
    final_iter = number(terminal.get('iterations_completed')) or number(last.get('iter'))
    budget = number(terminal.get('max_iter')) or number(policy.get('max_iter'))
    flags = {}
    basis = 'no explicit terminal criteria available'
    if holds and number(holds[-1].get('iter')) == final_iter:
        flags = {k: truth(v) for k, v in holds[-1].items() if k.startswith('conv_')}
        basis = 'terminal gamsig_hold flags'
    elif last and policy:
        mapping = [('conv_elbo', 'crit_elbo', 'elbo_tol'),
                   ('conv_state', 'crit_state_norm_sq', 'state_norm_sq_tol'),
                   ('conv_sigma', 'crit_sigma_exp', 'sigma_exp_tol'),
                   ('conv_gamma', 'crit_gamma_exp', 'gamma_exp_tol')]
        for name, metric, tolerance in mapping:
            a, b = number(last.get(metric)), number(policy.get(tolerance))
            if a is not None and b is not None:
                flags[name] = a < b
        updates, required = number(last.get('gamsig_update_iters')), number(policy.get('min_update_iters'))
        if updates is not None and required is not None:
            flags['conv_min_updates'] = updates >= required
        minimum = number(policy.get('min_total_iters'))
        if final_iter is not None and minimum is not None:
            flags['conv_min_iters'] = final_iter >= minimum
        basis = 'criteria reconstructed from logged values; printed precision applies'
    if terminal.get('converged') in ('true', 'false'):
        status = 'converged' if truth(terminal['converged']) else (
            'budget_limited' if terminal.get('convergence_reason') == 'iteration_budget_reached'
            else 'criteria_unmet')
        basis = 'explicit vb_fit_end record'
    elif len(flags) == 6 and all(flags.values()):
        # A held/frozen state can have zero changes without an evaluated joint
        # stopping condition. Do not turn those zeros into convergence evidence.
        if truth(last.get('frozen')):
            status = 'budget_limited' if final_iter is not None and budget is not None and final_iter >= budget else 'unknown'
            basis = 'terminal state frozen; reconstructed zero changes do not establish evaluated criteria'
        else:
            status = 'converged'
    elif len(flags) == 6 and not all(flags.values()):
        status = 'budget_limited' if final_iter is not None and budget is not None and final_iter >= budget else 'criteria_unmet'
    else:
        status = 'unknown'
    return dict(stopping_status=status, stopping_evidence_basis=basis,
                final_iter=final_iter, max_iter=budget,
                at_iteration_budget=(final_iter >= budget) if final_iter is not None and budget is not None else None,
                terminal_criteria=flags)


def parse_multivar(text, tail_n=20):
    lines = text.splitlines()
    progress = [kv(x) for x in lines if '[gamsig_progress]' in x]
    holds = [kv(x) for x in lines if '[gamsig_hold]' in x]
    policies = [kv(x) for x in lines if '[gamsig_policy]' in x]
    terminals = [kv(x) for x in lines if '[vb_fit_end]' in x]
    policy, terminal = (policies[-1] if policies else {}), (terminals[-1] if terminals else {})
    result = classify_multivar(policy, progress, holds, terminal)
    preflight = [kv(x) for x in lines if '[sampling_preflight]' in x and 'vb_terminal_guard' in x]
    guard = preflight[-1] if preflight else {}
    last = progress[-1] if progress else {}
    warmup = int(number(policy.get('warmup_freeze_iters')) or 0)
    result.update(tail_metrics(progress, warmup, tail_n))
    result.update(dict(progress_rows=len(progress), warmup_policy_available='warmup_freeze_iters' in policy,
                       terminal_progress=last, terminal_hold=holds[-1] if holds else {},
                       terminal_guard=guard, reported_guard_count=number(guard.get('guard_count')),
                       historical_state_guard_events=sum('[gamsig_state_guard]' in x for x in lines),
                       historical_finite_guard_events=sum('[gamsig_finite_guard]' in x for x in lines),
                       post_warmup_frozen_rows=sum((number(r.get('iter')) or 0) > warmup and truth(r.get('frozen')) for r in progress),
                       legacy_converged_phrase_present='VB converged:' in text,
                       final_frozen=truth(last['frozen']) if 'frozen' in last else None,
                       actual_update_iters=number(last.get('gamsig_update_iters')),
                       required_update_iters=number(policy.get('min_update_iters')),
                       terminal_guard_blocked=truth(guard['blocked']) if 'blocked' in guard else None))
    # The logged `blocked` condition is computed even for non-median lanes,
    # where the historical fail-fast terminal guard is inactive. Only an
    # emitted terminal_sampling_guard error establishes blocked sampling.
    actually_blocked = any('[terminal_sampling_guard]' in x for x in lines)
    result['terminal_sampling_actually_blocked'] = actually_blocked
    result['safeguard_status'] = ('sampling_blocked' if actually_blocked else
        'frozen_at_stop' if truth(guard.get('frozen')) or result['final_frozen'] else
        'historical_guard_recovered' if result['historical_state_guard_events'] or result['historical_finite_guard_events'] or result['reported_guard_count'] else
        'no_recorded_guard_event')
    if actually_blocked:
        result['criterion_status_before_guard'] = result['stopping_status']
        result['stopping_status'] = 'guarded'
    result['terminal_line_evidence'] = [x for x in lines if '[gamsig_hold]' in x][-1:] + [x for x in lines if '[sampling_preflight]' in x and 'vb_terminal_guard' in x][-1:]
    return result


def parse_summary(text):
    result = {}
    for line in text.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def parse_ndlm(summary, progress_text='', tail_n=20):
    values = parse_summary(summary)
    value = values.get('converged')
    status = ('converged' if truth(value) else 'budget_limited'
              if values.get('convergence_reason') == 'max_iter_reached' else 'criteria_unmet') if value in ('true', 'false') else 'unknown'
    rows = [kv(x) for x in progress_text.splitlines() if '[gamsig_progress]' in x]
    result = dict(stopping_status=status, stopping_evidence_basis='NDLM saved summary fields',
                  final_iter=number(values.get('iterations_completed')),
                  max_iter=number(values.get('max_iter')),
                  convergence_reason=values.get('convergence_reason'),
                  actual_update_iters=None, required_update_iters=None,
                  summary_fields={k: v for k, v in values.items() if k in (
                      'crit_elbo', 'crit_elbo_rel', 'sigma_usgs', 'sigma_nws', 'sigma_glofas',
                      'converged', 'convergence_reason', 'iterations_completed', 'max_iter') or k.startswith(('cov_diag.', 'stabilization.'))},
                  progress_rows=len(rows), terminal_progress=rows[-1] if rows else {})
    result.update(tail_metrics(rows, 0, tail_n))
    return result


def parse_univar(summary, legacy):
    """The historical legacy phrase and ELBO sequence do not supply joint flags."""
    values = parse_summary(summary)
    sequence = [number(line.split('=', 1)[1]) for line in summary.splitlines() if line.startswith('elbo_final=')]
    sequence = [x for x in sequence if x is not None]
    message = re.findall(r'VB converged:\s*(\d+) iterations', legacy)
    result = dict(stopping_status='unknown', stopping_evidence_basis='legacy summary omits terminal convergence criteria',
                  final_iter=int(message[-1]) if message else None,
                  legacy_converged_phrase_present=bool(message),
                  max_iter=None, actual_update_iters=None, required_update_iters=None,
                  objective_values_available=len(sequence),
                  summary_fields={k: values[k] for k in ('sigma', 'gamma', 'n_samp', 'quantile') if k in values})
    # The initial zero and unspecified warmup cannot certify terminal stability.
    tail = sequence[1:][-20:]
    if tail:
        result['elbo_tail_relative_range'] = (max(tail) - min(tail)) / max(abs(statistics.median(tail)), 1e-12)
    return result


def span(rows, field):
    values = [number(row.get(field)) for row in rows]
    values = [x for x in values if x is not None]
    return [min(values), max(values)] if values else None


def predictive_evidence(out: Path, evidence: Evidence):
    result = {}
    path = out / 'multivar_forecast_window_q50_summary.csv'
    if path.is_file():
        rows = evidence.rows(path)
        pairs = [(number(r.get('mu_q50')), number(r.get('usgs_future_withheld'))) for r in rows]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        widths = [number(r.get('upper_95')) - number(r.get('lower_95')) for r in rows
                  if number(r.get('upper_95')) is not None and number(r.get('lower_95')) is not None]
        result['q50_location'] = dict(path=str(path), rows=len(rows), mu_range=span(rows, 'mu_q50'),
            verification_range=span(rows, 'usgs_future_withheld'),
            mean_location_error=statistics.mean(a-b for a,b in pairs) if pairs else None,
            median_location_interval_width=statistics.median(widths) if widths else None,
            interval_kind='fitted q50 location uncertainty; not full predictive coverage')
    quantile_paths = sorted(out.glob('*_cutoff_window_quantiles.csv'))
    for path in quantile_paths:
        rows = [r for r in evidence.rows(path) if r.get('segment') == 'forecast']
        if not rows:
            continue
        widths = [number(r['q95'])-number(r['q05']) for r in rows
                  if number(r.get('q95')) is not None and number(r.get('q05')) is not None]
        result.setdefault('predictive_quantiles', []).append(dict(path=str(path), rows=len(rows),
            model_ids=sorted({r.get('model_id', '') for r in rows}), q50_range=span(rows, 'q50'),
            observed_range=span(rows, 'observed'), q05_range=span(rows, 'q05'), q95_range=span(rows, 'q95'),
            median_central90_width=statistics.median(widths) if widths else None,
            ordering_violations=sum(any(number(r.get(a)) is not None and number(r.get(b)) is not None
                                        and number(r[a]) > number(r[b]) for a,b in zip(
                                            ['q05','q20','q35','q50','q65','q80'], ['q20','q35','q50','q65','q80','q95'])) for r in rows)))
    for path in sorted(out.glob('*_forecast_quantile_synthesis_summary.csv')):
        result.setdefault('synthesis', []).extend(evidence.rows(path))
    audit = out / 'vb_latent_component_audit'
    for name in ('vb_component_diagnostic_summary.csv', 'vb_component_quantile_order_summary.csv'):
        path = audit / name
        if path.is_file():
            rows = evidence.rows(path)
            result[name.removesuffix('.csv')] = [{k: v for k,v in r.items() if k not in (
                'run_root', 'rdata_path', 'run_id', 'cutoff_date', 'spec')} for r in rows]
    return result


def run_rows(article: Path, evidence: Evidence):
    rows = []
    for raw in evidence.rows(article / 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv'):
        rows.append(dict(study='benchmark', cutoff=raw['cutoff'].replace('-', ''), label=raw['manuscript_label'],
                         family=raw['family'], variant='full' if raw['manuscript_label']=='exAL-M-T1' else raw['manuscript_label'],
                         run_id=raw.get('artifact_run_id') or raw['run_id'],
                         run_root=raw.get('artifact_run_root') or raw['run_root'],
                         manifest_pipeline_status='publication_selected'))
    for raw in evidence.rows(article / 'artifacts/he3_exdqlm_ablation_authoritative/he3_ablation_long.csv'):
        if raw['variant'] == 'full':
            continue
        rows.append(dict(study='component_removal', cutoff=raw['cutoff'], label=raw['manuscript_label'],
                         family='exdqlm_multivar', variant=raw['variant'], run_id=raw['resolved_run_id'],
                         run_root=raw['resolved_run_dir'], manifest_pipeline_status=raw['status']))
    for row in rows:
        row['run_key'] = ':'.join([row['study'], row['cutoff'], row['label']])
    return rows


def audit_run(run, evidence, tail_n):
    root = Path(run['run_root'])
    fits, out = [], root/'post/outputs'/run['run_id']
    if run['family'].startswith('ndlm'):
        summaries = sorted((root/'fit').glob('*/logs/*theory_summary.log'))
        if summaries:
            path = summaries[0]
            progress = path.parent/'ndlm_theory_progress.log'
            parsed = parse_ndlm(evidence.text(path) or '', evidence.text(progress) or '' if progress.is_file() else '', tail_n)
            parsed.update(quantile='gaussian', log_path=str(path))
            diagnostics = sorted((root/'fit/diagnostics').glob('*/*diagnostics.json'))
            if diagnostics:
                saved = json.loads(evidence.text(diagnostics[0]))
                parsed.update(numerical_diagnostics_status=saved.get('status'),
                              numerical_diagnostics_errors=saved.get('errors'),
                              numerical_diagnostics_warnings=saved.get('warnings'))
            fits.append(parsed)
        else:
            fits.append(dict(quantile='gaussian', stopping_status='unknown', stopping_evidence_basis='missing NDLM summary'))
    elif 'univar' in run['family']:
        by_q = {int(re.search(r'q=(\d+)', str(p)).group(1)):p
                for p in (root/'fit').rglob('univar_theory_summary.log') if re.search(r'q=(\d+)', str(p))}
        for q in QUANTILES:
            path = by_q.get(q)
            parsed = parse_univar(evidence.text(path) or '', evidence.text(path.parent/'univar_legacy.log') or '') if path else dict(
                stopping_status='unknown', stopping_evidence_basis='missing univariate summary')
            parsed.update(quantile=q, log_path=str(path) if path else None)
            fits.append(parsed)
    else:
        by_q = {int(re.search(r'q=(\d+)', str(p)).group(1)):p
                for p in (root/'fit').rglob('fit.log') if re.search(r'q=(\d+)', str(p))}
        for q in QUANTILES:
            path = by_q.get(q)
            parsed = parse_multivar(evidence.text(path) or '', tail_n) if path else dict(
                stopping_status='unknown', stopping_evidence_basis='missing multivariate log')
            parsed.update(quantile=q, log_path=str(path) if path else None)
            if path:
                health = path.parent.parent/'outputs/diagnostics/vb_iteration/fit_iteration_health_summary.csv'
                if health.is_file():
                    health_rows = evidence.rows(health)
                    warmup = parsed.get('warmup_excluded_through_iter', 0)
                    accepted = [r for r in health_rows if (number(r.get('iter')) or 0)>warmup and not truth(r.get('frozen'))]
                    parsed['iteration_health_rows'] = len(health_rows)
                    parsed['post_warmup_health_flagged_rows'] = sum((number(r.get('health_flag_n')) or 0)>0 for r in accepted)
                    parsed['terminal_health_flag_n'] = number(health_rows[-1].get('health_flag_n')) if health_rows else None
            fits.append(parsed)
    for row in fits:
        row.update({k:run[k] for k in ('run_key','study','cutoff','label','variant','run_id')})
    run = dict(run, run_root_exists=root.is_dir(), fit_count=len(fits),
               fit_status_counts=dict(Counter(r['stopping_status'] for r in fits)),
               predictive_evidence=predictive_evidence(out, evidence))
    return run, fits


def comparisons(article, evidence, runs):
    records = []
    for name in ('benchmark_crps_horizon_summary.csv', 'he3_ablation_crps_horizon_summary.csv'):
        records.extend(evidence.rows(article/'tables/generated_tex'/name))
    lookup = {(r['cutoff'],r['row_label'],int(r['horizon_days'])):number(r['mean_crps']) for r in records}
    result = []
    for run in runs:
        for horizon in (8,28):
            key = run['cutoff'],run['label'],horizon
            score = lookup.get(key)
            # HE3's full label is displayed differently, but benchmark full is identical.
            if score is None:
                continue
            raw, full = lookup.get((run['cutoff'],'RAW-GLOFAS',horizon)), lookup.get((run['cutoff'],'exAL-M-T1',horizon))
            nws = lookup.get((run['cutoff'],'RAW-NWS',horizon))
            result.append(dict(run_key=run['run_key'],study=run['study'],cutoff=run['cutoff'],label=run['label'],
                horizon_days=horizon,mean_crps=score,raw_glofas_crps=raw,raw_nws_crps=nws,full_crps=full,
                delta_vs_raw_glofas=score-raw if raw is not None else None,
                ratio_vs_raw_glofas=score/raw if raw else None,
                delta_vs_full=score-full if full is not None else None,ratio_vs_full=score/full if full else None,
                delta_vs_raw_nws=score-nws if nws is not None else None))
    return result


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(clean_json(v),sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1]/'Evironmetrics---REVISED-DOC-Corrected-2')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--tail-iterations', type=int, default=20)
    args = parser.parse_args()
    out, article = args.output_dir.resolve(), args.article_root.resolve()
    if out.exists():
        parser.error('--output-dir must be new; existing audit evidence is never overwritten')
    if args.tail_iterations < 2:
        parser.error('--tail-iterations must be at least two')
    evidence = Evidence()
    runs, fits = [], []
    selected = run_rows(article, evidence)
    if Counter(r['study'] for r in selected) != Counter(benchmark=45, component_removal=25):
        parser.error('Expected the current 45 benchmark and 25 component-removal identities')
    if len({r['run_key'] for r in selected}) != len(selected):
        parser.error('Duplicate publication run identities')
    for run in selected:
        result, lanes = audit_run(run, evidence, args.tail_iterations)
        runs.append(result)
        fits.extend(lanes)
    compare = comparisons(article, evidence, runs)
    evidence.text(Path(__file__).resolve())
    evidence.verify()
    cases = [r for r in runs if (r['cutoff'], r['label']) in (
        ('20220511','exAL-M-noTF'),('20220511','exAL-M-T1'),('20221225','exAL-M-T1-noH2'),
        ('20221225','exAL-M-T1'),('20211112','exAL-M-T0'),('20210123','N-M-T1'))]
    summary = dict(created_utc=datetime.now(timezone.utc).isoformat(), scope='saved publication component/fitting evidence only',
        article_root=str(article),tail_iterations=args.tail_iterations,
        invocation=[sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]],
        run_count=len(runs),benchmark_runs=sum(r['study']=='benchmark' for r in runs),
        component_removal_runs=sum(r['study']=='component_removal' for r in runs),
        fit_count=len(fits),fit_status_counts=dict(Counter(f['stopping_status'] for f in fits)),
        model_comparison_rows=len(compare),source_file_count=len(evidence.files),
        source_bytes=sum(r['bytes'] for r in evidence.files.values()),source_files_unchanged=True,
        numerical_outputs_modified=False,rdata_or_rds_read=False,
        interpretation='Recorded fit stopping and safeguards are evidence, not proof of model validity or a causal decomposition of component value.',
        missing_evidence=sorted(evidence.missing))
    out.mkdir(parents=True)
    for name, data in [('run_ledger',runs),('fit_ledger',fits),('model_comparisons',compare),('striking_cases',cases),('summary',summary),
                       ('source_manifest',dict(files=sorted(evidence.files.values(),key=lambda x:x['path']),missing=sorted(evidence.missing)))]:
        (out/(name+'.json')).write_text(json.dumps(clean_json(data),indent=2,sort_keys=True,allow_nan=False)+'\n')
    for name, rows in [('run_ledger',runs),('fit_ledger',fits),('model_comparisons',compare)]:
        write_csv(out/(name+'.csv'),rows)
    reduced = [r for r in compare if r['study']=='component_removal' and r['horizon_days']==28]
    text = ['Saved-fit diagnostic audit for major comment 2','',
        f'{len(runs)} selected run identities; {len(fits)} recorded/expected fits; {len(compare)} existing score comparisons.',
        'Stopping classifications: '+json.dumps(summary['fit_status_counts'],sort_keys=True),
        f'All {sum(r["delta_vs_raw_glofas"]>0 for r in reduced)}/{len(reduced)} component-removal 28-day cells are worse than RAW-GLOFAS.',
        '', 'Read run_ledger/fit_ledger and striking_cases for the saved evidence and exact source paths.',
        'The historical phrase "VB converged" is not used as a convergence certificate.',
        'Post-warmup stability summaries exclude planned warmup and frozen iterations when recorded.',
        'A logged blocked condition alone does not prove blocked sampling: non-median guards can be inactive.',
        'Univariate legacy summaries without explicit joint criteria remain unknown.',
        'A missing component decomposition for noTF reflects an existing transfer-specific helper limitation.',
        'Fitted-location intervals are not predictive intervals; no calibration claim is made.',
        'No monotonic objective criterion or arbitrary new stability pass/fail threshold is imposed.',
        'A budget-limited fit is not declared invalid, and a converged fit is not guaranteed predictive skill.',
        'All source files were checked unchanged; no fitting, RData reads or numerical-output writes occurred.','']
    (out/'README.txt').write_text('\n'.join(text))
    print(json.dumps(summary,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
