#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from article_repo_layout import build_layout

ARTIFACT_DESCRIPTIONS = {
    'five_cutoff_crps_validation_sources': 'Five-cutoff CRPS validation freeze used by the benchmark table.',
    'representative_selected_model_2022_12_25': 'Representative selected-model bundle for the verified 2022-12-25 exAL-M-T1 run, including synthesis, posterior tables, and authoritative q05/q50/q95 support figures.',
    'historical_support_from_current_models': 'Legacy/archive current-model support bundle. It must not feed the representative selected-model posterior-output figures.',
    'five_cutoff_setup_support': 'Canonical five-cutoff setup/support figure family mirrored from the validated workflow runtime bundle.',
    'five_cutoff_main_model_synthesis': 'Corrected cutoff-wide Figure 7 family copied from the five-cutoff he2pubgdpc1r1 exAL main-model reruns.',
    'five_cutoff_reference_synthesis': 'Cutoff-wide Figure A2-style reference synthesis family copied from the current exdqlm_univar output bundles.',
    'he2_publication_freeze': 'Frozen local snapshot of the current HE2 Bayesian publication manifest and alignment tables.',
    'he2_historical_support_audit': 'Workflow-side audit snapshot showing which publication rows use full historical support versus short-window support.',
    'software_availability': 'Compact HE-5 software availability and archive-status manifest for the revised article.',
}

REPORT_DESCRIPTIONS = {
    'manuscript_asset_review': 'Top-level review report, gallery, and wiring audit for manuscript figures and tables.',
    'manuscript_figure_selection': 'Manifest recording which artifact figures are currently promoted into the manuscript-facing figure directory.',
    'five_cutoff_setup_support_review': 'Review markdown, gallery, and audits for the five-cutoff setup/support figure family.',
    'five_cutoff_synthesis_review': 'Review markdown for the cutoff-wide Figure 7 and Figure A2 synthesis families.',
    'representative_setup_selection': 'Selection manifest recording which cutoff-specific setup/support bundle feeds Figures 1-4.',
}

PREFERRED_REVIEW_FILES = [
    'ARTICLE_ASSET_REVIEW.md',
    'FIGURE_POLISH_STATUS_AUDIT.md',
    'FIVE_CUTOFF_SETUP_SUPPORT_REVIEW.md',
    'CURRENT_MODEL_OUTPUT_WIRING_AUDIT.md',
    'TRANSFORM_AND_LINEAGE_AUDIT.md',
    'figure_gallery.html',
    'gallery.html',
    'README.md',
]


def count_files(root: Path) -> int:
    return sum(1 for p in root.rglob('*') if p.is_file())


def count_png(root: Path) -> int:
    return sum(1 for p in root.rglob('*.png') if p.is_file())


def pick_review_targets(root: Path) -> list[str]:
    picks: list[str] = []
    for name in PREFERRED_REVIEW_FILES:
        for p in sorted(root.rglob(name)):
            rel = p.relative_to(root)
            s = str(rel)
            if s not in picks:
                picks.append(s)
    return picks[:6]


