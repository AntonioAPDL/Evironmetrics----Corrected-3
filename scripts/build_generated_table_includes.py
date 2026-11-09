#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from article_asset_manifest import load_manifest, manifest_path
from article_repo_layout import TABLE_TEX_FILENAMES, build_layout

CUTOFF_ORDER = ['20210123', '20211112', '20211221', '20220511', '20221225']
MODEL_ORDER = ['N-U-T1', 'N-M-T0', 'N-M-T1', 'AL-U-T1', 'AL-M-T0', 'AL-M-T1', 'exAL-U-T1', 'exAL-M-T0', 'exAL-M-T1']
BENCHMARK_ROW_ORDER = ['RAW-GLOFAS', 'RAW-NWS'] + MODEL_ORDER
BENCHMARK_LONG_RAW_ROW_ORDER = ['RAW-GLOFAS']
BENCHMARK_SHORT_RAW_ROW_ORDER = ['RAW-GLOFAS', 'RAW-NWS']
QUANTILE_ORDER = ['5', '20', '35', '50', '65', '80', '95']
SOURCE_ORDER = ['USGS', 'GLOFAS', 'NWS']
COMPONENT_COVARIATES = ['Precipitation', 'Soil Moisture', 'PC1']
COMPONENT_QUANTILES = ['5', '50', '95']
COMPONENT_LABELS = {'PC1': 'First GDPC factor'}
HE4_MODEL_ORDER = ['exAL-M-T1', 'AL-M-T1', 'exAL-U-T1', 'AL-U-T1']
HE4_TAU_LABELS = ['q0.05', 'q0.20', 'q0.35', 'q0.50', 'q0.65', 'q0.80', 'q0.95']
HE4_TAU_COLUMNS = ['q0.05', 'q0.20', 'q0.35', 'q0.50', 'q0.65', 'q0.80', 'q0.95']
RAW_MODEL_MAP = {'RAW-GLOFAS': 'glofas_ensemble', 'RAW-NWS': 'nws_nwm_ensemble'}
DISPLAY_DIGITS = 5
DISPLAY_TIE_TOLERANCE = 0.5 * 10 ** (-DISPLAY_DIGITS)
RUN_SLUG_MAP = {
    '20210123': '20210123_exal_m_t1',
    '20211112': '20211112_exal_m_t1',
    '20211221': '20211221_exal_m_t1',
    '20220511': '20220511_exal_m_t1',
    '20221225': '20221225_exal_m_t1',
}
BENCHMARK_LONG_HORIZON_DAYS = 28
BENCHMARK_NWS_COMMON_HORIZON_DAYS = 8


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def preserved_external_manifest_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = read_csv(path)
    return [
        row for row in rows
        if row.get('table_label', '').startswith('tab:he3_')
    ]


def fmt_num(value: str | float, digits: int) -> str:
    return f'{float(value):.{digits}f}'


def fmt_display(value: str | float) -> str:
    return fmt_num(value, DISPLAY_DIGITS)


def fmt_ci(row: dict[str, str], digits: int) -> str:
    return f'$[{fmt_num(row["q2_5"], digits)},\ {fmt_num(row["q97_5"], digits)}]$'


def mean_crps_for_leads(
    rows: list[dict[str, str]],
    *,
    model_key: str,
    model_value: str,
    horizon_days: int,
    source_path: Path,
) -> float:
    selected = [
        row for row in rows
        if row.get(model_key) == model_value and 1 <= int(row['lead_day']) <= horizon_days
    ]
    leads = sorted(int(row['lead_day']) for row in selected)
    expected = list(range(1, horizon_days + 1))
    if leads != expected:
        raise ValueError(
            f'Expected leads {expected} for {model_key}={model_value} in {source_path}; got {leads}'
        )
    values = [float(row['crps']) for row in sorted(selected, key=lambda row: int(row['lead_day']))]
    return sum(values) / len(values)


