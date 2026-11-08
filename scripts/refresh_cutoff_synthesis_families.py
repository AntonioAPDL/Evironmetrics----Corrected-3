#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from article_runtime_bindings import binding_as_path, load_runtime_bindings
from exal_m_t1_authoritative import load_authoritative_five_run_specs
from article_repo_layout import (
    CUTOFF_MULTIVARIATE_SYNTHESIS_FILENAMES,
    CUTOFF_MULTIVARIATE_SYNTHESIS_OVERLAY_FILENAMES,
    CUTOFF_REFERENCE_SYNTHESIS_FILENAMES,
    CUTOFF_REFERENCE_SYNTHESIS_OVERLAY_FILENAMES,
    build_layout,
)

UNIVAR_RUN_ID_BY_CUTOFF = {
    '20210123': 'multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_univar',
    '20211112': 'multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_univar',
    '20211221': 'multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_univar',
    '20220511': 'multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_univar',
    '20221225': 'multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar',
}

MULTIVAR_FILES = [
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.pdf',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png',
    'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.pdf',
    'exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv',
    'exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv',
    'publication_figure_manifest.csv',
    'publication_style_used.yaml',
]

UNIVAR_FILES = [
    'exdqlm_univar_synth_cutoff_window_posterior_samples.png',
    'exdqlm_univar_synth_cutoff_window_posterior_samples.pdf',
    'exdqlm_univar_synth_cutoff_window_posterior_samples_with_raw_ensembles.png',
    'exdqlm_univar_synth_cutoff_window_posterior_samples_with_raw_ensembles.pdf',
    'exdqlm_univar_synth_cutoff_window_quantiles.csv',
    'exdqlm_univar_synth_cutoff_window_sample_subset.csv',
    'publication_figure_manifest.csv',
    'publication_style_used.yaml',
]


def sha256sum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(src: Path, dst: Path) -> dict[str, str | int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        'source_path': str(src),
        'target_path': str(dst),
        'sha256': sha256sum(dst),
        'bytes': dst.stat().st_size,
    }


def copy_tree_file(src: Path, dst: Path) -> dict[str, str | int]:
    return copy_file(src, dst)


