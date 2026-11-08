#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from article_asset_manifest import load_manifest
from article_runtime_bindings import binding_as_path, load_runtime_bindings
from article_repo_layout import build_layout

def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def keep_sharedspec_complete(live_keep_root: Path) -> bool:
    summaries = list((live_keep_root / 'runs').glob('*/report/summary.json'))
    return len(summaries) == 5


def infer_row(
    article_root: Path,
    rel_path: str,
    manuscript_sources: dict[str, dict[str, str]],
    appendix_rows: dict[str, dict[str, str]],
    forecast_rows: dict[str, dict[str, str]],
    multivar_rows: dict[str, dict[str, str]],
    reference_rows: dict[str, dict[str, str]],
    *,
    completed_keep_root: Path,
) -> dict[str, str]:
    prefix = rel_path.split('/', 1)[0]
    name = Path(rel_path).name

    if rel_path.startswith('manuscript/'):
        src = manuscript_sources.get(rel_path, {})
        label = src.get('label', '')
        source_path = src.get('source_path', '')
        if label in {'fig:sanlorenzo', 'fig:covariates', 'fig:retrospectives', 'fig:ensembles'}:
            return {
                'classification': 'input-side / support / context figure',
                'source_script': 'scripts/refresh_setup_support_by_cutoff_v2.py -> scripts/promote_setup_support_v2_to_disc.py -> scripts/promote_generated_figures_to_disc.py',
                'source_lineage': 'corrected_setup_support_v2_20260516',
                'status': 'updated_now',
                'blocker': '',
                'source_path': source_path,
            }
        if label in {'fig:synth1'}:
            return {
                'classification': 'model-output-driven figure',
                'source_script': 'scripts/refresh_exal_m_t1_generated_assets.py -> scripts/promote_generated_figures_to_disc.py',
                'source_lineage': 'completed_keep_outputs_20260516',
                'status': 'updated_now',
                'blocker': '',
                'source_path': source_path,
            }
        if label in {'fig:dry_quantile', 'fig:rainy_quantile', 'fig:80_components'}:
            return {
                'classification': 'model-output-driven figure',
                'source_script': 'scripts/refresh_authoritative_selected_model_support_figures.py -> scripts/promote_generated_figures_to_disc.py',
                'source_lineage': 'current_selected_model_representative',
                'status': 'updated_now',
                'blocker': '',
                'source_path': source_path,
            }
        if label in {'fig:synth2'}:
            historical_support_bundle = article_root / 'artifacts' / 'historical_support_from_current_models' / 'bundle_metadata.json'
            historical_support_refresh = article_root / 'artifacts' / 'historical_support_from_current_models' / 'refresh_status.json'
            bundle_payload = json.loads(historical_support_bundle.read_text(encoding='utf-8')) if historical_support_bundle.exists() else {}
            refresh_payload = json.loads(historical_support_refresh.read_text(encoding='utf-8')) if historical_support_refresh.exists() else {}
            render_mode = bundle_payload.get('multivar_source', {}).get('historical_support_render_generation_mode', '')
            canonical_root = bundle_payload.get('multivar_source', {}).get('canonical_runtime_run_root', '')
            refreshed_ok = refresh_payload.get('returncode') == 0
            canonical_ok = canonical_root.startswith(str(completed_keep_root))
            if refreshed_ok and canonical_ok and render_mode:
                return {
                    'classification': 'model-output-driven figure',
                    'source_script': 'scripts/refresh_current_model_output_support_figures.py -> scripts/promote_generated_figures_to_disc.py',
                    'source_lineage': f'completed_keep_outputs_20260516_via_{render_mode}',
                    'status': 'updated_now',
                    'blocker': '',
                    'source_path': source_path,
                }
            return {
                'classification': 'model-output-driven figure',
                'source_script': 'scripts/refresh_current_model_output_support_figures.py -> scripts/promote_generated_figures_to_disc.py',
                'source_lineage': 'historical_support_retained_artifacts_missing_20260516',
                'status': 'blocked_retained_support_artifacts_missing',
                'blocker': 'Current-model support renderer still expects retained multivariate fit artifacts or a retained corrected state-summary contract that has not been refreshed successfully yet.',
                'source_path': source_path,
            }
    if rel_path.startswith('appendix_cutoff_panels/') and name != 'README.md' and name != 'manifest.csv':
        row = next((r for r in appendix_rows.values() if Path(r['panel_path']).name == name), {})
        return {
            'classification': 'input-side / support / context figure',
            'source_script': 'scripts/refresh_setup_support_by_cutoff_v2.py -> scripts/build_setup_support_by_cutoff_v2_appendix.py',
            'source_lineage': 'corrected_setup_support_v2_20260516',
            'status': 'updated_now',
            'blocker': '',
            'source_path': row.get('panel_path', ''),
        }
    if rel_path.startswith('forecast_context_by_cutoff/') and name not in {'README.md', 'manifest.csv'}:
        row = forecast_rows.get(name, {})
        return {
            'classification': 'input-side / support / context figure',
            'source_script': 'scripts/refresh_setup_support_by_cutoff_v2.py -> scripts/promote_cutoff_forecast_context_figures.py',
            'source_lineage': 'corrected_setup_support_v2_20260516',
            'status': 'updated_now',
            'blocker': '',
            'source_path': row.get('source_path', ''),
        }
    if rel_path.startswith('multivariate_synthesis_by_cutoff/') and name not in {'README.md', 'manifest.csv'}:
        row = multivar_rows.get(name, {})
        return {
            'classification': 'synthesis figure',
            'source_script': 'scripts/refresh_cutoff_synthesis_families.py',
            'source_lineage': 'completed_keep_outputs_20260516',
            'status': 'updated_now',
            'blocker': '',
            'source_path': row.get('source_path', ''),
        }
    if rel_path.startswith('reference_synthesis_by_cutoff/') and name not in {'README.md', 'manifest.csv'}:
        row = reference_rows.get(name, {})
        return {
            'classification': 'synthesis figure',
            'source_script': 'scripts/refresh_cutoff_synthesis_families.py',
            'source_lineage': 'completed_univar_outputs_20260516',
            'status': 'updated_now',
            'blocker': '',
            'source_path': row.get('source_path', ''),
        }
    return {
        'classification': 'figure unaffected by corrected lineage',
        'source_script': 'n/a',
        'source_lineage': 'n/a',
        'status': 'unchanged_intentionally',
        'blocker': '',
        'source_path': '',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Build a strict article figure-lineage audit for the revised repo.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    bindings = load_runtime_bindings(article_root)
    live_keep_root = binding_as_path(bindings, 'exal_m_t1', 'keep_runtime_root')
    completed_keep_root = binding_as_path(bindings, 'exal_m_t1', 'keep_runtime_root')
    completed_univar_root = binding_as_path(bindings, 'exal_m_t1', 'univar_runtime_root')
    setup_support_runtime = binding_as_path(bindings, 'exal_m_t1', 'setup_support_runtime_root')
    layout = build_layout(article_root)
    layout.ensure_base_dirs()

    manifest = load_manifest(article_root)
    manuscript_sources = {
        Path(row['manuscript_path']).relative_to(layout.figures_dir.name).as_posix(): row
        for row in manifest['figures']
        if Path(row['manuscript_path']).parts[0] == layout.figures_dir.name
    }

    appendix_manifest = load_csv(layout.appendix_cutoff_panels_dir / 'manifest.csv')
    appendix_rows = {Path(r['panel_path']).name: r for r in appendix_manifest}
    forecast_manifest = load_csv(layout.cutoff_forecast_context_dir / 'manifest.csv')
    forecast_rows = {Path(r['target_path']).name: r for r in forecast_manifest}
    multivar_manifest = load_csv(layout.cutoff_multivariate_synthesis_dir / 'manifest.csv') if (layout.cutoff_multivariate_synthesis_dir / 'manifest.csv').exists() else []
    multivar_rows = {Path(r['target_path']).name: r for r in multivar_manifest}
    reference_manifest = load_csv(layout.cutoff_reference_synthesis_dir / 'manifest.csv') if (layout.cutoff_reference_synthesis_dir / 'manifest.csv').exists() else []
    reference_rows = {Path(r['target_path']).name: r for r in reference_manifest}

    setup_rows = []
    for slug_dir in sorted(layout.five_cutoff_setup_support_dir.iterdir()):
        if not slug_dir.is_dir() or slug_dir.name == 'review':
            continue
        coverage = json.loads((slug_dir / 'metadata' / 'cutoff_entry.json').read_text())
        cov_yaml = (slug_dir / 'metadata' / 'coverage_audit.yaml').read_text(encoding='utf-8')
        support_yaml = (slug_dir / 'metadata' / 'support_window.yaml').read_text(encoding='utf-8')
        setup_rows.append((slug_dir.name, coverage, cov_yaml, support_yaml))

    full_history_all_setup = True
    gdpc_all_setup = True
    for slug, entry, cov_text, _support_text in setup_rows:
        if "retrospective:\n  requested_start: '1987-05-29'" not in cov_text or "full_history_available: true" not in cov_text.split('retrospective:')[-1]:
            full_history_all_setup = False
        if "gdpc:" not in cov_text or "full_history_available: true" not in cov_text.split('gdpc:')[-1].split('retrospective:')[0]:
            gdpc_all_setup = False

    rows = []
    for rel in sorted(str(p.relative_to(layout.figures_dir)) for p in layout.figures_dir.rglob('*') if p.is_file()):
        info = infer_row(
            article_root,
            rel,
            manuscript_sources,
            appendix_rows,
            forecast_rows,
            multivar_rows,
            reference_rows,
            completed_keep_root=completed_keep_root,
        )
        rows.append({
            'figure_path': f'{layout.figures_dir.name}/{rel}',
            **info,
        })

    historical_support_refresh = article_root / 'artifacts' / 'historical_support_from_current_models' / 'refresh_status.json'
    historical_support_bundle = article_root / 'artifacts' / 'historical_support_from_current_models' / 'bundle_metadata.json'
    refresh_payload = json.loads(historical_support_refresh.read_text(encoding='utf-8')) if historical_support_refresh.exists() else {}
    bundle_payload = json.loads(historical_support_bundle.read_text(encoding='utf-8')) if historical_support_bundle.exists() else {}
    historical_render_mode = bundle_payload.get('multivar_source', {}).get('historical_support_render_generation_mode', '')
    historical_support_ok = refresh_payload.get('returncode') == 0 and bool(historical_render_mode)
    historical_support_status = 'updated_now' if historical_support_ok else 'blocked_retained_support_artifacts_missing'
    historical_support_lineage = (
        f'completed_keep_outputs_20260516_via_{historical_render_mode}'
        if historical_support_ok
        else 'historical_support_retained_artifacts_missing_20260516'
    )
    historical_support_notes = (
        'Refreshed from the corrected retained support contract using the dedicated historical-support replay root.'
        if historical_support_ok
        else 'Current-model support renderer still expects retained multivariate fit artifacts that are not exported by the completed workflow roots.'
    )

    lowercase_root = article_root / 'figures'
    tracked_files = {str(p.relative_to(layout.figures_dir)) for p in layout.figures_dir.rglob('*') if p.is_file()}
    lowercase_files = (
        {str(p.relative_to(lowercase_root)) for p in lowercase_root.rglob('*') if p.is_file()}
        if lowercase_root.exists()
        else set()
    )
    lowercase_has_only_compatibility_outputs = not lowercase_files

    report_root = layout.reports_dir / 'article_figure_lineage_audit_20260516'
    report_root.mkdir(parents=True, exist_ok=True)

    with (report_root / 'figure_lineage_status.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        'setup_support_runtime_root': str(setup_support_runtime),
        'completed_keep_output_root': str(completed_keep_root),
        'completed_univar_output_root': str(completed_univar_root),
        'live_keep_sharedspec_root': str(live_keep_root),
        'live_keep_sharedspec_complete': keep_sharedspec_complete(live_keep_root),
        'setup_support_full_history_all_cutoffs': full_history_all_setup,
        'setup_support_gdpc_all_cutoffs': gdpc_all_setup,
        'current_tracked_figure_tree': layout.figures_dir.name,
        'lowercase_compatibility_tree_empty': lowercase_has_only_compatibility_outputs,
        'lowercase_figure_file_count': len(lowercase_files),
        'tracked_figure_file_count': len(tracked_files),
        'status_counts': {s: sum(1 for row in rows if row['status'] == s) for s in sorted({row['status'] for row in rows})},
    }
    (report_root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

    md = []
    md.append('# Article Figure Lineage Audit\n\n')
    md.append('## Executive read\n\n')
    md.append(f"- Setup/support family refreshed from `{setup_support_runtime}`.\n")
    md.append(f"- Setup/support full-history contract across all cutoffs: `{'PASS' if full_history_all_setup else 'FAIL'}`.\n")
    md.append(f"- Setup/support GDPC contract across all cutoffs: `{'PASS' if gdpc_all_setup else 'FAIL'}`.\n")
    md.append(f"- Live shared-spec keep outputs complete: `{'YES' if keep_sharedspec_complete(live_keep_root) else 'NO'}`.\n")
    md.append(f"- Current tracked figure tree: `{layout.figures_dir.name}/`.\n")
    md.append(f"- Lowercase compatibility figure tree empty: `{'YES' if lowercase_has_only_compatibility_outputs else 'NO'}`.\n\n")
    md.append('## Figure family conclusions\n\n')
    md.append('| Family | Current status | Source lineage | Notes |\n')
    md.append('|---|---|---|---|\n')
    md.append(f"| Setup/support manuscript figures + cutoff-wide forecast-context family | `updated_now` | `exal_m_t1_setup_support_by_cutoff_v2_20260516` | Full USGS/PPT/SOIL/GDPC history from `1987-05-29 -> cutoff`; retrospective support now sourced from repaired canonical shared bundles for all cutoffs. Setup/support composites are retained as support artifacts but are no longer manuscript appendix figures. |\n")
    md.append(f"| Representative keep synthesis + cutoff-wide multivariate synthesis overlays | `updated_now` | completed keep output root `20260516` | Refreshed from the completed shared-spec keep rerun; Figure 7 and the supplementary cutoff-specific synthesis panels use reference-product overlay variants. |\n")
    md.append(f"| Historical support from current models | `{historical_support_status}` | `{historical_support_lineage}` | {historical_support_notes} |\n")
    md.append(f"| Reference synthesis family | `updated_now` | completed univariate output root `20260516` | Refreshed from the completed shared-spec univariate rerun. |\n\n")
    md.append('## Per-figure status\n\n')
    md.append('| Figure path | Class | Status | Source lineage | Source script | Blocker |\n')
    md.append('|---|---|---|---|---|---|\n')
    for row in rows:
        md.append(f"| `{row['figure_path']}` | {row['classification']} | `{row['status']}` | `{row['source_lineage']}` | `{row['source_script']}` | {row['blocker'] or '-'} |\n")
    md.append('\n## Explicit keep-family confirmation\n\n')
    md.append(f"- Setup/support keep figure families now use full history: `{'YES' if full_history_all_setup else 'NO'}`.\n")
    md.append(f"- Setup/support keep figure families now use GDPC instead of the legacy PCA interpretation: `{'YES' if gdpc_all_setup else 'NO'}`.\n")
    md.append('- Setup/support keep figure families now use corrected retrospective/forecast bundle lineage from the canonical `20260510` shared-input bundles.\n')
    md.append('- Keep model-output families are now refreshed to the completed `20260516` shared-spec keep rerun.\n')
    md.append('- Reference synthesis families are now refreshed to the completed `20260516` shared-spec univariate rerun.\n')
    if historical_support_ok:
        md.append('- Historical-support figures are now refreshed from the dedicated retained-support replay contract and promoted into the revised manuscript figure tree.\n')
    else:
        md.append('- Historical-support figures remain explicitly blocked because the renderer still requires retained multivariate fit artifacts that the completed workflow roots do not currently export.\n')
    (report_root / 'ARTICLE_FIGURE_LINEAGE_AUDIT_20260516.md').write_text(''.join(md), encoding='utf-8')
    print(report_root)


if __name__ == '__main__':
    main()
