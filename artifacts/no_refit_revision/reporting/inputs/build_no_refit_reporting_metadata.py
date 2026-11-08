#!/usr/bin/env python3
"""Freeze and derive reporting metadata only; never load fitted binary objects.

First collection reads only selected configurations, small text/CSV exports and
primary source text. Later generation/checks use the portable ``inputs`` subtree.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
from typing import Any


STATE_KEYS = ('df_t', 'df_s1', 'df_s2', 'df_s67', 'df_discrep',
              'df_trans', 'df_covs', 'lambda')
BASE_FEATURES = {'PPT': 'Precipitation', 'SOIL': 'Soil Moisture', 'PCA': 'PC1'}
LEGACY_LABEL_STATE = {'Precipitation': 23, 'Soil Moisture': 24, 'PC1': 25,
                      'Intercept': 26, 'Lag1': 27, 'Lag2': 28,
                      'Lag3': 29, 'Lag4': 30, 'Lag5': 31}
EXPECTED_FEATURES = ('PPT', 'SOIL', 'PCA', 'PPT_sq', 'SOIL_sq', 'PPT_x_SOIL',
                     'PPT_lag1', 'PPT_lag2', 'PPT_lag3',
                     'SOIL_lag1', 'SOIL_lag2', 'SOIL_lag3')
MANIFEST_PATH = 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv'
COEFFICIENT_PATH = 'artifacts/representative_selected_model_2022_12_25/covariate_effects_summary.csv'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> str:
    number = Decimal(str(value))
    require(number.is_finite(), 'Nonfinite numerical setting')
    return format(number.normalize(), 'f')


def numeric_tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): numeric_tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [numeric_tree(v) for v in value]
    if value is None or isinstance(value, (bool, str)):
        return value
    return canonical(value)


def exact_tex(value: str, *, complement: bool = True) -> str:
    """Format exact source decimals without rounding through binary floats."""
    number = Decimal(value)
    require(number.is_finite(), 'Nonfinite display setting')
    if number == number.to_integral_value():
        return str(int(number))
    if complement and Decimal('0.9') < number < 1:
        delta = (Decimal(1) - number).normalize()
        sign, digits, exponent = delta.as_tuple()
        require(not sign, 'Invalid discount complement')
        coefficient = int(''.join(str(d) for d in digits))
        body = '10^{' + str(exponent) + '}'
        if coefficient != 1:
            body = str(coefficient) + r'\times ' + body
        return r'1-' + body
    numerator, denominator = number.as_integer_ratio()
    return r'\frac{' + str(numerator) + '}{' + str(denominator) + '}'


def csv_bytes(rows: list[dict[str, Any]], fields: list[str] | None = None) -> bytes:
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields or list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def model_key(family: str) -> str:
    if family == 'ndlm_univar_keep':
        return 'ndlm_univar'
    if family.startswith('ndlm_main'):
        return 'ndlm_main'
    return 'exdqlm_univar' if 'univar' in family else 'exdqlm_multivar'


def source_record(path: Path, *, root: Path | None = None) -> dict[str, str]:
    data = path.read_bytes()
    return {'path': str(path.relative_to(root) if root else path), 'sha256': digest(data)}


def history_count(row: dict[str, str], model: str) -> tuple[int, dict[str, str]]:
    root = Path(row['artifact_run_root'])
    if model == 'exdqlm_multivar':
        candidates = [root / 'fit/exdqlm_multivar' / row['forecast_transfer_mode'] / 'q=50/outputs/diagnostics/transfer_design/transfer_feature_metadata.csv',
                      root / 'fit/q=50/outputs/diagnostics/transfer_design/transfer_feature_metadata.csv']
        available = [path for path in candidates if path.is_file()]
        require(len(available) <= 1, 'Ambiguous selected-run feature metadata paths')
        if not available:
            path = root / 'post/outputs' / row['artifact_run_id'] / 'timestamps.csv'
            dates = [datetime.strptime(r['x'], '%Y-%m-%d').date() for r in read_csv(path)]
            require(bool(dates) and dates[-1].strftime('%Y%m%d') == row['cutoff'],
                    'Historical date export does not end at its selected origin')
            require(all(b - a == timedelta(days=1) for a, b in zip(dates, dates[1:])),
                    'Historical date export is not contiguous')
            return len(dates), source_record(path)
        path = available[0]
        entries = read_csv(path)
        counts = {int(entry['history_n']) for entry in entries}
        require(len(counts) == 1, 'Inconsistent historical count')
        return counts.pop(), source_record(path)
    subpath = {'ndlm_main': 'fit/ndlm_main/logs/ndlm_theory_summary.log',
               'ndlm_univar': 'fit/ndlm_univar/logs/ndlm_univar_theory_summary.log',
               'exdqlm_univar': 'fit/exdqlm_univar/q=50/logs/univar_theory_summary.log'}[model]
    path = root / subpath
    match = re.search(r'^T=(\d+)$', path.read_text(), re.M)
    require(match is not None, 'Saved history count unavailable')
    return int(match.group(1)), source_record(path)


def validate_primary_sources(workflow: Path) -> list[dict[str, Any]]:
    checks = [
        ('R/unified/stages/stage_fit.R',
         ['NDLM_FORECAST_IW_EPSILON0 = if', 'DISC_W_FORECAST_COV_EPSILON',
          '"state_evolution", "df_covs"'], 'Configuration-to-worker adapter'),
        ('R/unified/families/ndlm_main/08_vb_cavi_exact.R',
         ['epsilon0 <- as.numeric(inputs$T)', 'd_k + dof_offset + epsilon0'],
         'Gaussian multivariate null epsilon resolves to actual historical T'),
        ('R/unified/families/ndlm_main/05_fitloop.R', ['ndlm_exact_fit(inputs = inputs'],
         'Active Gaussian multivariate implementation'),
        ('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r',
         ['df.discrep <- df.discrep*rep(df,J)',
          'else TT', 'Gx[1, 2:ppx, ] <- as.matrix(t(X))'],
         'Discrepancy multiplier and transfer transition'),
        ('R/environmetrics/40_figures_smoke_fast.R',
         ['component_idx <- 23:31', 'draws <- scale_fac * as.numeric(theta_obj$samp_theta[comp, tt, ])'],
         'Current endpoint draw-summary exporter'),
        ('R/environmetrics/02_helpers_core.R', ['"26" = "Intercept"', '"31" = "Lag5"'],
         'Original label-to-state identity for preserved exports'),
        ('R/unified/families/shared_input_helpers.R', ['family_shared_sd_scale_history_future'],
         'Historical-SD design scaling'),
        ('R/unified/families/ndlm_univar/03_filter_forecast_fit.R',
         ['ndlm_univar'], 'Univariate Gaussian forecast implementation'),
    ]
    evidence = []
    for relative, tokens, purpose in checks:
        path = workflow / relative
        text = path.read_text()
        for token in tokens:
            require(token in text, 'Primary source contract changed: ' + relative)
        evidence.append({**source_record(path, root=workflow), 'purpose': purpose,
                         'anchors': [{'token': token, 'line': text[:text.index(token)].count('\n') + 1}
                                     for token in tokens]})
    return evidence


def collect_inputs(article: Path, workflow: Path, original_workflow: Path) -> dict[str, bytes]:
    import yaml  # Used only for collection; portable replay needs the standard library.

    class DecimalLoader(yaml.SafeLoader):
        pass
    DecimalLoader.add_constructor('tag:yaml.org,2002:float',
                                 lambda loader, node: Decimal(loader.construct_scalar(node)))
    rows = read_csv(article / MANIFEST_PATH)
    require(len(rows) == 45, 'Expected 45 authoritative model-origin cases')
    require(len({(r['cutoff'], r['manuscript_label']) for r in rows}) == 45,
            'Repeated selected identity')
    sources = [source_record(article / MANIFEST_PATH)]
    settings = []
    for row in rows:
        config_path = Path(row['resolved_config_path'])
        before = config_path.read_bytes()
        config = yaml.load(before, Loader=DecimalLoader)
        key = model_key(row['family'])
        state = json.loads(row['state_evolution_json'], parse_float=Decimal)
        configured_state = config['models'][key]['state_evolution']
        require(state == configured_state, 'Selected state settings differ from resolved configuration')
        require(set(state) <= set(STATE_KEYS), 'Unknown state setting: explicit schema required')
        prior = json.loads(row['prior_json'], parse_float=Decimal)
        historical_t, count_source = history_count(row, key)
        settings.append({'origin': row['cutoff'], 'model_id': row['manuscript_label'],
                         'family': key, 'run_id': row['run_id'], 'artifact_run_id': row['artifact_run_id'],
                         'config_sha256': digest(before), 'config_path': str(config_path),
                         'state': numeric_tree(state), 'prior': numeric_tree(prior),
                         'fit_quantiles': numeric_tree(config['fit']['quantiles']),
                         'actual_fit_probabilities': ['0.5'] if key.startswith('ndlm') else numeric_tree(config['fit']['quantiles']),
                         'history_n': historical_t, 'history_count_source': count_source,
                         'implementation_mode': row['implementation_mode']})
        require(config_path.read_bytes() == before, 'Configuration changed during collection')
        sources += [{'path': str(config_path), 'sha256': digest(before)}, count_source]
    reference = next(row for row in rows if row['cutoff'] == '20221225' and row['manuscript_label'] == 'exAL-M-T1')
    output = Path(reference['artifact_run_root']) / 'post/outputs' / reference['artifact_run_id']
    feature_path = Path(reference['artifact_run_root']) / 'fit/exdqlm_multivar/keep/q=50/outputs/diagnostics/transfer_design/transfer_feature_metadata.csv'
    features = read_csv(feature_path)
    require(tuple(r['feature_name'] for r in features) == EXPECTED_FEATURES, 'Actual feature order changed')
    design_path = output / 'data_cbind_tY_X.csv'
    design = read_csv(design_path)
    require(len(design) == 12995, 'Unexpected representative historical time index')
    factors = {name: format(statistics.stdev(float(r[name]) for r in design), '.17g')
               for name in EXPECTED_FEATURES}
    require(all(abs(Decimal(factors[name]) - 1) <= Decimal('1e-12') for name in BASE_FEATURES),
            'Displayed base-feature export scaling is no longer unit SD')
    coefficient_bytes = (article / COEFFICIENT_PATH).read_bytes()
    require((output / 'tables/covariate_effects_summary.csv').read_bytes() == coefficient_bytes,
            'Representative coefficient export is not identical to selected output')
    sources += [source_record(feature_path), source_record(design_path),
                source_record(article / COEFFICIENT_PATH),
                source_record(output / 'tables/covariate_effects_summary.csv')]
    source_evidence = validate_primary_sources(workflow)
    old_path = original_workflow / 'R/environmetrics/40_figures_multivar_only.R'
    new_path = workflow / 'R/environmetrics/40_figures_multivar_only.R'
    old, new = old_path.read_text(), new_path.read_text()
    old_helper = old[old.index('safe_diag_sd <- function'):old.index('safe_linear_sd <- function')]
    new_helper = new[new.index('safe_diag_sd <- function'):new.index('safe_linear_sd <- function')]
    restored = new.replace(new_helper, old_helper, 1).replace(
        'safe_diag_sd(sC_hist, psi_hist_idx[k], n_hist, time_indices = hist_idx)',
        'safe_diag_sd(sC_hist, psi_hist_idx[k], n_hist)', 1)
    require(restored == old and new != old, 'Diagnostic source repair exceeds declared helper/caller scope')
    proof = {'original_source': source_record(old_path), 'repaired_source': source_record(new_path),
             'only_changes': ['safe_diag_sd adds optional explicit time indices',
                              'historical coefficient caller supplies hist_idx'],
             'all_other_source_text_identical': True, 'new_fits': False,
             'numerical_band_regeneration': False}
    return {
        'settings_records.json': json_bytes(settings),
        'feature_metadata.csv': feature_path.read_bytes(),
        'covariate_effects_summary.csv': coefficient_bytes,
        'design_scale_factors.json': json_bytes({'factors': factors,
                                                'design_source': source_record(design_path)}),
        'source_evidence.json': json_bytes(source_evidence),
        'source_registry.json': json_bytes(sources),
        'source_scope_proof.json': json_bytes(proof),
        'build_no_refit_reporting_metadata.py': Path(__file__).read_bytes(),
    }


def derived_products(inputs: dict[str, bytes]) -> dict[str, bytes]:
    settings = json.loads(inputs['settings_records.json'])
    features = list(csv.DictReader(io.StringIO(inputs['feature_metadata.csv'].decode())))
    endpoints = list(csv.DictReader(io.StringIO(inputs['covariate_effects_summary.csv'].decode())))
    scales = json.loads(inputs['design_scale_factors.json'])['factors']
    require(len(settings) == 45 and len(features) == 12 and len(endpoints) == 27,
            'Wrong reporting input dimensions')
    require(len({(r['origin'], r['model_id']) for r in settings}) == 45,
            'Repeated reporting model-origin identity')
    require(tuple(r['feature_name'] for r in features) == EXPECTED_FEATURES,
            'Actual feature order changed')
    configured = []
    reference_rows = []
    for record in settings:
        state = record['state']
        row = {key: record[key] for key in ['origin', 'model_id', 'family', 'run_id',
                                          'artifact_run_id', 'config_sha256', 'implementation_mode']}
        row.update({key: state.get(key, '') for key in STATE_KEYS})
        row['history_n'] = str(record['history_n'])
        row['fit_probabilities'] = '|'.join(record['actual_fit_probabilities'])
        row['fit_probability_semantics'] = ('single_Gaussian_distribution_fit_with_median_compatibility_tag'
                                             if record['family'].startswith('ndlm')
                                             else 'separate_quantile_specific_fits')
        row['df_discrep_status'] = 'configured_multiplier' if 'df_discrep' in state else 'not_applicable_univariate'
        for component in ('df_t', 'df_s1', 'df_s2', 'df_s67'):
            row['effective_discrep_' + component] = (canonical(Decimal(state[component]) * Decimal(state['df_discrep']))
                                                     if 'df_discrep' in state else '')
        covariance = record['prior'].get('forecast_cov')
        if record['family'] == 'ndlm_main':
            require(covariance is not None, 'Gaussian covariance specification absent')
            epsilon = covariance.get('epsilon')
            row['epsilon_configured'] = 'null' if epsilon is None else canonical(epsilon)
            row['epsilon_effective'] = str(record['history_n']) if epsilon is None else canonical(epsilon)
            row['epsilon_status'] = 'adapter_default_historical_T' if epsilon is None else 'configured'
            row['covariance_family'] = 'Gaussian_multivariate_inverse_Wishart'
            row['c'] = canonical(covariance['c_factor'])
        elif record['family'] == 'exdqlm_multivar':
            require(covariance is not None and covariance.get('epsilon') is not None,
                    'Unresolved multivariate covariance default')
            row['epsilon_configured'] = canonical(covariance['epsilon'])
            row['epsilon_effective'] = canonical(covariance['epsilon'])
            row['epsilon_status'] = 'configured'
            row['covariance_family'] = 'quantile_multivariate_inverse_Wishart'
            row['c'] = canonical(covariance['c_factor'])
        else:
            row.update(epsilon_configured='', epsilon_effective='',
                       epsilon_status='not_applicable_univariate_forecast_formulation',
                       covariance_family='univariate_forecast_formulation', c='')
        row['prior_numeric_json'] = json.dumps(record['prior'], sort_keys=True, separators=(',', ':'))
        configured.append(row)
        if record['model_id'] == 'exAL-M-T1':
            view = dict(row)
            for key in (*STATE_KEYS, 'epsilon_effective', 'c'):
                view[key + '_tex'] = exact_tex(view[key])
            reference_rows.append(view)
    dictionary = []
    source_hash = digest(inputs['feature_metadata.csv'])
    for feature in features:
        index = int(feature['feature_index'])
        require(index == len(dictionary) + 1, 'Non-contiguous actual feature order')
        dictionary.append({'feature_index': str(index), 'actual_feature_name': feature['feature_name'],
                           'state_index': str(22 + index), 'run_id': next(r['run_id'] for r in settings if r['origin'] == '20221225' and r['model_id'] == 'exAL-M-T1'),
                           'time_index': '12995', 'state_date': '2022-12-25',
                           'scale': 'historical_standard_deviation_without_centering',
                           'export_scale_factor': scales[feature['feature_name']],
                           'availability_status': 'available_existing_summary' if index <= 9 else 'unavailable_not_exported',
                           'feature_metadata_sha256': source_hash})
    by_state = {int(r['state_index']): r for r in dictionary}
    require(set(by_state) == set(range(23, 35)), 'Incomplete 12-feature dictionary')
    corrected = []
    source_hash = digest(inputs['covariate_effects_summary.csv'])
    for endpoint in endpoints:
        require(endpoint['covariate'] in LEGACY_LABEL_STATE, 'Unrecognized original endpoint row')
        state = LEGACY_LABEL_STATE[endpoint['covariate']]
        feature = by_state[state]
        require(endpoint['quantile'] in ('5', '50', '95') and endpoint['time_index'] == '12995',
                'Unexpected endpoint quantile/time identity')
        corrected.append({'original_row_key': endpoint['covariate'] + '|' + endpoint['quantile'],
                          'original_label': endpoint['covariate'],
                          'feature_index': feature['feature_index'],
                          'actual_feature_name': feature['actual_feature_name'], 'state_index': str(state),
                          'run_id': feature['run_id'], 'time_index': endpoint['time_index'],
                          'state_date': '2022-12-25', 'quantile': endpoint['quantile'],
                          'center_kind': 'approximate_VB_state_draw_mean',
                          'center': endpoint['center'], 'lower': endpoint['q2_5'], 'upper': endpoint['q97_5'],
                          'source_sha256': source_hash, 'export_scale_factor': feature['export_scale_factor'],
                          'availability_status': 'available_existing_summary',
                          'interval_estimand': 'empirical_pointwise_95pct_VB_state_draw_interval'})
    require(len({(r['state_index'], r['quantile']) for r in corrected}) == 27,
            'Duplicate or missing derived endpoint row')
    require(all(Decimal(r['lower']) <= Decimal(r['center']) <= Decimal(r['upper']) for r in corrected),
            'Invalid source interval')
    estimands = [
        {'summary': 'transfer_feature_loading', 'center': 'mean',
         'interval': 'empirical_2.5th_97.5th_percentiles_of_approximate_VB_state_draws',
         'time': 'psi_T; T=12995; 2022-12-25',
         'interpretation': 'conditional_dynamic_loading_on_SD_scaled_feature; no_total_or_causal_response'},
        {'summary': 'source_skewness_gamma', 'center': 'median',
         'interval': 'empirical_2.5th_97.5th_percentiles_of_approximate_VB_factor_draws',
         'time': 'source_specific_static_parameter', 'interpretation': 'approximate_parameter_posterior'},
        {'summary': 'source_scale_sigma', 'center': 'median',
         'interval': 'empirical_2.5th_97.5th_percentiles_of_approximate_VB_factor_draws',
         'time': 'source_specific_static_parameter', 'interpretation': 'approximate_parameter_posterior'},
    ]
    gates = {'status': 'VALIDATED_REPORTING_ONLY', 'new_fits': False, 'new_simulations': False,
             'metadata_counts': {'selected_settings': 45, 'feature_dictionary': 12, 'existing_endpoint_summaries': 27},
             'original_numeric_strings_preserved': True,
             'displayed_base_rows_unchanged': True,
             'N11a': 'SOURCE_ONLY_REPAIR_WITH_DEDICATED_REGRESSION',
             'N11b': 'OPTIONAL_SKIPPED_MISSING_COVARIANCE',
             'N11b_scope': 'Listed selected exports lack recoverable late-time coefficient covariance/draw arrays; no numerical band reconstruction performed.',
             'missing_endpoint_states': [32, 33, 34],
             'approximation_accuracy_experiment': 'DEFERRED_NEW_INFERENCE'}
    return {'configured_settings.csv': csv_bytes(configured),
            'reference_settings.csv': csv_bytes(reference_rows),
            'feature_state_dictionary.csv': csv_bytes(dictionary),
            'corrected_endpoint_summaries.csv': csv_bytes(corrected),
            'parameter_estimands.csv': csv_bytes(estimands),
            'source_gates.json': json_bytes(gates),
            'README.txt': ("Reporting-only metadata derived from frozen selected records.\n"
                           "No fitted binary state objects, model fits or simulation are used.\n"
                           "inputs/ contains portable, numeric-only source snapshots. Original paths are provenance.\n"
                           "Configured and effective values are separate; Gaussian null epsilon is historical T.\n"
                           "df_discrep is a multiplier; effective component discounts are exact products.\n"
                           "The 12-feature dictionary does not invent three unexported endpoint summaries.\n"
                           "All 27 relabelled source centers and interval endpoints retain their original strings.\n"
                           "Original coefficient source and all article wrappers remain unchanged.\n"
                           "Optional historical coefficient-window bands are not reconstructed.\n\n"
                           "Portable metadata replay from the article checkout (fresh output directory):\n"
                           "  python3 -B artifacts/no_refit_revision/reporting/inputs/build_no_refit_reporting_metadata.py --inputs-dir artifacts/no_refit_revision/reporting/inputs --output-dir /tmp/no_refit_reporting_replay\n"
                           "Read-only metadata check:\n"
                           "  python3 -B artifacts/no_refit_revision/reporting/inputs/build_no_refit_reporting_metadata.py --output-dir artifacts/no_refit_revision/reporting --check\n").encode()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path)
    parser.add_argument('--workflow-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--original-workflow-root', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--inputs-dir', type=Path, help='Portable replay from an existing frozen inputs subtree')
    parser.add_argument('--check', action='store_true', help='Read-only validation of existing derived products')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if args.inputs_dir or args.check:
        input_dir = (args.inputs_dir or output / 'inputs').resolve()
        inputs = {p.name: p.read_bytes() for p in input_dir.iterdir() if p.is_file()}
    else:
        require(args.article_root is not None and args.original_workflow_root is not None,
                'First collection needs article and original workflow roots')
        require(not output.exists(), 'First collection requires a fresh output directory')
        inputs = collect_inputs(args.article_root.resolve(), args.workflow_root.resolve(),
                                args.original_workflow_root.resolve())
    products = derived_products(inputs)
    all_files = {'inputs/' + name: value for name, value in inputs.items()} | products
    manifest = {'schema': 'no_refit_reporting_v1', 'no_fits': True,
                'files': {name: digest(value) for name, value in sorted(all_files.items())}}
    all_files['reporting_manifest.json'] = json_bytes(manifest)
    if args.check:
        for name, value in all_files.items():
            require((output / name).read_bytes() == value, 'Reporting artifact differs: ' + name)
        print('Validated 45 settings, 12 feature identities, 27 unchanged endpoint summaries; read-only.')
    else:
        output.mkdir(parents=True, exist_ok=False)
        for name, value in all_files.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        print('Wrote deterministic no-fit reporting bundle: ' + str(output))


if __name__ == '__main__':
    main()
