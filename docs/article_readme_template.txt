# Revised Article Repository

This repository is the submission-facing freeze of the revised manuscript, its manuscript-facing figures and tables, and the article-local artifact bundles used to verify them.

## Where to look first

- `wileyNJD-APA.tex`: the complete article and only Overleaf root
- `appendices.tex`: Appendices A--D, included in the article before its single bibliography
- `wileyNJD-APA.pdf`: locally reviewed complete article PDF (not versioned)
- `PUBLICATION_PACKAGE.json`: authoritative inventory of the article, its main/appendix scopes and submitted assets
- `docs/compact_publication.txt`: editorial dispositions, bounded regeneration and validation
- `docs/presentation_revision.txt`: current presentation, uncertainty and table revisions
- `docs/presentation_revision_release.json`: current source and proof record
- `docs/foundation_revision_release.json`: historical foundation-revision proof record
- `docs/appendix_integration_release.json`: historical integrated-appendix release record
- `docs/comment1_revision.txt`: implemented comment-1 changes and review/build entrypoints
- `docs/comment2_revision.txt`: external comparisons, fitting evidence and portable replay
- `Figures/manuscript/`: the exact figure files used by the manuscript
- `Figures/forecast_context_by_cutoff/`: cutoff-wide copies of the forecast-context view for all five cutoffs
- `Figures/multivariate_synthesis_by_cutoff/`: cutoff-wide selected-model synthesis family, including retained overlay panels
- `Figures/reference_synthesis_by_cutoff/`: univariate reference-synthesis family for all five cutoffs
- `tables/compact_publication/`: compact main and appendix tables from saved summaries
- `tables/editorial_revision/`: retained presentation sources, including the active appendix coefficient table
- `tables/generated_tex/`: retained original numerical tables and source-replay evidence
- `docs/figure_table_provenance.md`: figure/table provenance summary
- `artifacts/software_availability/software_availability_manifest.json`: compact HE-5 software availability and archive-status manifest
- `docs/software_availability_contract.md`: manuscript-side software reproducibility contract
- `scripts/validate_manuscript_figure_paths.py`: validates that every `\includegraphics{}` call in the manuscript resolves through the canonical figure search paths
- Public clean reproducibility bundle: `https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility`

For any future HE2 publication-authority replacement, start from the workflow
runbook:

- `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/current_authority_refresh_runbook.md`

Authority promotion is workflow-first. This article repo snapshots the promoted
manifest, generated tables, and figures after the workflow overlay and
validators pass.

## Directory roles

- `Figures/`: manuscript-facing figures, appendix cutoff panels, and cutoff-wide forecast/synthesis figure families
- `tables/`: generated TeX tables used by the manuscript
- `artifacts/`: frozen local bundles copied from validated workflow outputs
- `docs/`: submission-facing documentation and provenance notes
- `scripts/`: refresh and audit scripts used to rebuild the article-side bundles

## Standard refresh command

For the current compact reading package, use only:

```bash
python3 -B scripts/compact_publication.py --check
python3 -B scripts/predictive_synthesis_figures.py --check
python3 -B scripts/publication_package.py --check
```

The compact generator owns tables only. To regenerate them after an intentional
presentation change, run `python3 -B scripts/compact_publication.py`. Figures 2, B1
and B2 have one separate owner: `python3 -B scripts/predictive_synthesis_figures.py`.
It uses portable source-product inputs and unchanged saved means, intervals and
sample values, checks two independent exports, then promotes all three PDFs.
Run the three checks above after an intentional regeneration. Neither generator
fits models, produces forecasts or changes scores.
The active inventory describes what readers receive; the older
`MANUSCRIPT_ASSET_MANIFEST.json` retains the original scientific lineage.

For the earlier additive saved-output revision, the retained commands are:

```bash
python3 -B scripts/no_refit_revision.py --check
python3 -B scripts/refresh_no_refit_revision.py
```

These validate the frozen evidence and generate only the five new table files
and inventory guides. They do not fit models or call the broad legacy refresh.
See `docs/no_refit_revision.txt` for portable numerical replay and scope.
Use the full refresh below only for an intentional authority/asset rebuild.

