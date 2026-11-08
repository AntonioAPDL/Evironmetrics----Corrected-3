# Revised Article Repository

This repository is the submission-facing freeze of the revised manuscript, its manuscript-facing figures and tables, and the article-local artifact bundles used to verify them.

## Where to look first

- `wileyNJD-APA.tex`: manuscript source used by Overleaf
- `Figures/manuscript/`: the exact figure files used by the manuscript
- `Figures/forecast_context_by_cutoff/`: cutoff-wide copies of the Figure 4 forecast-context view for all five cutoffs
- `Figures/multivariate_synthesis_by_cutoff/`: cutoff-wide selected-model synthesis family, including the supplementary overlay panels
- `Figures/reference_synthesis_by_cutoff/`: Figure A2-style reference-synthesis family for all five cutoffs
- `tables/generated_tex/`: the exact generated table blocks included by the manuscript
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

```bash
python3 scripts/refresh_all_generated_assets.py
```

The refresh path now includes a figure-path validation step. The manuscript keeps
the lowercase `figures/` tree as canonical, while `wileyNJD-APA.tex` also
accepts the legacy uppercase `Figures/` tree as a compile-time fallback for
Overleaf Git-sync compatibility.

For a benchmark-only authority refresh, prefer the narrower sequence in the
workflow runbook: refresh the HE2 manifest snapshot, selected-model bundles,
cutoff synthesis families, generated table includes, and corrections response
tables. Use the broad refresh only when setup/support, full-history diagnostic
assets, or local audit reports are intentionally being rebuilt too.

## Overleaf sync recovery

Overleaf can create `overleaf-*` branches that delete generated publication
assets under `figures/`, `Figures/`, `artifacts/`, or `tables/generated_tex/`.
Those deletion-only branches are not manuscript edits and should not be accepted
into `main`.

When Overleaf reports that GitHub and Overleaf could not automatically merge,
first audit the branch from this repo:

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
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```
