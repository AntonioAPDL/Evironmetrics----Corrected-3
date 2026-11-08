#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from article_repo_layout import build_layout


def file_exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def build_items(root: Path) -> list[dict[str, object]]:
    tex = read_text(root / 'wileyNJD-APA.tex')
    render_meta_path = root / 'artifacts' / 'representative_selected_model_2022_12_25' / 'authoritative_support' / 'figures' / 'render_metadata.json'
    render_meta = json.loads(render_meta_path.read_text(encoding='utf-8')) if render_meta_path.exists() else {}

    no_support_window_phrase = 'support window for the cutoff' not in tex.lower()
    no_cutoff_centered = 'cutoff-centered' not in tex.lower()
    has_all_cutoff_forecast_context = len(list((root / 'Figures' / 'forecast_context_by_cutoff').glob('cutoff_*_forecast_context.png'))) == 5
    has_all_cutoff_multivar_synthesis = len(list((root / 'Figures' / 'multivariate_synthesis_by_cutoff').glob('cutoff_*_multivariate_synthesis.png'))) == 5
    has_all_cutoff_multivar_synthesis_overlay = len(list((root / 'Figures' / 'multivariate_synthesis_by_cutoff').glob('cutoff_*_multivariate_synthesis_with_reference_ensembles.png'))) == 5
    has_all_cutoff_reference_synthesis = len(list((root / 'Figures' / 'reference_synthesis_by_cutoff').glob('cutoff_*_reference_synthesis.png'))) == 5
    has_rep_multivar_overlay = file_exists(root, 'artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png')
    has_rep_multivar = file_exists(root, 'Figures/multivariate_synthesis_by_cutoff/cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png')
    has_rep_univar = file_exists(root, 'Figures/manuscript/reference_synthesis_univariate.png')
    has_wet_fullrange = file_exists(root, 'artifacts/historical_support_from_current_models/figures/historical_summary_wet_period_fullrange.png')
    long_cycle_component_only = (
        render_meta.get('figure_a1_component') == 6
        and render_meta.get('figure_a1_component_contract') == 'raw_state_component'
    )
    appendix_setup_panels_in_article = 'setup_support.png' in tex

    items: list[dict[str, object]] = [
        {
            'item': 1,
            'request': 'Figure 1 should remain good and consistent.',
            'status': 'complete',
            'evidence': [
                'Figures/manuscript/site_context_usgs.png',
                'wileyNJD-APA.tex:243',
                'scripts/setup_support_bundle_v2_helpers.R:330-371',
            ],
                'note': 'USGS figure remains the manuscript anchor and uses the shared current-rating NWS discharge-reference styling and flow-axis label contract.',
        },
        {
            'item': 2,
            'request': 'Figure 2 should remove support-window subtitle, show units for precipitation and soil moisture, keep the large-scale climate-factor label concise, and keep caption compact/high quality.',
            'status': 'complete' if no_support_window_phrase else 'partial',
            'evidence': [
                'Figures/manuscript/covariate_context_precip_soil_gdpc.png',
                'scripts/figure_style_contract.R:86-92',
                'scripts/setup_support_bundle_v2_helpers.R:376-401',
                'wileyNJD-APA.tex:259-264',
            ],
            'note': 'Facet labels now render as plotmath expressions for precipitation, soil moisture, and `GDPC[1]`; the manuscript caption describes the raw support-file scale directly.',
        },
        {
            'item': 3,
            'request': 'Figure 3 should remove the historical-support subtitle, keep clear flow units, and use a compact/high-quality caption.',
            'status': 'complete',
            'evidence': [
                'Figures/manuscript/retrospective_products_context.png',
                'scripts/setup_support_bundle_v2_helpers.R:403-432',
                'scripts/figure_style_contract.R:3-14',
                'wileyNJD-APA.tex:278',
            ],
            'note': 'The retrospective figure uses the shared flow-axis label and no support-window subtitle; the caption now states the available pre-cutoff support window and `log(1+x)` units.',
        },
        {
            'item': 4,
                'request': 'Figure 4 should use the same flow-axis contract, simplified legend labels, aligned current-rating discharge references when present, and readable caption wording without “cutoff-centered”.',
            'status': 'complete' if no_cutoff_centered else 'partial',
            'evidence': [
                'Figures/manuscript/forecast_products_context.png',
                'scripts/forecats_plot_bundle.R:390-541',
                'scripts/figure_style_contract.R:61-121',
                'wileyNJD-APA.tex:330',
            ],
                'note': 'Legend labels now use product/version names only, the flow axis matches the other flow figures, and the current-rating discharge-reference lines come from the shared helper used by the USGS plot.',
        },
        {
            'item': 5,
            'request': 'Figure 5 should use a 0 to 7 y-range and inherit the normalized style when possible.',
            'status': 'complete',
            'evidence': [
                'Figures/manuscript/historical_summary_dry_period.png',
                'scripts/render_current_model_output_support_figures.R:617-623',
            ],
            'note': 'The dry-period historical summary is rendered with an explicit `ylim_override = c(0, 7)` under the shared flow display contract.',
        },
        {
            'item': 6,
            'request': 'Figure 6 should exist in both 0 to 20 and 0 to 7 variants and keep the normalized style.',
            'status': 'complete' if has_wet_fullrange else 'partial',
            'evidence': [
                'Figures/manuscript/historical_summary_wet_period.png',
                'artifacts/historical_support_from_current_models/figures/historical_summary_wet_period_fullrange.png',
                'scripts/render_current_model_output_support_figures.R:624-634',
            ],
            'note': 'The manuscript version uses `0–7`; the repo preserves the full-range companion under the historical-support artifact bundle.',
        },
        {
            'item': 7,
            'request': 'Figure 7 and Figure A2 should align visually with Figure 4, be produced for all cutoffs, and also have extra overlay versions with raw/reference ensembles.',
            'status': 'complete' if (has_all_cutoff_multivar_synthesis and has_all_cutoff_multivar_synthesis_overlay and has_all_cutoff_reference_synthesis and has_rep_multivar_overlay and has_rep_multivar and has_rep_univar) else 'partial',
            'evidence': [
                'Figures/multivariate_synthesis_by_cutoff/cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png',
                'artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png',
                'Figures/multivariate_synthesis_by_cutoff/manifest.csv',
                'Figures/reference_synthesis_by_cutoff/manifest.csv',
                'R/unified/post_publication_figures.R:546-807',
            ],
            'note': 'The representative cutoff uses the polished `publication_focus_v2` style and now the corresponding Figure 7 and Figure A2 families are also preserved article-side for all five cutoffs, including the overlay variants with raw/reference ensembles.',
        },
        {
            'item': 8,
            'request': 'Figure A1 should plot the long-cycle seasonal component alone and use a compact, high-quality caption.',
            'status': 'complete' if long_cycle_component_only else 'partial',
            'evidence': [
                'Figures/manuscript/historical_component_80month.png',
                'artifacts/historical_support_from_current_models/figures/render_metadata.json',
                'scripts/render_authoritative_selected_model_support_figures.R',
                'wileyNJD-APA.tex:460-466',
            ],
            'note': 'The render metadata records the intended raw component-6 contract explicitly; plus/minus-trend variants are retained only as analysis diagnostics.',
        },
        {
            'item': 9,
            'request': 'Keep the forecast-context panel D for all cutoffs, and replace manuscript A3–A6 setup/support composites with cutoff-specific multivariate synthesis overlays.',
            'status': 'complete' if (has_all_cutoff_forecast_context and has_all_cutoff_multivar_synthesis_overlay and not appendix_setup_panels_in_article) else 'partial',
            'evidence': [
                'Figures/forecast_context_by_cutoff/manifest.csv' if has_all_cutoff_forecast_context else 'Figures/forecast_context_by_cutoff/',
                'Figures/multivariate_synthesis_by_cutoff/manifest.csv' if has_all_cutoff_multivar_synthesis_overlay else 'Figures/multivariate_synthesis_by_cutoff/',
                'Figures/reference_synthesis_by_cutoff/manifest.csv' if has_all_cutoff_reference_synthesis else 'Figures/reference_synthesis_by_cutoff/',
                'artifacts/five_cutoff_setup_support/review/figure_manifest.csv',
                'wileyNJD-APA.tex:483-520',
            ],
            'note': 'Forecast-context figures remain preserved cutoff-wide for review. The manuscript appendix now uses the cutoff-specific multivariate synthesis overlay figures; setup/support composites are retained only as generated support artifacts and are no longer included in the manuscript.',
        },
    ]
    return items