def write_inventory_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['name', 'path', 'description', 'file_count', 'png_count', 'has_readme', 'review_targets'],
            lineterminator='\n',
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description='Build article-side inventory guides for artifacts and local reports.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    layout.ensure_base_dirs()

    artifact_rows = []
    for path in sorted(p for p in layout.artifacts_dir.iterdir() if p.is_dir()):
        artifact_rows.append({
            'name': path.name,
            'path': str(path.relative_to(article_root)),
            'description': ARTIFACT_DESCRIPTIONS.get(path.name, 'Artifact bundle.'),
            'file_count': count_files(path),
            'png_count': count_png(path),
            'has_readme': 'yes' if (path / 'README.md').exists() else 'no',
            'review_targets': ' | '.join(pick_review_targets(path)),
        })

    report_rows = []
    for path in sorted(p for p in layout.reports_dir.iterdir() if p.is_dir()):
        report_rows.append({
            'name': path.name,
            'path': str(path.relative_to(article_root)),
            'description': REPORT_DESCRIPTIONS.get(path.name, 'Report bundle.'),
            'file_count': count_files(path),
            'png_count': count_png(path),
            'has_readme': 'yes' if (path / 'README.md').exists() else 'no',
            'review_targets': ' | '.join(pick_review_targets(path)),
        })

    write_inventory_csv(layout.artifacts_dir / 'artifact_inventory.csv', artifact_rows)
    write_inventory_csv(layout.reports_dir / 'report_inventory.csv', report_rows)

    (layout.artifacts_dir / 'README.md').write_text(
        '# Article Artifacts\n\n'
        'These folders are the article-side frozen artifact bundles that feed the manuscript figures, tables, and supporting audits.\n\n'
        '| Artifact family | Description | Files | PNGs | README | Review entrypoints |\n'
        '|---|---|---:|---:|---|---|\n' + ''.join(
            f"| `{row['name']}` | {row['description']} | {row['file_count']} | {row['png_count']} | {row['has_readme']} | `{row['review_targets']}` |\n"
            for row in artifact_rows
        ) +
        '\nPreferred refresh entrypoint:\n- `scripts/refresh_all_generated_assets.py`\n'
    )

    (layout.reports_dir / 'README.md').write_text(
        '# Article Reports\n\n'
        'These folders contain local review reports, galleries, and manifest summaries for the current revised article state. '
        'They are generated audit outputs and are intentionally ignored in the submission-facing repository.\n\n'
        '| Report family | Description | Files | PNGs | README | Review entrypoints |\n'
        '|---|---|---:|---:|---|---|\n' + ''.join(
            f"| `{row['name']}` | {row['description']} | {row['file_count']} | {row['png_count']} | {row['has_readme']} | `{row['review_targets']}` |\n"
            for row in report_rows
        ) +
        '\nPreferred local review starting points:\n- `reports/manuscript_asset_review/ARTICLE_ASSET_REVIEW.md`\n- `reports/manuscript_asset_review/FIGURE_POLISH_STATUS_AUDIT.md`\n- `reports/five_cutoff_setup_support_review/FIVE_CUTOFF_SETUP_SUPPORT_REVIEW.md`\n'
    )

    (article_root / 'README.md').write_text(
        '# Revised Article Repository\n\n'
        'This repository is the submission-facing freeze of the revised manuscript, its manuscript-facing figures and tables, and the article-local artifact bundles used to verify them.\n\n'
        '## Where to look first\n\n'
        '- `wileyNJD-APA.tex`: manuscript source used by Overleaf\n'
        '- `Figures/manuscript/`: the exact figure files used by the manuscript\n'
        '- `Figures/forecast_context_by_cutoff/`: cutoff-wide copies of the Figure 4 forecast-context view for all five cutoffs\n'
        '- `Figures/multivariate_synthesis_by_cutoff/`: cutoff-wide selected-model synthesis family, including the supplementary overlay panels\n'
        '- `Figures/reference_synthesis_by_cutoff/`: Figure A2-style reference-synthesis family for all five cutoffs\n'
        '- `tables/generated_tex/`: the exact generated table blocks included by the manuscript\n'
        '- `docs/figure_table_provenance.md`: figure/table provenance summary\n'
        '- `artifacts/software_availability/software_availability_manifest.json`: compact HE-5 software availability and archive-status manifest\n'
        '- `docs/software_availability_contract.md`: manuscript-side software reproducibility contract\n'
        '- `scripts/validate_manuscript_figure_paths.py`: validates that every `\\includegraphics{}` call in the manuscript resolves through the canonical figure search paths\n'
        '- Public clean reproducibility bundle: `https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility`\n\n'
        'For any future HE2 publication-authority replacement, start from the workflow\n'
        'runbook:\n\n'
        '- `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/current_authority_refresh_runbook.md`\n\n'
        'Authority promotion is workflow-first. This article repo snapshots the promoted\n'
        'manifest, generated tables, and figures after the workflow\n'
        'overlay and validators pass.\n\n'
        '## Directory roles\n\n'
        '- `Figures/`: manuscript-facing figures, appendix cutoff panels, and cutoff-wide forecast/synthesis figure families\n'
        '- `tables/`: generated TeX tables used by the manuscript\n'
        '- `artifacts/`: frozen local bundles copied from validated workflow outputs\n'
        '- `docs/`: submission-facing documentation and provenance notes\n'
        '- `scripts/`: refresh and audit scripts used to rebuild the article-side bundles\n\n'
        '## Standard refresh command\n\n'
        '```bash\npython3 scripts/refresh_all_generated_assets.py\n```\n\n'
        'The refresh path now includes a figure-path validation step. The manuscript keeps\n'
        'the lowercase `figures/` tree as canonical, while `wileyNJD-APA.tex` also\n'
        'accepts the legacy uppercase `Figures/` tree as a compile-time fallback for\n'
        'Overleaf Git-sync compatibility.\n\n'
        'For a benchmark-only authority refresh, prefer the narrower sequence in the\n'
        'workflow runbook: refresh the HE2 manifest snapshot, selected-model bundles,\n'
        'cutoff synthesis families, generated table includes, and corrections response\n'
        'tables. Use the broad refresh only when setup/support, full-history diagnostic\n'
        'assets, or local audit reports are intentionally being rebuilt too.\n\n'
        '## Overleaf sync recovery\n\n'
        'Overleaf can create `overleaf-*` branches that delete generated publication\n'
        'assets under `figures/`, `Figures/`, `artifacts/`, or `tables/generated_tex/`.\n'
        'Those deletion-only branches are not manuscript edits and should not be accepted\n'
        'into `main`.\n\n'
        'When Overleaf reports that GitHub and Overleaf could not automatically merge,\n'
        'first audit the branch from this repo:\n\n'
        '```bash\n'
        'python3 scripts/merge_overleaf_branch_preserving_generated_assets.py --fetch origin/overleaf-YYYY-MM-DD-HHMM\n'
        '```\n\n'
        'If the audit reports no TeX/Bib source edits and only protected generated-asset\n'
        'changes, merge it with:\n\n'
        '```bash\n'
        'python3 scripts/merge_overleaf_branch_preserving_generated_assets.py origin/overleaf-YYYY-MM-DD-HHMM --merge-generated-deletions-only\n'
        'git push origin main\n'
        '```\n\n'
        'If real TeX/Bib source edits are present, merge them normally, but keep\n'
        'generated article assets from `main` unless the workflow-side refresh scripts are\n'
        'deliberately regenerating them.\n\n'
        '## Standard compile command\n\n'
        '```bash\npdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex\nbibtex output\npdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex\npdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex\n```\n'
    )


if __name__ == '__main__':
    main()