def build_benchmark_rows(
    article_root: Path,
    table_cfg: dict,
    *,
    horizon_days: int,
    raw_row_order: list[str],
    table_label: str,
) -> tuple[list[str], list[str], list[str], list[dict[str, str]], list[dict[str, str]]]:
    manifest_rows = read_csv(article_root / table_cfg['sources']['bayesian_manifest_csv'])
    bayes = {(row['manuscript_label'], row['cutoff']): row for row in manifest_rows}
    raw_rows: dict[tuple[str, str], float] = {}
    source_rows: list[dict[str, str]] = []
    five_root = article_root / table_cfg['sources']['five_run_source_root']
    for cutoff in CUTOFF_ORDER:
        slug = RUN_SLUG_MAP[cutoff]
        per_time_path = five_root / slug / 'crps_forecast_per_time.csv'
        crps_rows = read_csv(per_time_path)
        for raw_label in raw_row_order:
            model_id = RAW_MODEL_MAP[raw_label]
            raw_rows[(raw_label, cutoff)] = mean_crps_for_leads(
                crps_rows,
                model_key='model_id',
                model_value=model_id,
                horizon_days=horizon_days,
                source_path=per_time_path,
            )
            source_rows.append({
                'table_label': table_label,
                'row_label': raw_label,
                'cutoff': cutoff,
                'horizon_days': str(horizon_days),
                'source_class': 'raw_forecast_product',
                'source_path': str(per_time_path.relative_to(article_root)),
                'model_selector': f'model_id={model_id}',
                'mean_crps': f'{raw_rows[(raw_label, cutoff)]:.17g}',
            })

    values_by_cutoff: dict[str, dict[str, float]] = {cutoff: {} for cutoff in CUTOFF_ORDER}
    for cutoff in CUTOFF_ORDER:
        for raw_label in raw_row_order:
            values_by_cutoff[cutoff][raw_label] = raw_rows[(raw_label, cutoff)]
        for label in MODEL_ORDER:
            row = bayes[(label, cutoff)]
            per_time_path = Path(row['score_source']).with_name('crps_forecast_per_time.csv')
            crps_rows = read_csv(per_time_path)
            value = mean_crps_for_leads(
                crps_rows,
                model_key='model_variant',
                model_value=row['family'],
                horizon_days=horizon_days,
                source_path=per_time_path,
            )
            values_by_cutoff[cutoff][label] = value
            source_rows.append({
                'table_label': table_label,
                'row_label': label,
                'cutoff': cutoff,
                'horizon_days': str(horizon_days),
                'source_class': row['family'],
                'source_path': str(per_time_path),
                'model_selector': f'model_variant={row["family"]}',
                'mean_crps': f'{value:.17g}',
            })

    best_by_cutoff = {cutoff: min(vals.values()) for cutoff, vals in values_by_cutoff.items()}

    raw_lines: list[str] = []
    bayesian_lines: list[str] = []
    manifest_out: list[dict[str, str]] = []
    for row_label in raw_row_order:
        parts = [row_label]
        for cutoff in CUTOFF_ORDER:
            value = values_by_cutoff[cutoff][row_label]
            rendered = fmt_display(value)
            if abs(value - best_by_cutoff[cutoff]) < 1e-12:
                rendered = f'\\textbf{{{rendered}}}'
            parts.append(rendered)
        raw_lines.append(' & '.join(parts) + ' \\\\')
        manifest_out.append({
            'table_label': table_label,
            'row_label': row_label,
            'source_class': table_cfg['source_class'],
            'source_note': table_cfg['note'],
        })
    for row_label in MODEL_ORDER:
        parts = [row_label]
        for cutoff in CUTOFF_ORDER:
            value = values_by_cutoff[cutoff][row_label]
            rendered = fmt_display(value)
            if abs(value - best_by_cutoff[cutoff]) < 1e-12:
                rendered = f'\\textbf{{{rendered}}}'
            parts.append(rendered)
        bayesian_lines.append(' & '.join(parts) + ' \\\\')
        manifest_out.append({
            'table_label': table_label,
            'row_label': row_label,
            'source_class': table_cfg['source_class'],
            'source_note': table_cfg['note'],
        })
    body_lines = [
        r'\multicolumn{6}{l}{\textit{Raw forecast products}} \\',
        *raw_lines,
        r'\midrule',
        r'\multicolumn{6}{l}{\textit{Bayesian benchmark variants}} \\',
        *bayesian_lines,
    ]
    return raw_lines, bayesian_lines, body_lines, manifest_out, source_rows