def write_markdown(path: Path, items: list[dict[str, object]]) -> None:
    complete = sum(1 for item in items if item['status'] == 'complete')
    partial = sum(1 for item in items if item['status'] == 'partial')
    not_done = sum(1 for item in items if item['status'] == 'not_done')

    lines = [
        '# Figure Polish Status Audit',
        '',
        'This audit checks the implementation status of the nine-point figure-polish request that preceded the PCA hardening and full-history reconstruction phase.',
        '',
        f'- `complete`: {complete}',
        f'- `partial`: {partial}',
        f'- `not_done`: {not_done}',
        '',
        '## Item-by-item status',
        '',
    ]
    for item in items:
        lines.append(f"### Item {item['item']} [{item['status']}]")
        lines.append(item['request'])
        lines.append('')
        lines.append(f"- Note: {item['note']}")
        lines.append('- Evidence:')
        for ev in item['evidence']:
            lines.append(f'  - `{ev}`')
        lines.append('')

    lines.extend([
        '## Remaining work before the next modeling phase',
        '',
        '1. Keep setup/support composites as repo-only support artifacts unless a future manuscript revision explicitly requests them.',
        '2. Keep the early short-window cutoffs (`2021-01-23`, `2021-11-12`) separate from any future full-history-only interpretation claims until the full-table corrected bundle relaunch is complete.',
        '',
    ])
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Build a point-by-point audit of the figure-polish checklist status.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    layout = build_layout(args.article_root.resolve())
    layout.ensure_base_dirs()
    out_dir = layout.manuscript_asset_review_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    items = build_items(layout.root)
    md_path = out_dir / 'FIGURE_POLISH_STATUS_AUDIT.md'
    json_path = out_dir / 'figure_polish_status_audit.json'
    write_markdown(md_path, items)
    json_path.write_text(json.dumps(items, indent=2), encoding='utf-8')
    print(f'Wrote {md_path}')
    print(f'Wrote {json_path}')


if __name__ == '__main__':
    main()
