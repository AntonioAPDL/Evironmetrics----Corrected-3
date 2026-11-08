# Article Repository Structure

This document describes the current submission-facing structure of the revised
article repository after the cleanup and reproducibility rewiring pass on
2026-08-12.

## Purpose

The repository is organized so that a reader can separate three roles
immediately:

1. manuscript-facing assets actually used by the paper
2. frozen artifact bundles copied from validated workflow outputs
3. provenance and reproducibility contracts that document the wiring

## Top-level layout

- `wileyNJD-APA.tex`: manuscript source used by Overleaf
- `Figures/`: current tracked manuscript-facing figures, supplementary cutoff synthesis panels, and advisor-facing forecast-context copies
- `tables/`: generated TeX tables consumed by `\input{}` in the manuscript
- `artifacts/`: article-local frozen bundles copied from validated workflow outputs
- `docs/`: submission-facing documentation and provenance notes
- `scripts/`: refresh, promotion, and audit scripts used to regenerate the article-side state

The manuscript now resolves figures through a validated `\graphicspath` layer.
The current Overleaf-facing tracked tree is uppercase `Figures/`. The TeX
compile path also tolerates lowercase `figures/` paths because several older
local refresh helpers used that spelling before promotion.

## Manuscript-facing paths

### Figures used directly by the manuscript

- `Figures/manuscript/site_context_usgs.png`
- `Figures/manuscript/covariate_context_precip_soil_gdpc.png`
- `Figures/manuscript/retrospective_products_context.png`
- `Figures/manuscript/forecast_products_context.png`
- `Figures/manuscript/historical_summary_dry_period.png`
- `Figures/manuscript/historical_summary_wet_period.png`
- `Figures/multivariate_synthesis_by_cutoff/cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png`
- `Figures/manuscript/historical_component_80month.png`
- `Figures/manuscript/reference_synthesis_univariate.png`

### Supplementary cutoff synthesis figures

- `Figures/multivariate_synthesis_by_cutoff/cutoff_2021_01_23_multivariate_synthesis_with_reference_ensembles.png`
- `Figures/multivariate_synthesis_by_cutoff/cutoff_2021_11_12_multivariate_synthesis_with_reference_ensembles.png`
- `Figures/multivariate_synthesis_by_cutoff/cutoff_2021_12_21_multivariate_synthesis_with_reference_ensembles.png`
- `Figures/multivariate_synthesis_by_cutoff/cutoff_2022_05_11_multivariate_synthesis_with_reference_ensembles.png`

The former setup/support composites remain available as generated support artifacts under `Figures/appendix_cutoff_panels/` and `artifacts/five_cutoff_setup_support/`, but they are no longer included as manuscript appendix figures.

### Cutoff forecast-context figures

- `Figures/forecast_context_by_cutoff/cutoff_2021_01_23_forecast_context.png`
- `Figures/forecast_context_by_cutoff/cutoff_2021_11_12_forecast_context.png`
- `Figures/forecast_context_by_cutoff/cutoff_2021_12_21_forecast_context.png`
- `Figures/forecast_context_by_cutoff/cutoff_2022_05_11_forecast_context.png`
- `Figures/forecast_context_by_cutoff/cutoff_2022_12_25_forecast_context.png`

These are copies of the Figure 4 forecast-context view for every cutoff. They
are not all manuscript-facing paths, but they are refreshed automatically and
support cutoff-by-cutoff review before wider synthesis promotion work.

### Generated tables used directly by the manuscript

- `tables/generated_tex/benchmark_crps_main_table.tex`
- `tables/generated_tex/benchmark_crps_nws_horizon_table.tex`
- `tables/generated_tex/representative_covariate_effects_table.tex`
- `tables/generated_tex/appendix_gamma_summary_table.tex`
- `tables/generated_tex/appendix_sigma_summary_table.tex`
- `tables/generated_tex/he3_ablation_crps_main_table.tex`
- `tables/generated_tex/he3_ablation_crps_nws_horizon_table.tex`
- `tables/generated_tex/he4_quantile_check_loss_main_table.tex`

## Artifact bundles

- `artifacts/five_cutoff_setup_support/`
  - canonical five-cutoff setup/support family mirrored from the validated runtime bundle
- `artifacts/five_cutoff_main_model_synthesis/`
  - cutoff-wide synthesis figure family for the selected multivariate model
- `artifacts/five_cutoff_reference_synthesis/`
  - cutoff-wide reference synthesis figure family for the univariate reference model
- `artifacts/historical_support_from_current_models/`
  - appendix univariate transfer-active reference synthesis support
- `artifacts/representative_selected_model_2022_12_25/`
  - representative selected-model bundle for the verified 2022-12-25 exAL-M-T1 rerun, including the selected-model quantile-dynamic and long-cycle component diagnostics
- `artifacts/five_cutoff_crps_validation_sources/`
  - five-cutoff CRPS source freeze used by the benchmark table
- `artifacts/he2_publication_freeze/`
  - local snapshot of the workflow-side HE2 publication manifest
- `artifacts/he2_historical_support_audit/`
  - local snapshot of the workflow-side HE2 historical-support audit
- `artifacts/he3_exdqlm_ablation_authoritative/`
  - local snapshot of the authoritative HE3 component-removal sensitivity matrix and audit files
- `artifacts/he4_quantile_check_loss_current_publication/`
  - local snapshot of the current HE4 quantile check-loss artifact

## Local Review Bundles

Audit galleries and reviewer-workbench reports are not tracked in the
submission-facing repo. They may be regenerated locally by the refresh scripts
and are ignored under `reports/`. Preserved local copies from the cleanup pass
live under ignored `local_notes/`.

## Canonical manifest

The source-controlled selection contract is:

- `MANUSCRIPT_ASSET_MANIFEST.json`

This manifest records:

- manuscript-facing figure paths
- artifact-source paths for those figures
- manuscript table include paths
- artifact-source paths for the table inputs

## Standard refresh workflow

```bash
python3 scripts/refresh_all_generated_assets.py
```

This refresh path now does all of the following:

1. rebuild article-side artifact bundles
2. rebuild local review reports and audits under ignored `reports/`
3. promote manuscript-facing figure files from the manifest contract
4. promote the cutoff forecast-context and cutoff synthesis figure families
5. regenerate manuscript table blocks
6. remove the retired `DISC/` and `generated/` naming layers
7. rebuild inventory guides
8. validate that every manuscript `\includegraphics{}` call resolves to an
   existing figure asset

## Standard Compile Workflow

```bash
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```

## Public Reproducibility Bundle

The clean public reproducibility repository is:

- `https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility`

That repository is generated from the workflow repo with:

```bash
python3 scripts/export_san_lorenzo_exdqlm_reproducibility.py
```