def build_component_rows(article_root: Path, table_cfg: dict) -> tuple[list[str], list[dict[str, str]]]:
    rows = read_csv(article_root / table_cfg['sources']['covariate_effects_csv'])
    lookup = {(row['covariate'], row['quantile']): row for row in rows}
    q_label = {'5': '5th', '50': '50th', '95': '95th'}
    lines: list[str] = []
    manifest_out: list[dict[str, str]] = []
    for cov in COMPONENT_COVARIATES:
        display = COMPONENT_LABELS.get(cov, cov)
        for idx, q in enumerate(COMPONENT_QUANTILES):
            row = lookup[(cov, q)]
            prefix = f'\\multirow{{3}}{{*}}{{{display}}}' if idx == 0 else ''
            connector = '&' if idx > 0 else '  &'
            lines.append(f'{prefix}{connector} {q_label[q]} & {fmt_display(row["center"])} & {fmt_ci(row, DISPLAY_DIGITS)} \\\\')
            manifest_out.append({'table_label': 'tab:components_23_31', 'row_label': f'{cov}_{q}', 'source_class': table_cfg['source_class'], 'source_note': table_cfg['note']})
        if cov != COMPONENT_COVARIATES[-1]:
            lines.append('\\midrule')
    return lines, manifest_out


def build_source_summary_rows(article_root: Path, table_cfg: dict, table_label: str, digits: int) -> tuple[list[str], list[dict[str, str]]]:
    source_key = 'gamma_summary_csv' if table_label == 'tab:gamma_sigma_intervals1' else 'sigma_summary_csv'
    rows = read_csv(article_root / table_cfg['sources'][source_key])
    lookup = {(row['quantile'], row['source']): row for row in rows}
    q_label = {'5': '05th', '20': '20th', '35': '35th', '50': '50th', '65': '65th', '80': '80th', '95': '95th'}
    lines: list[str] = []
    manifest_out: list[dict[str, str]] = []
    for q in QUANTILE_ORDER:
        cells = [q_label[q]]
        for source in SOURCE_ORDER:
            row = lookup[(q, source)]
            cells.append(fmt_num(row['center'], digits))
            cells.append(fmt_ci(row, digits))
            manifest_out.append({'table_label': table_label, 'row_label': f'{q}_{source}', 'source_class': table_cfg['source_class'], 'source_note': table_cfg['note']})
        lines.append(' & '.join(cells) + ' \\\\')
    return lines, manifest_out