```bash
python3 scripts/refresh_all_generated_assets.py
```

The refresh path includes a figure-path validation step. The canonical manuscript
assets are in uppercase `Figures/`, matching `MANUSCRIPT_ASSET_MANIFEST.json`.
Lowercase `figures/` is an optional compatibility copy. The historically named
`scripts/sync_legacy_uppercase_figures.py` copies only from `Figures/` to
`figures/`, preserves unmanaged files, and supports bounded `--relative-path`
updates. It never writes to the canonical tree.

For a benchmark-only authority refresh, prefer the narrower sequence in the
workflow runbook: refresh the HE2 manifest snapshot, selected-model bundles,
cutoff synthesis families, generated table includes, and corrections response
tables. Use the broad refresh only when setup/support, full-history diagnostic
assets, or local audit reports are intentionally being rebuilt too.

## Overleaf sync recovery

Overleaf can create `overleaf-*` branches that delete generated publication
assets under `figures/`, `Figures/`, `artifacts/`, `tables/generated_tex/`,
`tables/editorial_revision/` or `tables/compact_publication/`.
Those deletion-only branches are not manuscript edits and should not be accepted
into `main`.

When Overleaf reports that GitHub and Overleaf could not automatically merge,
first audit the branch from this repo. Install the local ancestry guard once:

```bash
python3 -B scripts/install_overleaf_guard.py
```

Its dispatcher lives in Git metadata outside the Overleaf-synchronized tree,
preserves existing hooks, and continues to work if an Overleaf merge changes the
tracked hook's executable permission. Before every main publication, also invoke
`python3 -B scripts/check_overleaf_sync.py` explicitly. The check queries live
Overleaf branches; it never discards or automatically merges their edits.

Audit a reported branch:

```bash
python3 scripts/merge_overleaf_branch_preserving_generated_assets.py --fetch origin/overleaf-YYYY-MM-DD-HHMM
```

If the audit reports no TeX/Bib source edits and only protected generated-asset
changes, merge it with:

```bash
python3 scripts/merge_overleaf_branch_preserving_generated_assets.py origin/overleaf-YYYY-MM-DD-HHMM --merge-generated-deletions-only
git push origin main
```

If real TeX/Bib source edits are present, merge them normally, but keep
generated article assets from `main` unless the workflow-side refresh scripts are
deliberately regenerating them.

## Standard compile command

```bash
python3 -B scripts/build_manuscript_review.py \
  --output-dir /tmp/NEW_article_review --jobname manuscript_review
```

Validate and build the complete article with all appendices:

```bash
python3 -B scripts/publication_package.py --check
python3 -B scripts/publication_package.py --build-dir /tmp/NEW_article_package
```

In Overleaf, keep `wileyNJD-APA.tex` as the main document. It includes
`appendices.tex`; the article, appendix tables/figures/algorithms and shared
references compile into one PDF. All appendix citations use local LaTeX labels.

Choose a new output directory for each build. The helper records source, table
and included-image hashes, LaTeX/BibTeX commands, label stability and PDF checks.
It builds from the article directory and keeps temporary files in the requested
output directory. `main.tex` is a wrapper for the same manuscript source.

The reviewed presentation assets are preserved by the checksummed registry in
`artifacts/comment1_figure_revision/`. Check it with
`python3 -B scripts/comment1_figure_revision.py --check`. A new numerical source
or selected-run identity requires a new inspected presentation revision.

## Point-2 evidence and table regeneration

The additive external comparisons and saved-fit diagnostics are in
`artifacts/comment2_revision/`. Validate them without writing:

```bash
python3 -B scripts/comment2_revision.py --check
```

Regenerate only the three new tables with `python3 -B scripts/comment2_revision.py`.
The validation preserves original article assets and checks imported scores,
climatological skill, training eligibility and diagnostic run identities.
`docs/comment2_revision.txt` and the artifact README describe portable baseline
replay. `docs/article_readme_template.txt` is the source of this README for the
asset-index builder.