def write_rows(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def mirror_figure_family_to_lowercase(
    *,
    article_root: Path,
    uppercase_dir: Path,
    lowercase_dir: Path,
    manifest_rows: list[dict[str, str | int]],
) -> None:
    if lowercase_dir.exists():
        for child in lowercase_dir.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                shutil.rmtree(child)
    lowercase_dir.mkdir(parents=True, exist_ok=True)

    for src in sorted(path for path in uppercase_dir.iterdir() if path.is_file() and path.name != 'manifest.csv'):
        copy_tree_file(src, lowercase_dir / src.name)

    lower_rows: list[dict[str, str | int]] = []
    for row in manifest_rows:
        lower = dict(row)
        target = str(lower['target_path'])
        if target.startswith('Figures/'):
            target = 'figures/' + target[len('Figures/'):]
        lower['target_path'] = target
        lower_rows.append(lower)
    write_rows(lowercase_dir / 'manifest.csv', lower_rows)


def refresh_poster_frozen_synthesis(
    *,
    article_root: Path,
    source_overlay_path: Path,
) -> None:
    poster_frozen_dir = article_root / 'isba2026_poster' / 'figures' / 'frozen'
    if not poster_frozen_dir.exists():
        return
    target = poster_frozen_dir / source_overlay_path.name
    meta = copy_file(source_overlay_path, target)
    rows = [
        {
            'poster_file': target.name,
            'source_path': str(source_overlay_path.relative_to(article_root)),
            'target_path': str(target.relative_to(article_root)),
            'sha256': meta['sha256'],
            'bytes': meta['bytes'],
        }
    ]
    write_rows(poster_frozen_dir / 'manifest.csv', rows)


def _resolve_output_root(runtime_root: Path, run_id: str, cutoff_code: str, family_token: str) -> Path:
    output_root = runtime_root / 'runs' / run_id / 'post' / 'outputs' / run_id
    if output_root.exists():
        return output_root

    runs_root = runtime_root / 'runs'
    if not runs_root.exists():
        return output_root

    matches = []
    for run_root in sorted(runs_root.glob(f'multimodel_{cutoff_code}_*{family_token}*')):
        candidate = run_root / 'post' / 'outputs' / run_root.name
        if candidate.exists():
            matches.append(candidate)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = '\n  '.join(str(path) for path in matches)
        raise RuntimeError(
            f'Ambiguous {family_token} output roots for cutoff {cutoff_code} under {runtime_root}:\n  {joined}'
        )
    return output_root


def _source_output_roots(multivar_runtime_root: Path, univar_runtime_root: Path, spec: dict[str, str]) -> tuple[Path, Path]:
    multivar_root = (
        Path(spec['runtime_output_root'])
        if spec.get('runtime_output_root')
        else multivar_runtime_root
        / 'runs'
        / spec['multivar_run_id']
        / 'post'
        / 'outputs'
        / spec['multivar_run_id']
    )
    if not multivar_root.exists():
        multivar_root = _resolve_output_root(
            multivar_runtime_root,
            spec['multivar_run_id'],
            spec['cutoff_code'],
            'exdqlm_multivar_keep',
        )
    univar_root = (
        univar_runtime_root
        / 'runs'
        / spec['univar_run_id']
        / 'post'
        / 'outputs'
        / spec['univar_run_id']
    )
    if not univar_root.exists():
        univar_root = _resolve_output_root(
            univar_runtime_root,
            spec['univar_run_id'],
            spec['cutoff_code'],
            'exdqlm_univar',
        )
    return multivar_root, univar_root


def _run_root_from_output_root(output_root: Path) -> Path:
    return output_root.parents[2]


def _spec_with_resolved_output_roots(
    spec: dict[str, str],
    *,
    multivar_output_root: Path,
    univar_output_root: Path,
) -> dict[str, str]:
    resolved = dict(spec)
    resolved['multivar_run_id'] = multivar_output_root.name
    resolved['run_id'] = multivar_output_root.name
    resolved['runtime_run_root'] = str(_run_root_from_output_root(multivar_output_root))
    resolved['runtime_output_root'] = str(multivar_output_root)
    resolved['univar_run_id'] = univar_output_root.name
    resolved['univar_runtime_run_root'] = str(_run_root_from_output_root(univar_output_root))
    resolved['univar_runtime_output_root'] = str(univar_output_root)
    return resolved


def cutoff_specs(article_root: Path, multivar_runtime_root: Path | None) -> list[dict[str, str]]:
    specs = []
    for row in load_authoritative_five_run_specs(article_root, multivar_runtime_root):
        cutoff_code = row['cutoff_code']
        specs.append({
            'slug': row['slug'],
            'cutoff': row['cutoff'],
            'cutoff_code': cutoff_code,
            'multivar_run_id': row['multivar_run_id'],
            'grid_spec_id': row['grid_spec_id'],
            'univar_run_id': UNIVAR_RUN_ID_BY_CUTOFF[cutoff_code],
            'source_lineage': row['source_lineage'],
            'authoritative_manifest': row['authoritative_manifest'],
            'runtime_run_root': row.get('runtime_run_root', ''),
            'runtime_output_root': row.get('runtime_output_root', ''),
        })
    return specs


def _write_bundle(
    bundle_root: Path,
    *,
    family_name: str,
    source_run_id: str,
    source_output_root: Path,
    files: list[str],
) -> list[dict[str, str | int]]:
    bundle_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | int]] = []
    for rel in files:
        meta = copy_file(source_output_root / rel, bundle_root / Path(rel).name)
        rows.append(
            {
                'family_name': family_name,
                'source_run_id': source_run_id,
                'bundle_file': Path(rel).name,
                'source_relative_path': rel,
                'source_path': meta['source_path'],
                'target_path': meta['target_path'],
                'sha256': meta['sha256'],
                'bytes': meta['bytes'],
            }
        )
    with (bundle_root / 'manifest.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    (bundle_root / 'SHA256SUMS.txt').write_text(
        '\n'.join(f"{row['sha256']}  {row['bundle_file']}" for row in rows) + '\n', encoding='utf-8'
    )
    return rows


def _write_family_readme(path: Path, *, title: str, description: str) -> None:
    path.write_text(
        f'# {title}\n\n'
        f'{description}\n\n'
        'Refresh entrypoint:\n'
        '- `scripts/refresh_cutoff_synthesis_families.py`\n',
        encoding='utf-8',
    )


def write_figure_dir_readme(path: Path, *, title: str, family_description: str) -> None:
    path.write_text(
        f'# {title}\n\n'
        f'{family_description}\n\n'
        'These cutoff-wide copies are refreshed from the authoritative synthesis output roots. '
        'The representative 2022-12-25 manuscript figure is still promoted through '
        '`MANUSCRIPT_ASSET_MANIFEST.json`; the non-representative multivariate overlay copies '
        'are also available for the supplementary cutoff-specific synthesis panels.\n',
        encoding='utf-8',
    )