def build_he4_rows(article_root: Path, table_cfg: dict) -> tuple[list[str], list[dict[str, str]]]:
    rows = read_csv(article_root / table_cfg['sources']['he4_quantile_check_loss_wide_csv'])
    lookup = {(row['cutoff'], row['manuscript_label']): row for row in rows}
    cutoffs = [cutoff for cutoff in CUTOFF_ORDER if any(row['cutoff'] == cutoff for row in rows)]
    if len(cutoffs) != len(CUTOFF_ORDER):
        raise ValueError(f'HE4 source is missing one or more expected cutoffs: {CUTOFF_ORDER}')

    lines: list[str] = []
    manifest_out: list[dict[str, str]] = []
    for cutoff in CUTOFF_ORDER:
        cutoff_rows = [lookup[(cutoff, label)] for label in HE4_MODEL_ORDER]
        display = cutoff_rows[0]['cutoff_display']
        best_by_tau = {
            tau_col: min(float(row[tau_col]) for row in cutoff_rows)
            for tau_col in HE4_TAU_COLUMNS
        }
        lines.append(rf'\multicolumn{{8}}{{l}}{{\textit{{Cutoff {display}}}}} \\')
        for label in HE4_MODEL_ORDER:
            row = lookup[(cutoff, label)]
            cells = [label]
            for tau_col in HE4_TAU_COLUMNS:
                value = float(row[tau_col])
                rendered = fmt_display(value)
                if abs(round(value, DISPLAY_DIGITS) - round(best_by_tau[tau_col], DISPLAY_DIGITS)) <= DISPLAY_TIE_TOLERANCE:
                    rendered = f'\\textbf{{{rendered}}}'
                cells.append(rendered)
            lines.append(' & '.join(cells) + ' \\\\')
            manifest_out.append({
                'table_label': 'tab:he4_quantile_check_loss',
                'row_label': f'{cutoff}_{label}',
                'source_class': table_cfg['source_class'],
                'source_note': table_cfg['note'],
            })
        if cutoff != CUTOFF_ORDER[-1]:
            lines.append(r'\addlinespace[1pt]')
    return lines, manifest_out


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description='Build generated TeX table includes for the revised article.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    layout.ensure_base_dirs()
    manifest = load_manifest(article_root)
    out_root = layout.generated_tex_dir
    out_root.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []

    benchmark_raw_lines, benchmark_bayesian_lines, benchmark_body_lines, rows, benchmark_source_rows = build_benchmark_rows(
        article_root,
        manifest['tables']['tab:benchmark_crps_models'],
        horizon_days=BENCHMARK_LONG_HORIZON_DAYS,
        raw_row_order=BENCHMARK_LONG_RAW_ROW_ORDER,
        table_label='tab:benchmark_crps_models',
    )
    manifest_rows.extend(rows)
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_rows'], benchmark_raw_lines)
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_bayesian_rows'], benchmark_bayesian_lines)
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_body'], benchmark_body_lines)
    benchmark_block_lines = [
        r'\begin{table*}[htbp]',
        r'\centering',
        r'\renewcommand{\arraystretch}{1.08}',
        r'\begin{threeparttable}',
        r'\caption{Mean 28-day forecast-window CRPS by model family and cutoff across the five rolling-origin evaluation folds, including normal dynamic linear model baselines. Lower values are better; bold indicates the lowest CRPS within each cutoff column.}',
        r'\label{tab:benchmark_crps_models}',
        r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} >{\ttfamily}l r r r r r}',
        r'\toprule',
        r'Model label & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\',
        r'\midrule',
        *benchmark_body_lines,
        r'\bottomrule',
        r'\end{tabular*}',
        r'\end{threeparttable}',
        r'\end{table*}',
    ]
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_block'], benchmark_block_lines)

    benchmark_nws_raw_lines, benchmark_nws_bayesian_lines, benchmark_nws_body_lines, rows, benchmark_nws_source_rows = build_benchmark_rows(
        article_root,
        manifest['tables']['tab:benchmark_crps_models'],
        horizon_days=BENCHMARK_NWS_COMMON_HORIZON_DAYS,
        raw_row_order=BENCHMARK_SHORT_RAW_ROW_ORDER,
        table_label='tab:benchmark_crps_models_nws_horizon',
    )
    benchmark_source_rows.extend(benchmark_nws_source_rows)
    manifest_rows.extend(rows)
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_nws_horizon_raw_rows'], benchmark_nws_raw_lines)
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_nws_horizon_bayesian_rows'], benchmark_nws_bayesian_lines)
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_nws_horizon_body'], benchmark_nws_body_lines)
    benchmark_nws_block_lines = [
        r'\begin{table*}[htbp]',
        r'\centering',
        r'\renewcommand{\arraystretch}{1.08}',
        r'\begin{threeparttable}',
        r'\caption{Mean CRPS over the common eight-day NWS forecast horizon. Lower values are better; bold indicates the lowest CRPS within each cutoff column.}',
        r'\label{tab:benchmark_crps_models_nws_horizon}',
        r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} >{\ttfamily}l r r r r r}',
        r'\toprule',
        r'Model label & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\',
        r'\midrule',
        *benchmark_nws_body_lines,
        r'\bottomrule',
        r'\end{tabular*}',
        r'\begin{tablenotes}',
        r'\item \textit{Note:} This table restricts every row to forecast leads 1--8, the common daily horizon available for NWS, GloFAS, and the Bayesian predictive distributions. It is therefore the appropriate direct comparison to \texttt{RAW-NWS}; Table~\ref{tab:benchmark_crps_models} gives the complementary 28-day comparison and omits NWS.',
        r'\end{tablenotes}',
        r'\end{threeparttable}',
        r'\end{table*}',
    ]
    write_lines(out_root / TABLE_TEX_FILENAMES['benchmark_nws_horizon_block'], benchmark_nws_block_lines)
    with (out_root / 'benchmark_crps_horizon_summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'table_label', 'row_label', 'cutoff', 'horizon_days', 'source_class',
                'source_path', 'model_selector', 'mean_crps',
            ],
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(benchmark_source_rows)

    he4_lines, rows = build_he4_rows(article_root, manifest['tables']['tab:he4_quantile_check_loss'])
    manifest_rows.extend(rows)
    write_lines(out_root / TABLE_TEX_FILENAMES['he4_rows'], he4_lines)
    he4_block_lines = [
        r'\begin{table*}[htbp]',
        r'\centering',
        r'\renewcommand{\arraystretch}{1.08}',
        r'\begin{threeparttable}',
        r'\caption{Mean forecast-window quantile check loss by synthesis model, cutoff, and target quantile. Lower values are better; bold indicates the lowest check loss within each cutoff and quantile column.}',
        r'\label{tab:he4_quantile_check_loss}',
        r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} >{\ttfamily}l r r r r r r r}',
        r'\toprule',
        r'Model & q0.05 & q0.20 & q0.35 & q0.50 & q0.65 & q0.80 & q0.95 \\',
        r'\midrule',
        *he4_lines,
        r'\bottomrule',
        r'\end{tabular*}',
        r'\begin{tablenotes}',
        r'\item \textit{Note:} Check loss is computed on forecast-window rows only, using held-out USGS observations as verification targets on the same $\log(1+Q)$ scale used for CRPS. The four synthesis competitors are resolved directly from the frozen HE-2 publication manifest.',
        r'\end{tablenotes}',
        r'\end{threeparttable}',
        r'\end{table*}',
    ]
    write_lines(out_root / TABLE_TEX_FILENAMES['he4_block'], he4_block_lines)

    component_lines, rows = build_component_rows(article_root, manifest['tables']['tab:components_23_31'])
    manifest_rows.extend(rows)
    write_lines(out_root / TABLE_TEX_FILENAMES['components_rows'], component_lines)
    component_block_lines = [
        r'\begin{table*}[htbp]',
        r'\centering',
        r'\begin{threeparttable}',
        r'\caption{Selected Posterior Means and 95\% Credible Intervals for Transfer-Function Covariates}',
        r'\label{tab:components_23_31}',
        r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} l c S[table-format=-1.5] l }',
        r'\toprule',
        r'\textbf{Covariate} & \textbf{Quantile} & \textbf{Mean} & \textbf{95\% CI} \\',
        r'\midrule',
        *component_lines,
        r'\bottomrule',
        r'\end{tabular*}',
        r'\begin{tablenotes}',
        r'\item \textit{Note:} Posterior means and 95\% credible intervals $[{\rm Q2.5}, {\rm Q97.5}]$ for selected transfer-function coefficients at the representative December 25, 2022 cutoff, for the 5th, 50th, and 95th quantile models. \texttt{First GDPC factor} refers to the first generalized dynamic principal component introduced in Section~\ref{sec:data}.',
        r'\end{tablenotes}',
        r'\end{threeparttable}',
        r'\end{table*}',
    ]
    write_lines(out_root / TABLE_TEX_FILENAMES['components_block'], component_block_lines)

    gamma_lines, rows = build_source_summary_rows(article_root, manifest['tables']['tab:gamma_sigma_intervals1'], 'tab:gamma_sigma_intervals1', DISPLAY_DIGITS)
    manifest_rows.extend(rows)
    write_lines(out_root / TABLE_TEX_FILENAMES['gamma_rows'], gamma_lines)
    gamma_block_lines = [
        r'\begin{table*}[htbp]',
        r'\centering',
        r'\begin{threeparttable}',
        r'\caption{Posterior Medians and 95\% Credible Intervals for the Source-Specific Skewness Parameters $\gamma_j(\tau)$ at the Representative December 25, 2022 Cutoff}',
        r'\label{tab:gamma_sigma_intervals1}',
        r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} l',
        r' S[table-format=-1.5] l',
        r' S[table-format=-1.5] l',
        r' S[table-format=-1.5] l',
        r'@{}}',
        r'\toprule',
        r' & \multicolumn{2}{c}{\textbf{USGS}} & \multicolumn{2}{c}{\textbf{GLOFAS}} & \multicolumn{2}{c}{\textbf{NWS}} \\',
        r'\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}',
        r'\textbf{Quantile} & \textbf{Median} & \textbf{95\% CI} & \textbf{Median} & \textbf{95\% CI} & \textbf{Median} & \textbf{95\% CI} \\',
        r'\midrule',
        *gamma_lines,
        r'\bottomrule',
        r'\end{tabular*}',
        r'\begin{tablenotes}',
        r'\item \textit{Note:} Posterior medians and 95\% credible intervals $[{\rm Q2.5}, {\rm Q97.5}]$ for the source-specific skewness parameters $\gamma_j(\tau)$ in the exAL observation model at the representative December 25, 2022 cutoff. The quantile labels 05th through 95th correspond to the seven fitted quantile models. These summaries are included as supplementary appendix support rather than as primary forecast-validation evidence.',
        r'\end{tablenotes}',
        r'\end{threeparttable}',
        r'\end{table*}',
    ]
    write_lines(out_root / TABLE_TEX_FILENAMES['gamma_block'], gamma_block_lines)

    sigma_lines, rows = build_source_summary_rows(article_root, manifest['tables']['tab:gamma_sigma_intervals2'], 'tab:gamma_sigma_intervals2', DISPLAY_DIGITS)
    manifest_rows.extend(rows)
    write_lines(out_root / TABLE_TEX_FILENAMES['sigma_rows'], sigma_lines)
    sigma_block_lines = [
        r'\begin{table*}[htbp]',
        r'\centering',
        r'\begin{threeparttable}',
        r'\caption{Posterior Medians and 95\% Credible Intervals for the Source-Specific Scale Parameters $\sigma_j(\tau)$ at the Representative December 25, 2022 Cutoff}',
        r'\label{tab:gamma_sigma_intervals2}',
        r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} l',
        r' S[table-format=1.5] l',
        r' S[table-format=1.5] l',
        r' S[table-format=1.5] l',
        r'@{}}',
        r'\toprule',
        r' & \multicolumn{2}{c}{\textbf{USGS}} & \multicolumn{2}{c}{\textbf{GLOFAS}} & \multicolumn{2}{c}{\textbf{NWS}} \\',
        r'\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}',
        r'\textbf{Quantile} & \textbf{Median} & \textbf{95\% CI} & \textbf{Median} & \textbf{95\% CI} & \textbf{Median} & \textbf{95\% CI} \\',
        r'\midrule',
        *sigma_lines,
        r'\bottomrule',
        r'\end{tabular*}',
        r'\begin{tablenotes}',
        r'\item \textit{Note:} Posterior medians and 95\% credible intervals $[{\rm Q2.5}, {\rm Q97.5}]$ for the source-specific scale parameters $\sigma_j(\tau)$ at the representative December 25, 2022 cutoff. These summaries are included as supplementary appendix support rather than as primary forecast-validation evidence.',
        r'\end{tablenotes}',
        r'\end{threeparttable}',
        r'\end{table*}',
    ]
    write_lines(out_root / TABLE_TEX_FILENAMES['sigma_block'], sigma_block_lines)

    external_manifest_rows = preserved_external_manifest_rows(out_root / 'manifest.csv')
    manifest_rows.extend(external_manifest_rows)

    with (out_root / 'manifest.csv').open('w', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['table_label', 'row_label', 'source_class', 'source_note'],
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    metadata = {
        'manifest_path': str(manifest_path(article_root)),
        'display_precision_digits': DISPLAY_DIGITS,
        'outputs': {
            'tab:benchmark_crps_models': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_rows']).relative_to(article_root)),
            'tab:benchmark_crps_models_bayesian': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_bayesian_rows']).relative_to(article_root)),
            'tab:benchmark_crps_models_body': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_body']).relative_to(article_root)),
            'tab:benchmark_crps_models_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_block']).relative_to(article_root)),
            'tab:benchmark_crps_models_nws_horizon': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_nws_horizon_raw_rows']).relative_to(article_root)),
            'tab:benchmark_crps_models_nws_horizon_bayesian': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_nws_horizon_bayesian_rows']).relative_to(article_root)),
            'tab:benchmark_crps_models_nws_horizon_body': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_nws_horizon_body']).relative_to(article_root)),
            'tab:benchmark_crps_models_nws_horizon_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['benchmark_nws_horizon_block']).relative_to(article_root)),
            'tab:benchmark_crps_horizon_summary': str((layout.generated_tex_dir / 'benchmark_crps_horizon_summary.csv').relative_to(article_root)),
            'tab:he4_quantile_check_loss': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['he4_rows']).relative_to(article_root)),
            'tab:he4_quantile_check_loss_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['he4_block']).relative_to(article_root)),
            'tab:components_23_31': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['components_rows']).relative_to(article_root)),
            'tab:components_23_31_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['components_block']).relative_to(article_root)),
            'tab:gamma_sigma_intervals1': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['gamma_rows']).relative_to(article_root)),
            'tab:gamma_sigma_intervals1_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['gamma_block']).relative_to(article_root)),
            'tab:gamma_sigma_intervals2': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['sigma_rows']).relative_to(article_root)),
            'tab:gamma_sigma_intervals2_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['sigma_block']).relative_to(article_root)),
            'tab:he3_ablation_crps_body': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['he3_ablation_body']).relative_to(article_root)),
            'tab:he3_ablation_crps_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['he3_ablation_block']).relative_to(article_root)),
            'tab:he3_ablation_crps_nws_horizon_body': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['he3_ablation_nws_horizon_body']).relative_to(article_root)),
            'tab:he3_ablation_crps_nws_horizon_block': str((layout.generated_tex_dir / TABLE_TEX_FILENAMES['he3_ablation_nws_horizon_block']).relative_to(article_root)),
            'tab:he3_ablation_crps_horizon_summary': str((layout.generated_tex_dir / 'he3_ablation_crps_horizon_summary.csv').relative_to(article_root))
        }
    }
    (out_root / 'build_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (out_root / 'README.md').write_text(
        '# Generated Table Includes\n\n'
        'These TeX table fragments are generated from the article-side artifact bundles named in `MANUSCRIPT_ASSET_MANIFEST.json`.\n\n'
        f'Publication-facing numeric cells are rendered with fixed {DISPLAY_DIGITS} decimal places.\n\n'
        'Refresh path:\n'
        '- `scripts/build_generated_table_includes.py`\n\n'
        'The manuscript uses `\\input{}` to consume these files directly.\n'
    )
    print(f'Built generated table includes in {out_root}')


if __name__ == '__main__':
    main()
