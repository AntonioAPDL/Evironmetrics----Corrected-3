# exAL-M-T1 Artifact-to-Run Map

Date: 2026-06-23

## Purpose

This file locks the reproducible `exAL-M-T1` source set used by the revised article and maps each manuscript object to its exact verified run/output source.

It is the run-level companion to:
- `docs/figure_table_provenance.md`
- `MANUSCRIPT_ASSET_MANIFEST.json`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/current_authority_refresh_runbook.md`

Important transition note:
- the main HE2 benchmark authority now combines the two retained canonical-grid winners for `20210123` and `20211112` with three clean `20260623` replays for `20211221`, `20220511`, and `20221225`;
- the refreshed clean replays are the source for the promoted CRPS values, representative synthesis panel, cutoff-specific multivariate synthesis panels, posterior table exports, and source/covariate summaries;
- the historical dry/wet and long-cycle seasonal support diagnostics are wired to the same current `2022-12-25` selected `exAL-M-T1` output authority as the representative synthesis figure, while remaining interpretation diagnostics rather than forecast-validation evidence.

## Cleanup status

The article repo cleanup on 2026-05-09 removed stale manuscript-facing figure copies and legacy article-side support bundles that were no longer part of the current workflow contract.

Current canonical article-side figure/table families are:
- `artifacts/representative_selected_model_2022_12_25/`
- `artifacts/five_cutoff_crps_validation_sources/`
- `artifacts/historical_support_from_current_models/`
- `artifacts/five_cutoff_setup_support/`
- `Figures/appendix_cutoff_panels/`
- `Figures/forecast_context_by_cutoff/`
- `tables/generated_tex/`

Removed legacy article-side families:
- `artifacts/historical_summary_sources/`
- `artifacts/workflow_linked_support_sources/`
- `artifacts/setup_support_by_cutoff/`
- `artifacts/setup_support_by_cutoff_review/`

`Figures/manuscript/` is now pruned automatically to the exact figure files named in `MANUSCRIPT_ASSET_MANIFEST.json`.

## 1. Locked reproducible source set

The revised article now carries a minimal local freeze of the five verified publication `exAL-M-T1` runs under:

- `artifacts/five_cutoff_crps_validation_sources/`

For each cutoff, that local freeze includes:
- `crps_forecast_summary.csv`
- `compare_report.json`
- `summary.json`

These local copies are derived from the verified workflow replay roots and should be treated as the article-side provenance anchor for the five-cutoff `exAL-M-T1` CRPS lineage.

## 2. Verified five-run publication lineage

| Cutoff | Local frozen copy | Authority run root | Authority CRPS source | Status |
|---|---|---|---|---|
| `2021-01-23` | `artifacts/five_cutoff_crps_validation_sources/20210123_exal_m_t1/` | `SOURCE_RUNTIME_REFERENCE/selected_exdqlm_multivariate_keep_20210123` | `post/outputs/.../tables/crps_forecast_summary.csv` | selected output, `0.13971` |
| `2021-11-12` | `artifacts/five_cutoff_crps_validation_sources/20211112_exal_m_t1/` | `SOURCE_RUNTIME_REFERENCE/selected_exdqlm_multivariate_keep_20211112` | `post/outputs/.../tables/crps_forecast_summary.csv` | selected output, `0.04724` |
| `2021-12-21` | `artifacts/five_cutoff_crps_validation_sources/20211221_exal_m_t1/` | `SOURCE_RUNTIME_REFERENCE/selected_exdqlm_multivariate_keep_20211221` | `post/outputs/.../tables/crps_forecast_summary.csv` | selected output, `0.26045` |
| `2022-05-11` | `artifacts/five_cutoff_crps_validation_sources/20220511_exal_m_t1/` | `SOURCE_RUNTIME_REFERENCE/selected_exdqlm_multivariate_keep_20220511` | `post/outputs/.../tables/crps_forecast_summary.csv` | selected output, `0.02273` |
| `2022-12-25` | `artifacts/five_cutoff_crps_validation_sources/20221225_exal_m_t1/` | `SOURCE_RUNTIME_REFERENCE/selected_exdqlm_multivariate_keep_20221225` | `post/outputs/.../tables/crps_forecast_summary.csv` | selected output, `0.53806` |

## 3. Representative selected-model bundle

The representative Section 5 cutoff is `2022-12-25`.

The revised article now carries a richer local copy of the verified representative output bundle under:

- `artifacts/representative_selected_model_2022_12_25/`

That bundle now includes:
- selected synthesis figures:
  - `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.(png,pdf)`
  - `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.(png,pdf)`
- synthesis exports:
  - `exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`
  - `exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv`
- figure provenance:
  - `figure_manifest.csv`
  - `publication_figure_manifest.csv`
  - `publication_style_used.yaml`
- posterior tables:
  - `covariate_effects_summary.csv/.tex`
  - `gamma_summary.csv/.tex`
  - `sigma_summary.csv/.tex`
  - `posterior_table_exports_manifest.csv`
- CRPS summaries:
  - `crps_forecast_summary.csv`
  - `crps_forecast_per_time.csv`

## 4. Manuscript artifact map

### In-scope objects now locked to the verified five-run/representative source set

| Manuscript object | Current role | Locked cutoff/run | Exact verified source | Current manuscript target | Current status |
|---|---|---|---|---|---|
| `tab:benchmark_crps_models` | five-cutoff validation table | HE2 publication freeze across all five cutoffs | local snapshot in `artifacts/he2_publication_freeze/`, with the `exAL-M-T1` row additionally locked to `artifacts/five_cutoff_crps_validation_sources/<slug>/crps_forecast_summary.csv` | values in `wileyNJD-APA.tex` Table 1 | locked |
| `fig:synth1` | representative selected-model illustration with retrospective and forecast-product overlays | `2022-12-25 exAL-M-T1 keep` | `artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png` | `Figures/multivariate_synthesis_by_cutoff/cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png` | refreshed from the five-cutoff synthesis family |
| `tab:components_23_31` | representative transfer-function summary | `2022-12-25 exAL-M-T1 keep` | `artifacts/representative_selected_model_2022_12_25/covariate_effects_summary.csv` | values in `wileyNJD-APA.tex` | refreshed |

### Supplementary appendix support tied to the representative selected-model run

| Manuscript object | Current role | Locked cutoff/run | Exact verified source | Current manuscript target | Current status |
|---|---|---|---|---|---|
| `tab:gamma_sigma_intervals1` | supplementary appendix `gamma` summary | `2022-12-25 exAL-M-T1 keep` | `artifacts/representative_selected_model_2022_12_25/gamma_summary.csv` | values in `wileyNJD-APA.tex` | refreshed |
| `tab:gamma_sigma_intervals2` | supplementary appendix `sigma` summary | `2022-12-25 exAL-M-T1 keep` | `artifacts/representative_selected_model_2022_12_25/sigma_summary.csv` | values in `wileyNJD-APA.tex` | refreshed |

### Interpretation and appendix support outside the forecast-validation table

These objects are not additional forecast-validation table entries. The selected-model dry/wet and long-cycle diagnostics are current representative selected-output interpretation support; the univariate transfer-active reference synthesis remains a separate appendix comparison.

| Manuscript object | Current role | Current source status | Action |
|---|---|---|---|
| `fig:synth2` | appendix univariate transfer-active reference | copied from the current `2022-12-25 exdqlm_univar` publication-style output bundle and frozen locally in `artifacts/historical_support_from_current_models/` | keep with explicit current-output support provenance; reference excludes retrospective-product and forecast-product source channels |
| `fig:dry_quantile` | selected-model fitted quantile-location diagnostic, dry regime | rendered from `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_quantile_dry_period.png` | keep as selected-model interpretation support from the current representative selected-output authority; not forecast-validation evidence |
| `fig:rainy_quantile` | selected-model fitted quantile-location diagnostic, wet regime | rendered from `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_quantile_wet_period.png` | keep as selected-model interpretation support from the current representative selected-output authority; not forecast-validation evidence |
| `fig:80_components` | main-text long-cycle component diagnostic | rendered from `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_component_80month.png` using raw state component 6 only | keep as selected-model interpretation support from the current representative selected-output authority; not forecast-validation evidence |

### Setup figures outside the selected-model refresh scope

| Manuscript object | Role | Action |
|---|---|---|
| `fig:sanlorenzo` | study-setting figure | now tied to the corrected `v2` cutoff-specific setup/support family; manuscript-facing `Figures/manuscript/site_context_usgs.png` is promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/usgs.png`, while all five cutoff variants are preserved under `artifacts/five_cutoff_setup_support/`. In the corrected contract this figure uses the full `1987-05-29 -> cutoff` USGS history available in the selected-run shared inputs. |
| `fig:covariates` | data/covariate setup figure | now tied to the corrected `v2` cutoff-specific setup/support family; manuscript-facing `Figures/manuscript/covariate_context_precip_soil_gdpc.png` is promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/...`, while all five cutoff variants are preserved under `artifacts/five_cutoff_setup_support/`. In the corrected contract this figure uses the full `1987-05-29 -> cutoff` raw PPT/SOIL histories together with the canonical GDPC history. |
| `fig:retrospectives` | retrospective-product setup figure | now tied to the corrected `v2` cutoff-specific setup/support family; manuscript-facing `Figures/manuscript/retrospective_products_context.png` is promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/...`, while all five cutoff variants are preserved under `artifacts/five_cutoff_setup_support/`. In the corrected contract this figure uses the retrospective support actually available for the cutoff-specific bundle, with the availability audit recorded alongside the figures. |
| `fig:ensembles` | forecast-product setup figure | now tied to the corrected `v2` cutoff-specific setup/support family; manuscript-facing `Figures/manuscript/forecast_products_context.png` is promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/...`, while advisor-facing cutoff-wide copies live under `Figures/forecast_context_by_cutoff/`. In the corrected contract this figure uses a strict `cutoff - 28 days` to `cutoff + 28 days` display window. |

## 5. What this means operationally

1. The five verified `exAL-M-T1` keep runs are now the locked reproducible source set for the main selected-model manuscript evidence.
2. Any further refresh of the central selected-model objects should preserve the current provenance split: `fig:synth1` comes from the five-cutoff synthesis-family overlay for 2022-12-25, while `tab:components_23_31` comes from the representative selected-model posterior-table exports recorded above.
3. The appendix support tables `tab:gamma_sigma_intervals1` and `tab:gamma_sigma_intervals2` should remain supplementary and should continue to use the representative `2022-12-25` source files recorded above.
4. `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components` are current representative selected-output support diagnostics.
   - They should remain distinguished from the forecast-validation evidence used for the main benchmark table.
   - Their article-side provenance anchor is now `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/`.
5. `fig:synth2` remains a separate univariate transfer-active appendix reference sourced from `artifacts/historical_support_from_current_models/`.

## 6. Locked choice for the current manuscript pass

For the current revised article pass, the chosen approach is:

1. keep `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components`
2. treat them explicitly as selected-model fitted quantile-location/component diagnostics
3. do not treat them as additional five-cutoff forecast-validation evidence
4. preserve their article-side provenance bundle in `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/`
5. keep the analysis-only component gallery out of the manuscript asset manifest
6. preserve `fig:synth2` in `artifacts/historical_support_from_current_models/`
7. preserve the corrected cutoff-dependent setup/support figures through:
   - `artifacts/five_cutoff_setup_support/`
   - optional local audit reports under ignored `reports/`
8. keep the article repo free of older `v1` / ad hoc support families; the cleanup step removes them automatically.
9. refresh the current-model support bundle through:
   - `scripts/refresh_current_model_output_support_figures.py`
10. refresh the corrected cutoff-specific setup/support family through:
   - `scripts/refresh_setup_support_by_cutoff_v2.py`
   - `scripts/build_setup_support_by_cutoff_v2_review.py`
   - `scripts/promote_setup_support_v2_to_disc.py`
11. promote manuscript-facing `Figures/manuscript/` figures through the source-controlled generated-asset manifest:
   - `MANUSCRIPT_ASSET_MANIFEST.json`
   - `scripts/promote_generated_figures_to_disc.py`
12. rebuild the manuscript table rows from the frozen article-side CSV exports through:
   - `scripts/build_generated_table_includes.py`
13. refresh the representative selected-model bundle and five-run source freeze through:
   - `scripts/refresh_exal_m_t1_generated_assets.py`
14. refresh the HE2 publication snapshot through:
   - `scripts/refresh_he2_manifest_snapshot.py`
15. refresh all article-side generated bundles and the review report through:
   - `scripts/refresh_all_generated_assets.py`
16. re-apply the article-side cleanup/audit contract through:
   - `scripts/clean_article_legacy_assets.py`

This is the strongest minimal choice because it preserves reproducibility, avoids mixing incompatible provenance roles, and does not require unnecessary reruns.