def build_review(layout) -> None:
    out_root = layout.five_cutoff_synthesis_review_dir
    out_root.mkdir(parents=True, exist_ok=True)

    multivar_rows = list(csv.DictReader((layout.cutoff_multivariate_synthesis_dir / 'manifest.csv').open('r', encoding='utf-8')))
    reference_rows = list(csv.DictReader((layout.cutoff_reference_synthesis_dir / 'manifest.csv').open('r', encoding='utf-8')))

    md: list[str] = []
    md.append('# Five-Cutoff Synthesis Review\n\n')
    md.append('This review bundle records the cutoff-wide synthesis families promoted into the revised article repo for Stage 1 contract qualification and supplementary cutoff-specific synthesis review.\n\n')
    md.append('## Family coverage\n\n')
    md.append('| Family | Cutoffs | Overlay variants | Review figure directory |\n')
    md.append('|---|---:|---:|---|\n')
    md.append(f"| `Figure 7` multivariate family | {sum(row['variant']=='primary' for row in multivar_rows)} | {sum(row['variant']=='overlay' for row in multivar_rows)} | `Figures/multivariate_synthesis_by_cutoff/` |\n")
    md.append(f"| `Figure A2` reference family | {sum(row['variant']=='primary' for row in reference_rows)} | {sum(row['variant']=='overlay' for row in reference_rows)} | `Figures/reference_synthesis_by_cutoff/` |\n")
    md.append('\n## Cutoff summary\n\n')
    md.append('| Cutoff | Multivariate source | Reference source |\n')
    md.append('|---|---|---|\n')
    by_cutoff_multi = {row['cutoff']: row for row in multivar_rows if row['variant'] == 'primary'}
    by_cutoff_ref = {row['cutoff']: row for row in reference_rows if row['variant'] == 'primary'}
    for cutoff in sorted(by_cutoff_multi):
        md.append(
            f"| {cutoff} | `{by_cutoff_multi[cutoff]['source_path']}` | `{by_cutoff_ref[cutoff]['source_path']}` |\n"
        )
    (out_root / 'FIVE_CUTOFF_SYNTHESIS_REVIEW.md').write_text(''.join(md), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Refresh cutoff-wide synthesis figure families into the revised article repo.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        '--multivar-runtime-root',
        type=Path,
    )
    parser.add_argument(
        '--univar-runtime-root',
        type=Path,
    )
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    bindings = load_runtime_bindings(article_root)
    multivar_runtime_root = (
        args.multivar_runtime_root.resolve()
        if args.multivar_runtime_root is not None
        else binding_as_path(bindings, 'exal_m_t1', 'keep_runtime_root')
    )
    univar_runtime_root = (
        args.univar_runtime_root.resolve()
        if args.univar_runtime_root is not None
        else binding_as_path(bindings, 'exal_m_t1', 'univar_runtime_root')
    )
    layout = build_layout(article_root)
    layout.ensure_base_dirs()

    multivar_figure_rows: list[dict[str, str | int]] = []
    reference_figure_rows: list[dict[str, str | int]] = []

    specs = cutoff_specs(
        article_root,
        args.multivar_runtime_root.resolve() if args.multivar_runtime_root is not None else None,
    )
    for spec in specs:
        multivar_output_root, univar_output_root = _source_output_roots(multivar_runtime_root, univar_runtime_root, spec)
        resolved_spec = _spec_with_resolved_output_roots(
            spec,
            multivar_output_root=multivar_output_root,
            univar_output_root=univar_output_root,
        )
        if not multivar_output_root.exists():
            raise FileNotFoundError(f'Missing multivariate synthesis output root: {multivar_output_root}')
        if not univar_output_root.exists():
            raise FileNotFoundError(f'Missing reference synthesis output root: {univar_output_root}')

        multivar_bundle_dir = layout.five_cutoff_main_model_synthesis_dir / spec['slug']
        reference_bundle_dir = layout.five_cutoff_reference_synthesis_dir / spec['slug']
        _write_bundle(
            multivar_bundle_dir,
            family_name='multivariate_synthesis',
            source_run_id=resolved_spec['multivar_run_id'],
            source_output_root=multivar_output_root,
            files=MULTIVAR_FILES,
        )
        _write_bundle(
            reference_bundle_dir,
            family_name='reference_synthesis',
            source_run_id=resolved_spec['univar_run_id'],
            source_output_root=univar_output_root,
            files=UNIVAR_FILES,
        )
        (multivar_bundle_dir / 'source_metadata.json').write_text(json.dumps(resolved_spec, indent=2) + '\n', encoding='utf-8')
        (reference_bundle_dir / 'source_metadata.json').write_text(json.dumps(resolved_spec, indent=2) + '\n', encoding='utf-8')

        primary_multivar = copy_file(
            multivar_output_root / 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png',
            layout.cutoff_multivariate_synthesis_path(spec['slug']),
        )
        overlay_multivar = copy_file(
            multivar_output_root / 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png',
            layout.cutoff_multivariate_synthesis_overlay_path(spec['slug']),
        )
        primary_reference = copy_file(
            univar_output_root / 'exdqlm_univar_synth_cutoff_window_posterior_samples.png',
            layout.cutoff_reference_synthesis_path(spec['slug']),
        )
        overlay_reference = copy_file(
            univar_output_root / 'exdqlm_univar_synth_cutoff_window_posterior_samples_with_raw_ensembles.png',
            layout.cutoff_reference_synthesis_overlay_path(spec['slug']),
        )

        multivar_figure_rows.extend(
            [
                {
                    'cutoff': spec['cutoff'],
                    'slug': spec['slug'],
                    'family': 'multivariate_synthesis',
                    'variant': 'primary',
                    'source_path': str(multivar_output_root / 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png'),
                    'target_path': str(layout.cutoff_multivariate_synthesis_path(spec['slug']).relative_to(article_root)),
                    'sha256': primary_multivar['sha256'],
                    'bytes': primary_multivar['bytes'],
                },
                {
                    'cutoff': spec['cutoff'],
                    'slug': spec['slug'],
                    'family': 'multivariate_synthesis',
                    'variant': 'overlay',
                    'source_path': str(multivar_output_root / 'exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png'),
                    'target_path': str(layout.cutoff_multivariate_synthesis_overlay_path(spec['slug']).relative_to(article_root)),
                    'sha256': overlay_multivar['sha256'],
                    'bytes': overlay_multivar['bytes'],
                },
            ]
        )
        reference_figure_rows.extend(
            [
                {
                    'cutoff': spec['cutoff'],
                    'slug': spec['slug'],
                    'family': 'reference_synthesis',
                    'variant': 'primary',
                    'source_path': str(univar_output_root / 'exdqlm_univar_synth_cutoff_window_posterior_samples.png'),
                    'target_path': str(layout.cutoff_reference_synthesis_path(spec['slug']).relative_to(article_root)),
                    'sha256': primary_reference['sha256'],
                    'bytes': primary_reference['bytes'],
                },
                {
                    'cutoff': spec['cutoff'],
                    'slug': spec['slug'],
                    'family': 'reference_synthesis',
                    'variant': 'overlay',
                    'source_path': str(univar_output_root / 'exdqlm_univar_synth_cutoff_window_posterior_samples_with_raw_ensembles.png'),
                    'target_path': str(layout.cutoff_reference_synthesis_overlay_path(spec['slug']).relative_to(article_root)),
                    'sha256': overlay_reference['sha256'],
                    'bytes': overlay_reference['bytes'],
                },
            ]
        )

    write_rows(layout.cutoff_multivariate_synthesis_dir / 'manifest.csv', multivar_figure_rows)
    write_rows(layout.cutoff_reference_synthesis_dir / 'manifest.csv', reference_figure_rows)

    write_figure_dir_readme(
        layout.cutoff_multivariate_synthesis_dir / 'README.md',
        title='Multivariate Synthesis By Cutoff',
        family_description='Cutoff-wide copies of the corrected selected-model synthesis family for all five cutoffs, including overlay companions with retrospective and forecast-product references.',
    )
    write_figure_dir_readme(
        layout.cutoff_reference_synthesis_dir / 'README.md',
        title='Reference Synthesis By Cutoff',
        family_description='Advisor-facing copies of the Figure A2-style reference synthesis family for all five cutoffs, including overlay companions with raw/reference ensembles.',
    )
    mirror_figure_family_to_lowercase(
        article_root=article_root,
        uppercase_dir=layout.cutoff_multivariate_synthesis_dir,
        lowercase_dir=layout.figures_dir / 'multivariate_synthesis_by_cutoff',
        manifest_rows=multivar_figure_rows,
    )
    mirror_figure_family_to_lowercase(
        article_root=article_root,
        uppercase_dir=layout.cutoff_reference_synthesis_dir,
        lowercase_dir=layout.figures_dir / 'reference_synthesis_by_cutoff',
        manifest_rows=reference_figure_rows,
    )
    refresh_poster_frozen_synthesis(
        article_root=article_root,
        source_overlay_path=layout.cutoff_multivariate_synthesis_overlay_path('20221225_exal_m_t1'),
    )

    _write_family_readme(
        layout.five_cutoff_main_model_synthesis_dir / 'README.md',
        title='Five-Cutoff Main Model Synthesis',
        description='Frozen cutoff-by-cutoff multivariate synthesis bundles copied from the authoritative canonical-grid exAL main-model winners.',
    )
    _write_family_readme(
        layout.five_cutoff_reference_synthesis_dir / 'README.md',
        title='Five-Cutoff Reference Synthesis',
        description='Frozen cutoff-by-cutoff reference synthesis bundles copied from the current publication-winning `exdqlm_univar` reruns.',
    )

    build_review(layout)
    print('Refreshed cutoff-wide synthesis figure families successfully.')


if __name__ == '__main__':
    main()
