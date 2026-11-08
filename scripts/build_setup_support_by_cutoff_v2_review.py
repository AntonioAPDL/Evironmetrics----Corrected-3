#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import yaml

from article_repo_layout import build_layout


def main() -> None:
    parser = argparse.ArgumentParser(description='Build an article-side review report for the five-cutoff setup/support figure family.')
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    bundle_root = layout.five_cutoff_setup_support_dir
    if not bundle_root.exists():
        raise FileNotFoundError(f'Missing article-side five-cutoff setup/support bundle: {bundle_root}')

    out_root = layout.five_cutoff_setup_support_review_dir
    out_root.mkdir(parents=True, exist_ok=True)

    cutoffs = sorted([p for p in bundle_root.iterdir() if p.is_dir() and p.name[:8].isdigit()])
    records = []
    for cutoff_dir in cutoffs:
        meta = json.loads((cutoff_dir / 'metadata' / 'cutoff_entry.json').read_text())
        support = yaml.safe_load((cutoff_dir / 'metadata' / 'support_window.yaml').read_text())
        policy = yaml.safe_load((cutoff_dir / 'metadata' / 'policy_summary.yaml').read_text())
        coverage = yaml.safe_load((cutoff_dir / 'metadata' / 'coverage_audit.yaml').read_text())
        scale = yaml.safe_load((cutoff_dir / 'metadata' / 'scale_contract.yaml').read_text())
        rows = list(csv.DictReader((cutoff_dir / 'review' / 'figure_manifest.csv').open()))
        records.append((cutoff_dir, meta, support, policy, coverage, scale, rows))

    with (out_root / 'figure_manifest.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['cutoff_dir', 'cutoff_date', 'published_crps', 'bundle_class', 'support_start', 'support_end', 'retrospective_available_start', 'retrospective_full_history_available', 'plot_start', 'plot_end', 'forecast_start_date', 'display_scale', 'selected_run_internal_analysis_scale', 'figure_name', 'article_bundle_path', 'sha256', 'bytes'])
        for cutoff_dir, meta, support, _policy, coverage, scale, rows in records:
            for row in rows:
                writer.writerow([
                    cutoff_dir.name,
                    meta['cutoff_date'],
                    meta['published_crps'],
                    meta['bundle_class'],
                    support['support_start'],
                    support['support_end'],
                    support['retrospective_available_start'],
                    coverage['retrospective']['full_history_available'],
                    support['plot_start'],
                    support['plot_end'],
                    support['forecast_start_date'],
                    scale['display_scale'],
                    scale.get('selected_run_internal_analysis_scale', ''),
                    row['figure_name'],
                    str((cutoff_dir / 'figures' / row['figure_name']).relative_to(article_root)),
                    row['sha256'],
                    row['bytes'],
                ])

    md = [
        '# Five-Cutoff Setup/Support Review\n\n',
        'This review bundle mirrors the validated cutoff-specific setup/support figures copied into the revised article repo.\n\n',
        'See also: `INPUT_ALIGNMENT_AUDIT.md` and `TRANSFORM_AND_LINEAGE_AUDIT.md` in this same directory.\n\n',
        '## Cutoff summary\n',
        '| Cutoff | Directory | Bundle class | Requested history | Retrospective available from | Forecast window | Flow display scale | Published CRPS |\n',
        '|---|---|---|---|---|---|---|---:|\n',
    ]
    for cutoff_dir, meta, support, policy, coverage, scale, _rows in records:
        md.append(f"| {meta['cutoff_date']} | `{cutoff_dir.name}` | `{meta['bundle_class']}` | {support['support_start']} to {support['support_end']} | {support['retrospective_available_start']} | {support['plot_start']} to {support['plot_end']} | {scale['display_scale']} | {meta['published_crps']} |\n")
    md.append('\n## Policy summary\n')
    md.append('| Cutoff | NWS policy | GloFAS policy | Notes |\n')
    md.append('|---|---|---|---|\n')
    for cutoff_dir, meta, support, policy, coverage, _scale, _rows in records:
        md.append(f"| {meta['cutoff_date']} | {policy['nws_policy_summary']} | {policy['glofas_policy_summary']} | {policy.get('notes','')} |\n")
    md.append('\n## Coverage audit\n')
    md.append('| Cutoff | USGS full history | PPT full history | SOIL full history | GDPC full history | Retros full history | Retros available start |\n')
    md.append('|---|---|---|---|---|---|---|\n')
    for cutoff_dir, meta, support, policy, coverage, _scale, _rows in records:
        md.append(
            f"| {meta['cutoff_date']} | {coverage['usgs']['full_history_available']} | {coverage['ppt']['full_history_available']} | "
            f"{coverage['soil']['full_history_available']} | {coverage['gdpc']['full_history_available']} | "
            f"{coverage['retrospective']['full_history_available']} | {coverage['retrospective']['available_start']} |\n"
        )
    (out_root / 'FIVE_CUTOFF_SETUP_SUPPORT_REVIEW.md').write_text(''.join(md))

    audit = []
    audit.append('# Input Alignment Audit\n\n')
    audit.append('This audit summarizes the selected-run input alignment assumptions for the cutoff-specific setup/support family mirrored into the article repo.\n\n')
    audit.append('## What this family represents\n\n')
    audit.append('- `usgs.png` documents the cutoff-specific USGS history carried by the selected-run shared inputs, while the covariate figure combines cutoff-specific PPT/SOIL histories with the canonical master GDPC factor sliced to the cutoff.\n')
    audit.append('- `retrospective_log_discharge_plot_faceted.png` documents the retrospective support actually available to the selected run for that cutoff.\n')
    audit.append('- `forecats.png` documents the short forecast-context window tied to the selected forecast products.\n\n')
    audit.append('## Cutoff summary\n\n')
    audit.append('| Cutoff | Bundle class | Requested history | Retros available from | Full retrospective history available? | Flow display scale |\n')
    audit.append('|---|---|---|---|---|---|\n')
    for cutoff_dir, meta, support, _policy, coverage, scale, _rows in records:
        audit.append(f"| {meta['cutoff_date']} | `{meta['bundle_class']}` | {support['support_start']} to {support['support_end']} | {support['retrospective_available_start']} | {coverage['retrospective']['full_history_available']} | {scale['display_scale']} |\n")
    audit.append('\n## Interpretation\n\n')
    audit.append('- The five-cutoff artifact bundle is copied directly from the validated workflow runtime family preserved under `artifacts/five_cutoff_setup_support/`.\n')
    audit.append('- For `2021-01-23`, `2021-11-12`, and `2022-12-25`, the selected retrospective support is genuinely short-window, so a full-history retrospective panel would no longer be the same figure class.\n')
    audit.append('- For `2021-12-21` and `2022-05-11`, the retrospective support is full-history within the mirrored cutoff-specific bundle.\n')
    audit.append('- All flow figures in this family now use the article display contract `log1p_cms`.\n')
    (out_root / 'FIVE_CUTOFF_SETUP_SUPPORT_REVIEW.md').write_text(''.join(md))
    (out_root / 'INPUT_ALIGNMENT_AUDIT.md').write_text(''.join(audit))

    html = [
        '<!doctype html><html><head><meta charset="utf-8"><title>Five-Cutoff Setup/Support Review</title>',
        '<style>body{font-family:Arial,sans-serif;margin:24px;} .cutoff{margin-top:36px;} .grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;} .card{border:1px solid #ddd;padding:12px;border-radius:8px;background:#fff;} img{max-width:100%;height:auto;border:1px solid #eee;} .meta{font-size:13px;color:#333;line-height:1.4;} code{background:#f4f4f4;padding:2px 4px;border-radius:4px;}</style></head><body>',
        '<h1>Five-Cutoff Setup/Support Review</h1>',
        '<p>These figures are generated from the validated cutoff-specific setup/support workflow and mirrored into the revised-article repo for review.</p>',
        '<p>See <code>INPUT_ALIGNMENT_AUDIT.md</code> and <code>TRANSFORM_AND_LINEAGE_AUDIT.md</code> in this same directory for the supporting audits.</p>'
    ]
    for cutoff_dir, meta, support, policy, coverage, scale, rows in records:
        html.append(f'<div class="cutoff"><h2>{meta["cutoff_date"]}</h2>')
        html.append(f'<p class="meta"><strong>Directory:</strong> <code>{cutoff_dir.name}</code><br><strong>Bundle class:</strong> <code>{meta["bundle_class"]}</code><br><strong>Requested history:</strong> {support["support_start"]} to {support["support_end"]}<br><strong>Retrospective available from:</strong> {support["retrospective_available_start"]}<br><strong>Forecast window:</strong> {support["plot_start"]} to {support["plot_end"]}<br><strong>Flow display scale:</strong> <code>{scale["display_scale"]}</code><br><strong>Selected-run internal scale:</strong> <code>{scale.get("selected_run_internal_analysis_scale", "")}</code><br><strong>NWS policy:</strong> {policy["nws_policy_summary"]}<br><strong>GloFAS policy:</strong> {policy["glofas_policy_summary"]}<br><strong>Coverage audit:</strong> USGS={coverage["usgs"]["full_history_available"]}, PPT={coverage["ppt"]["full_history_available"]}, SOIL={coverage["soil"]["full_history_available"]}, GDPC={coverage["gdpc"]["full_history_available"]}, Retros={coverage["retrospective"]["full_history_available"]}</p>')
        html.append('<div class="grid">')
        for row in rows:
            rel = Path(os.path.relpath(cutoff_dir / 'figures' / row['figure_name'], out_root))
            html.append('<div class="card">')
            html.append(f'<h3>{row["figure_name"]}</h3>')
            html.append(f'<p class="meta"><strong>SHA256:</strong> <code>{row["sha256"][:16]}...</code><br><strong>Bytes:</strong> {row["bytes"]}</p>')
            html.append(f'<img src="{rel.as_posix()}" alt="{row["figure_name"]}">')
            html.append('</div>')
        html.append('</div></div>')
    html.append('</body></html>')
    (out_root / 'gallery.html').write_text(''.join(html))
    print('Built five-cutoff setup/support review successfully.')


if __name__ == '__main__':
    main()
