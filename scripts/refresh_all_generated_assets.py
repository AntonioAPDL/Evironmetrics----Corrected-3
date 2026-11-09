#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from article_runtime_bindings import binding_as_optional_path, binding_as_path, load_runtime_bindings

def run(cmd: list[str]) -> None:
    print('+', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def run_optional(cmd: list[str], status_path: Path, *, strict: bool) -> None:
    print('+', ' '.join(cmd))
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'command': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'status': 'ok' if proc.returncode == 0 else 'skipped',
    }
    status_path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    if proc.returncode == 0:
        if proc.stdout:
            print(proc.stdout, end='')
        if proc.stderr:
            print(proc.stderr, end='', file=sys.stderr)
        return
    if strict:
        if proc.stdout:
            print(proc.stdout, end='')
        if proc.stderr:
            print(proc.stderr, end='', file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
    print(
        'WARNING: current-model support refresh skipped; see '
        f'{status_path} for the captured failure and the retained artifact state.',
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh all article-side generated assets and reports.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--workflow-root', type=Path)
    parser.add_argument('--runtime-root', type=Path)
    parser.add_argument(
        '--setup-support-runtime-root',
        type=Path,
    )
    parser.add_argument(
        '--multivar-support-run-root',
        type=Path,
    )
    parser.add_argument(
        '--authoritative-selected-support-output-root',
        type=Path,
        help='Workflow post/outputs directory containing compact authoritative selected-model support exports.',
    )
    parser.add_argument('--univar-runtime-root', type=Path)
    parser.add_argument('--corrections-root', type=Path)
    parser.add_argument(
        '--skip-authoritative-selected-support',
        action='store_true',
        help='Skip selected-output support import. The final lineage validator will normally fail until this is imported.',
    )
    parser.add_argument(
        '--strict-current-model-support',
        action='store_true',
        help='Fail the full refresh if the current-model historical-support refresh cannot be rebuilt from the configured runtime roots.',
    )
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    bindings = load_runtime_bindings(article_root)
    workflow_root = args.workflow_root.resolve() if args.workflow_root is not None else binding_as_path(bindings, 'workflow_root')
    runtime_root = args.runtime_root.resolve() if args.runtime_root is not None else binding_as_path(bindings, 'exal_m_t1', 'keep_runtime_root')
    setup_support_runtime_root = (
        args.setup_support_runtime_root.resolve()
        if args.setup_support_runtime_root is not None
        else binding_as_path(bindings, 'exal_m_t1', 'setup_support_runtime_root')
    )
    multivar_support_run_root = (
        args.multivar_support_run_root.resolve()
        if args.multivar_support_run_root is not None
        else binding_as_path(bindings, 'exal_m_t1', 'historical_support_replay_run_root')
    )
    univar_runtime_root = (
        args.univar_runtime_root.resolve()
        if args.univar_runtime_root is not None
        else binding_as_path(bindings, 'exal_m_t1', 'univar_runtime_root')
    )
    authoritative_selected_support_output_root = (
        args.authoritative_selected_support_output_root.resolve()
        if args.authoritative_selected_support_output_root is not None
        else binding_as_optional_path(bindings, 'exal_m_t1', 'selected_support_output_root')
    )
    corrections_root = (
        args.corrections_root.resolve()
        if args.corrections_root is not None
        else binding_as_optional_path(bindings, 'corrections_root')
    )

    py = sys.executable
    run_optional([
        py,
        str(article_root / 'scripts' / 'refresh_current_model_output_support_figures.py'),
        '--article-root',
        str(article_root),
        '--workflow-root',
        str(workflow_root),
        '--multivar-runtime-root',
        str(runtime_root),
        '--multivar-support-run-root',
        str(multivar_support_run_root),
        '--univar-runtime-root',
        str(univar_runtime_root),
    ], article_root / 'artifacts' / 'historical_support_from_current_models' / 'refresh_status.json', strict=args.strict_current_model_support)
    if not args.skip_authoritative_selected_support:
        if authoritative_selected_support_output_root is None:
            raise RuntimeError(
                'No authoritative selected-support output root configured. '
                'Set config/runtime_bindings.json:exal_m_t1.selected_support_output_root '
                'or pass --authoritative-selected-support-output-root.'
            )
        run([
            py,
            str(article_root / 'scripts' / 'refresh_authoritative_selected_model_support_figures.py'),
            '--article-root',
            str(article_root),
            '--workflow-root',
            str(workflow_root),
            '--source-output-root',
            str(authoritative_selected_support_output_root),
        ])
    run([py, str(article_root / 'scripts' / 'refresh_exal_m_t1_generated_assets.py'), '--article-root', str(article_root), '--runtime-root', str(runtime_root)])
    run([
        py,
        str(article_root / 'scripts' / 'refresh_cutoff_synthesis_families.py'),
        '--article-root',
        str(article_root),
        '--multivar-runtime-root',
        str(runtime_root),
        '--univar-runtime-root',
        str(univar_runtime_root),
    ])
    run([py, str(article_root / 'scripts' / 'refresh_he2_manifest_snapshot.py'), '--article-root', str(article_root), '--workflow-root', str(workflow_root)])
    run([
        py,
        str(article_root / 'scripts' / 'refresh_setup_support_by_cutoff_v2.py'),
        '--article-root',
        str(article_root),
        '--workflow-runtime-root',
        str(setup_support_runtime_root),
    ])
    run([py, str(article_root / 'scripts' / 'build_setup_support_by_cutoff_v2_review.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_setup_support_transform_lineage_audit.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_setup_support_by_cutoff_v2_appendix.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'promote_cutoff_forecast_context_figures.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'promote_setup_support_v2_to_disc.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_generated_table_includes.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'promote_generated_figures_to_disc.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'sync_legacy_uppercase_figures.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_article_asset_review_report.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_figure_polish_status_audit.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_article_figure_lineage_audit.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'clean_article_legacy_assets.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'build_generated_asset_index.py'), '--article-root', str(article_root)])
    run([py, str(article_root / 'scripts' / 'validate_manuscript_figure_paths.py'), '--article-root', str(article_root)])
    lineage_cmd = [
        py,
        str(article_root / 'scripts' / 'validate_authoritative_output_lineage.py'),
        '--article-root',
        str(article_root),
    ]
    if corrections_root is not None:
        lineage_cmd.extend(['--corrections-root', str(corrections_root)])
    run(lineage_cmd)
    print('Refreshed all article-side generated assets successfully.')


if __name__ == '__main__':
    main()
