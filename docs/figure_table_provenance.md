# Figure and Table Provenance Inventory

## Scope

This document records the current provenance status of manuscript figures and interpretation-dependent tables for the revised Environmetrics article.

Primary manuscript repo:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`

Primary workflow repo currently linked to figure/table generation:
- `/data/muscat_data/jaguir26/project1_ucsc_phd`

Main purpose:
- identify which manuscript outputs are already traceable to the current workflow,
- distinguish reproducible workflow-linked outputs from legacy or ambiguous outputs,
- and define the next regeneration tasks needed to align all interpretation material with the final selected `exAL-M-T1` analysis behind Table 1.

Tracked article-side companions:
- `MANUSCRIPT_ASSET_MANIFEST.json`
- `docs/exal_m_t1_artifact_run_map.md`
- `docs/forecast_design_contract.md`
- `docs/latest_forecast_issue_contract.md`
- `docs/software_availability_contract.md`

Setup/support figure correction plan:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_FILE_PLAN.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_ACCEPTANCE_CHECKLIST.md`

Canonical forward runbook:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/CANONICAL_REVISED_ARTICLE_WORKFLOW.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_FULL_HISTORY_REPAIR_FORWARD_PLAN.md`

Article-side provenance refresh helper:
- `MANUSCRIPT_ASSET_MANIFEST.json`
- `scripts/refresh_current_model_output_support_figures.py`
- `scripts/refresh_exal_m_t1_generated_assets.py`
- `scripts/refresh_he2_manifest_snapshot.py`
- `scripts/refresh_setup_support_by_cutoff_v2.py`
- `scripts/build_generated_table_includes.py`
- `scripts/promote_generated_figures_to_disc.py`
- `scripts/build_setup_support_by_cutoff_v2_appendix.py`
- `scripts/clean_article_legacy_assets.py`
- `scripts/build_generated_asset_index.py`
- `scripts/refresh_all_generated_assets.py`

Tracked article-side provenance outputs:
- `tables/generated_tex/README.md`
- `artifacts/README.md`
- `artifacts/artifact_inventory.csv`
- `artifacts/he2_historical_support_audit/historical_support_audit.md`
- `Figures/multivariate_synthesis_by_cutoff/README.md`
- `Figures/appendix_cutoff_panels/README.md`
- `Figures/forecast_context_by_cutoff/README.md`

Local audit reports and HTML galleries are generated under ignored `reports/`
when the broad refresh workflow is run. They are not part of the
submission-facing tracked repository.

This inventory now distinguishes three reproducibility levels:
- objects frozen locally in the article repo and tied to verified selected-model reruns,
- objects frozen locally in the article repo as canonical current-output or setup/support `v2` support bundles,
- and the underlying workflow-side generators that remain the authoritative reproduction path.

## Overall conclusion

The manuscript repo is **not fully self-contained** for figure/table generation. It now contains frozen local provenance bundles for all current figure/table assets used by the article, but the authoritative generators still live in the workflow repo above.

Most important results from this audit:
- every figure file currently used by the manuscript and checked below matches the workflow repo's recorded gold hash exactly.
- every current figure/table asset in the article is now either:
  - tied to a verified selected-model rerun bundle,
  - or frozen locally as a workflow-linked support figure.
- the manuscript-facing `Figures/manuscript/` figures are now promoted from a source-controlled generated-asset manifest rather than by manual selection.
- the model-derived manuscript tables now consume generated `\\input{}` row includes rebuilt from frozen article-side CSV sources.

That means the current manuscript figures are strongly linked to the current workflow repo, even though the manuscript repo itself does not carry the full generation scripts.

## 2026-06-23 HE2 authority refresh

The active HE2 publication authority was refreshed on 2026-06-23. The main
benchmark table, five-cutoff CRPS validation sources, representative
`2022-12-25` synthesis bundle, posterior table exports, source/covariate
summaries, and cutoff-specific multivariate synthesis panels now use:

- retained canonical-grid winners for `20210123` and `20211112`;
- clean replays from
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623`
  for `20211221`, `20220511`, and `20221225`.

Under this refreshed authority, `exAL-M-T1` has the lowest 28-day CRPS in all
five rolling-origin cutoffs: `0.13971`, `0.04724`, `0.26045`, `0.02273`, and
`0.53806`.

The HE3 component-removal sensitivity matrix remains a fixed sensitivity
analysis anchored to the current exAL-M-T1 authority recorded in the article manifests.
It should not be read as a replacement for the refreshed HE2 benchmark
authority.

The full-history dry/wet and long-cycle seasonal support diagnostics are now
wired to the same current `2022-12-25` selected `exAL-M-T1` output authority as
the representative synthesis figure. They remain interpretation diagnostics
only, not forecast-validation evidence.

The clean current generator contract is:
- `R/unified/stages/stage_post.R`
- `scripts/run_environmetrics_figures.R`
- `R/environmetrics/40_figures.R`

The software availability and archival-release contract is indexed under:
- `docs/software_availability_contract.md`
- `artifacts/software_availability/software_availability_manifest.json`

The article-side generated asset freeze point is now indexed under:
- `artifacts/README.md`
- `artifacts/artifact_inventory.csv`

The supplementary cutoff-specific selected-model synthesis overlays now live under:
- `Figures/multivariate_synthesis_by_cutoff/`

The former composite cutoff setup/support panels remain generated support artifacts under:
- `Figures/appendix_cutoff_panels/`

The weaker historical entrypoint is:
- `scripts/make_environmetrics_figures.R`

That legacy script still relies on notebook-linearized state and hard-coded external paths, so it should not be treated as the primary current reproduction contract.

## 2026-05-06 selected-model refresh status

The representative selected-model refresh is now partially complete.

Verified source run:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`

Verified status:
- `validation_status=pass`
- `compare_status=pass`
- deterministic-climate validation passes
- posterior table exports are present

The revised manuscript repo now contains a local copy of the representative selected-model artifacts under:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/artifacts/representative_selected_model_2022_12_25`

Those copied artifacts include:
- `posterior_samples_valid.png`
- `covariate_effects_summary.csv/.tex`
- `gamma_summary.csv/.tex`
- `sigma_summary.csv/.tex`
- `posterior_table_exports_manifest.csv`

Current manuscript refreshes already tied to verified selected-model outputs:
- `Figures/multivariate_synthesis_by_cutoff/cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png`, promoted from the five-cutoff main-model synthesis family for the representative 2022-12-25 cutoff
- `tab:components_23_31`
- `tab:gamma_sigma_intervals1`
- `tab:gamma_sigma_intervals2`

The narrow exAL-M-T1 relaunch is now verified across all five publication cutoffs.

The exact manuscript-side artifact mapping is recorded in:
- `docs/exal_m_t1_artifact_run_map.md`

That companion file should now be treated as the most direct answer to:
- which manuscript objects are locked to the verified five-run keep lineage,
- which objects are already refreshed from the representative `2022-12-25` run,
- and which remaining figures are workflow-linked support objects outside the narrow keep-run source set.

The revised manuscript repo now carries its current support-side freeze under:
- `artifacts/historical_support_from_current_models/`
- `artifacts/five_cutoff_setup_support/`

Legacy article-side support bundles removed during the 2026-05-09 cleanup:
- `artifacts/historical_summary_sources/`
- `artifacts/workflow_linked_support_sources/`
- `artifacts/setup_support_by_cutoff/`
- `artifacts/setup_support_by_cutoff_review/`

It also contains a dedicated cutoff-specific setup/support figure family derived from the five verified `exAL-M-T1` run bundles:
- `artifacts/five_cutoff_setup_support/`
- optional local audit outputs under ignored `reports/`

That family is produced from the current workflow-side derivation path:
- `config/exal_m_t1_setup_support_by_cutoff_v2_20260516.json`
- `scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py`
- `scripts/render_setup_support_bundle_v2.R`
- `scripts/setup_support_bundle_v2_helpers.R`
- `scripts/validate_exal_m_t1_setup_support_v2.py`
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_BY_CUTOFF_V2_WORKFLOW.md`

Current article-facing status:
- the corrected `v2` setup/support family is now implemented, validated, and mirrored locally;
- the manuscript-facing `Figures/manuscript/` copies are promoted from the representative `20221225_exal_m_t1` bundle;
- legacy `v1` and ad hoc support families have been removed from the article repo.

The current support families can now be refreshed through:
- `scripts/refresh_current_model_output_support_figures.py`
- `scripts/refresh_setup_support_by_cutoff_v2.py`
- `scripts/build_setup_support_by_cutoff_v2_appendix.py`
- `scripts/clean_article_legacy_assets.py`

The representative selected-model bundle and the HE2 snapshot can now be refreshed through:
- `scripts/refresh_exal_m_t1_generated_assets.py`
- `scripts/refresh_he2_manifest_snapshot.py`

The preferred top-level article-side refresh entrypoint is:
- `scripts/refresh_all_generated_assets.py`

The representative selected-model support refresh also writes an analysis-only
component gallery under:
- `artifacts/representative_selected_model_2022_12_25/authoritative_support/analysis_figures/component_evolution/`

That gallery is rendered from the same compact selected-model support CSVs as
Figure A1. It includes raw retained state components plus analysis-only
`component_6_plus_trend_component_1_samplewise` and
`component_6_minus_trend_component_1_samplewise` diagnostics.
It is checksummed in the local artifact bundle but intentionally not registered
in `MANUSCRIPT_ASSET_MANIFEST.json`.
For the current refresh, the compact quantile-dynamics and component summaries
are rebuilt from retained selected-model `.RData` objects; the previous compact
support root is used only for dates and observed USGS plotting values.

The compact posterior support CSV/RDS files used to render this gallery are not
persisted in the Overleaf-facing article repo. They remain workflow/runtime
source artifacts and are staged in a temporary directory by
`scripts/refresh_authoritative_selected_model_support_figures.py` during
refresh. This keeps the article repository focused on manuscript tables,
figures, and small provenance manifests.

## Current workflow evidence

### Figure-generation evidence

The workflow repo contains the following direct figure-generation references:
- authoritative current path:
  - `R/environmetrics/40_figures.R`
  - `scripts/run_environmetrics_figures.R`
  - `R/unified/stages/stage_post.R`
- legacy / historical references:
  - `scripts/make_environmetrics_figures.R`
  - `Environmetrics_Figures.ipynb`
  - `repro/extracted/Environmetrics_Figures__RECOVERED_WORKING.r`
- provenance / validation:
  - `repro/REPO_MAP.md`
  - `repro/REPRODUCE_PAPER.md`
  - `repro/gold_DISC_figures.sha256`

### Posterior-table export evidence

The workflow repo contains the following table-export infrastructure:
- `R/environmetrics/02_helpers_core.R`
- `R/unified/stages/stage_post.R`
- `R/unified/post_artifact_contract.R`
- `repro/UNIFIED_WORKFLOW_README.md`
- `tests/testthat/test_post_posterior_table_exports.R`

The documented post-stage outputs are:
- `gamma_summary.csv`
- `sigma_summary.csv`
- `covariate_effects_summary.csv`
- optional `.tex` snippets for the same summaries
- `posterior_table_exports_README.md`
- `posterior_table_exports_manifest.csv`

## Current-rating flood-reference lines

The horizontal reference lines on discharge-scale manuscript figures are not
stage values and are not historical flood-stage classifications. They are
approximate current-rating discharge equivalents of current NWS stage categories
for BTEC1/USGS 11160500.

Official source identity:
- NOAA/CNRFC `BTEC1`: San Lorenzo River -- Big Trees.
- USGS `11160500`: San Lorenzo R a Big Trees CA.

Rating source:
- USGS expanded shift-adjusted stage-discharge rating table:
  `https://waterdata.usgs.gov/nwisweb/get_ratings?file_type=exsa&site_no=11160500`
- Rating id: `40.0`
- Rating type: `STGQ`, stage-discharge
- Effective beginning: `2025-11-13 13:15 PST`
- Retrieved in source file: `2026-07-06 16:50:01`
- Status: provisional and subject to change

Displayed article levels:

| NWS category | Stage ft | Rating 40.0 discharge cfs | Discharge m^3/s | log(1 + m^3/s) |
|---|---:|---:|---:|---:|
| Minor | 16.50 | 7402.38 | 209.612058876 | 5.350017858 |
| Major | 21.76 | 14895.73 | 421.800101286 | 6.046899494 |

Full verified but not plotted by default:
- Action/monitor: 14.00 ft, 4864.84 cfs, `log1p_cms = 4.932723683`
- Moderate: 19.50 ft, 11302.95 cfs, `log1p_cms = 5.771640172`

Interpretation contract:
- Use the lines as present-day operational magnitude references only.
- Do not describe them as direct NOAA flood stages on the discharge axis.
- Do not use them to classify historical daily-mean observations as
  flood-stage exceedances.
- If stricter historical flood-stage classification is needed, use
  contemporaneous stage observations and rating curves for the relevant dates.

## Figure provenance map

### High-confidence, workflow-linked figures already matching the recorded gold outputs

The following manuscript figure assets in `Evironmetrics---REVISED-DOC-Corrected-2/Figures/manuscript/` were hashed locally and match the workflow repo's `repro/gold_DISC_figures.sha256` exactly.

| Manuscript label | Current asset | Current manuscript role | Workflow evidence | Hash match | Repro status | Selected-run status | Recommended action |
|---|---|---|---|---|---|---|---|
| `fig:sanlorenzo` | `Figures/manuscript/site_context_usgs.png` | study-setting figure | corrected cutoff-specific `v2` bundle built from the CRPS-linked `exAL-M-T1` source manifest and authoritative figure-input bundles; manuscript-facing copy promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/usgs.png`; current contract uses full `1987-05-29 -> cutoff` USGS history | yes | reproducible through validated `v2` workflow and frozen locally | representative `2022-12-25` support role; all five cutoff variants preserved | keep as representative setup/support figure with explicit cutoff-specific provenance |
| `fig:covariates` | `Figures/manuscript/covariate_context_precip_soil_gdpc.png` | covariate setup figure | corrected `v2` bundle reads raw cutoff-specific `cov_01_PPT.csv` and `cov_02_SOIL.csv`, together with the canonical `GDPC1` master factor truncated to the cutoff; manuscript-facing copy is promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/...`; current contract uses the full `1987-05-29 -> cutoff` covariate history | yes | reproducible through validated `v2` workflow and frozen locally | representative `2022-12-25` support role; all five cutoff variants preserved | keep as representative setup/support figure with explicit cutoff-specific provenance |
| `fig:retrospectives` | `Figures/manuscript/retrospective_products_context.png` | retrospective-product setup figure | corrected `v2` bundle reads authoritative retrospective lineage / bundle-native retrospective sources; manuscript-facing copy promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/...`; current contract uses the retrospective support actually available for the selected cutoff and records whether full history is present | yes | reproducible through validated `v2` workflow and frozen locally | representative `2022-12-25` support role; all five cutoff variants preserved | keep as representative setup/support figure with explicit cutoff-specific provenance |
| `fig:ensembles` | `Figures/manuscript/forecast_products_context.png` | forecast-product setup figure | corrected `v2` bundle stages bundle-native forecast inputs through `forecats_plot_bundle.R`; manuscript-facing copy promoted from `artifacts/five_cutoff_setup_support/20221225_exal_m_t1/figures/...`; current contract uses a strict `cutoff - 28 days` to `cutoff + 28 days` display window | yes | reproducible through validated `v2` workflow and frozen locally | representative `2022-12-25` support role; advisor-facing cutoff-wide copies also live under `Figures/forecast_context_by_cutoff/` | keep as representative setup/support figure with explicit cutoff-specific provenance |
| `fig:dry_quantile` | `Figures/manuscript/historical_summary_dry_period.png` | selected-model fitted quantile-location diagnostic, dry regime | `2022-12-25 exAL-M-T1` selected-output support figure copied from `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_quantile_dry_period.png` | yes | current representative selected-output interpretation support | selected-model support diagnostic; not part of the refreshed forecast-validation evidence | keep as selected-model diagnostic, not forecast-validation evidence |
| `fig:rainy_quantile` | `Figures/manuscript/historical_summary_wet_period.png` | selected-model fitted quantile-location diagnostic, wet regime | `2022-12-25 exAL-M-T1` selected-output support figure copied from `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_quantile_wet_period.png` | yes | current representative selected-output interpretation support | selected-model support diagnostic; not part of the refreshed forecast-validation evidence | keep as selected-model diagnostic, not forecast-validation evidence |
| `fig:synth1` | `Figures/multivariate_synthesis_by_cutoff/cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png` | predictive synthesis illustration | clean 2022-12-25 member of the five-cutoff main-model synthesis family, with exact source `artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png` | yes | reproducible from the five-cutoff selected `exAL-M-T1` synthesis family and frozen locally | locked to representative `2022-12-25` selected-model synthesis output | keep synced to the five-cutoff synthesis family rather than the older manuscript-only representative copy |
| `fig:80_components` | `Figures/manuscript/historical_component_80month.png` | selected-model long-cycle seasonal-component diagnostic with dry/wet overlays | `2022-12-25 exAL-M-T1` selected-output support figure copied from `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_component_80month.png` using raw state component 6 only | yes | current representative selected-output interpretation support | selected-model support diagnostic; not part of the refreshed forecast-validation evidence | keep as selected-model diagnostic, not forecast-validation evidence |
| `fig:synth2` | `Figures/manuscript/reference_synthesis_univariate.png` | appendix univariate transfer-active predictive synthesis | current `2022-12-25 exdqlm_univar` publication-style output bundle copied into `artifacts/historical_support_from_current_models/` | yes | reproducible from current model outputs and frozen locally in the article repo | current-model appendix support figure outside the narrow five-run keep lineage | keep with explicit current-output support provenance; reference excludes retrospective-product and forecast-product source channels |

### Notes on figure confidence

1. The four setup/support figures are now reproduced through the corrected cutoff-specific `v2` workflow.
   - Workflow-side review:
     - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_v2_20260516/review/`
   - Article-side mirror:
     - `artifacts/five_cutoff_setup_support/`
   - Representative manuscript promotion is governed by:
     - `MANUSCRIPT_ASSET_MANIFEST.json`
   - This validated family covers:
     - `usgs.png`
     - `precip_soilmoisture_climatePC1_faceted_labeled.png`
     - `retrospective_log_discharge_plot_faceted.png`
     - `forecats.png`
   - The corrected `v2` contract is now:
     - `usgs.png` and the raw covariate figure use the full `1987-05-29 -> cutoff` daily history available in the selected-run shared inputs
     - `forecats.png` uses a strict `cutoff - 28 days` to `cutoff + 28 days` display window
     - the retrospective figure now uses repaired full-history retrospective support from `1987-05-29 -> cutoff` for all five cutoffs through the canonical `20260510` shared-input bundles
   - Per-cutoff availability audits can be regenerated locally under ignored `reports/`.
   - The older `20260506` `v1` family has been removed from the article repo as part of the cleanup pass; only the canonical `v2` family remains.

2. `forecats.png` remains more delicate than the other setup figures, but the canonical `v2` path now stages bundle-native forecast inputs explicitly.
   - The workflow repo includes a dedicated reproducibility plan at:
     - `repro/FORECATS_INPUTS_AND_WEIGHTING_PLAN.md`
   - The corrected cutoff-specific derivation anchors that figure to the CRPS-linked `exAL-M-T1` source manifest and the selected forecast/setup support bundles instead of the older generic paper-level copy.

3. The dry/wet regime figures and the appendix long-cycle figure are now regenerated from the representative selected-model support bundle.
   - They are locked to the same `2022-12-25 exAL-M-T1` selected-output authority as the representative synthesis figure.
   - They are frozen locally in:
     - `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/`
   - Their role remains descriptive support:
     - selected-model fitted quantile-location and component diagnostics,
     - not full posterior predictive distributions,
     - and not a second forecast-validation exercise.

4. The older notebook/manual reproduction notes are now secondary.
   - `repro/REPRODUCE_PAPER.md` and `repro/REPO_MAP.md` remain useful provenance references.
   - But the clean current reproduction path is the run-scoped unified workflow:
     - `stage_post.R` injects the actual shared input paths,
     - `run_environmetrics_figures.R` runs headlessly,
     - `40_figures.R` generates the figures.

5. `fig:synth1` remains the representative selected-model synthesis figure for the `2022-12-25` cutoff, but the manuscript now uses the cutoff-family overlay in `Figures/multivariate_synthesis_by_cutoff/` so that the main-text panel and appendix cutoff panels share one synthesis-figure convention.
   - `fig:synth2` is now refreshed from a current `exdqlm_univar` output bundle.
   - It remains outside the narrow five-run keep-lineage freeze used for the main benchmark table.

## Table provenance map

### Interpretation-dependent tables in the manuscript

| Manuscript label | Current manuscript role | Current provenance evidence | Confidence | Repro status | Selected-run status | Recommended action |
|---|---|---|---|---|---|---|
| `tab:benchmark_crps_models` | main five-cutoff forecast-validation table | HE2 publication manifest plus synchronized manuscript table values; local article-side snapshot in `artifacts/he2_publication_freeze/` | high | validated against the frozen HE2 publication source | main reference table | current authoritative 28-day benchmark table for this revision snapshot; future better cells must replace it through the workflow manifest/overlay and validation gates |
| `tab:components_23_31` | main-text covariate-effects summary | verified representative rerun export frozen locally in `artifacts/representative_selected_model_2022_12_25/covariate_effects_summary.csv`; workflow export contract and tests remain in repo | high | reproducible from verified `2022-12-25 exAL-M-T1` rerun bundle and frozen locally | locked to representative `2022-12-25` selected-model run | keep synced to representative selected-model bundle |
| `tab:gamma_sigma_intervals1` | supplementary appendix `gamma` summary | verified representative rerun export frozen locally in `artifacts/representative_selected_model_2022_12_25/gamma_summary.csv`; workflow export contract and tests remain in repo | high | reproducible from verified `2022-12-25 exAL-M-T1` rerun bundle and frozen locally | locked to representative `2022-12-25` support role | keep as supplementary appendix support |
| `tab:gamma_sigma_intervals2` | supplementary appendix `sigma` summary | verified representative rerun export frozen locally in `artifacts/representative_selected_model_2022_12_25/sigma_summary.csv`; workflow export contract and tests remain in repo | high | reproducible from verified `2022-12-25 exAL-M-T1` rerun bundle and frozen locally | locked to representative `2022-12-25` support role | keep as supplementary appendix support |

### Notes on table confidence

1. Table exports are better documented than they first appeared.
   - The workflow repo has a formal post-stage artifact contract.
   - Export helpers and tests are already in place.
   - The missing piece is the exact run-level linkage for the current manuscript tables.

2. `tab:components_23_31` is now locked to the representative `2022-12-25` selected-model rerun.
   - The manuscript and local provenance bundle now use the verified `covariate_effects_summary.csv` export from that run.

3. The appendix `gamma` and `sigma` tables are now explicitly treated as supplementary representative-cutoff support.
   - They are frozen locally from the same verified `2022-12-25` rerun bundle.
   - They are no longer described as central forecast-validation evidence.

## Provenance classification for the next phase

### Group A: keep as cutoff-specific setup/support figures
These are now reproduced through the corrected `v2` per-cutoff family derived from the verified five-run `exAL-M-T1` bundles and the selected forecast/setup support bundle roots.
- `fig:sanlorenzo`
- `fig:covariates`
- `fig:retrospectives`
- `fig:ensembles`

### Group B: keep as current-model appendix support
- `fig:synth2`

### Group C: selected-run dependent and now locked to the representative selected-output authority
These are too tightly tied to one fitted output to leave ambiguous.
- `fig:synth1`
- `fig:dry_quantile`
- `fig:rainy_quantile`
- `fig:80_components`
- `tab:components_23_31`
- `tab:gamma_sigma_intervals1`
- `tab:gamma_sigma_intervals2`

### Group D: analysis-only selected-support diagnostics
These objects are produced from the same selected-output support but are intentionally not registered as manuscript figures.
- `artifacts/representative_selected_model_2022_12_25/authoritative_support/analysis_figures/component_evolution/`

## Locked provenance policy

The following policy is now adopted for the revised manuscript and should govern the regeneration work that follows.

### Section 4: forecast-validation evidence
- Section 4 remains the manuscript's five-cutoff forecast-validation evidence.
- Its benchmark values must continue to come from the validated five-cutoff `exdqlm_multivar_keep` / `exAL-M-T1` comparison workflow.
- Any rerun used to refresh those values must preserve the same configuration that produced the published CRPS table.

### Section 5: representative selected-model interpretation
- Section 5 will use one representative final cutoff of the selected specification.
- The representative cutoff is fixed as `2022-12-25`, because:
  - it is already the manuscript's current illustrative forecast origin,
  - a recent validated workflow run exists for it, and
  - that run already produces publication-facing cutoff-window synthesis artifacts.
- Therefore, the following Section 5 objects must be regenerated or re-verified from the `2022-12-25` `exdqlm_multivar_keep` run:
  - `fig:synth1`, through `artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/`
  - `tab:components_23_31`

### Appendix: selected-model diagnostics and support summaries
- Appendix figures and tables remain selected-model diagnostics and support summaries rather than forecast-validation evidence.
- This applies to:
  - `fig:dry_quantile`
  - `fig:rainy_quantile`
  - `fig:80_components`
  - `tab:gamma_sigma_intervals1`
  - `tab:gamma_sigma_intervals2`
- The captions and nearby text should continue to say so clearly.
- For the three selected-model diagnostic figures, the current article-side provenance anchor is now:
  - `artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/`
- The older historical-support figure source is no longer the manuscript authority for these three figures; `artifacts/historical_support_from_current_models/` remains only for the appendix univariate transfer-active reference synthesis.

## Recent selected-model workflow status

A recent validated family of selected-model runs exists under:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/`

For all five manuscript cutoffs, the corresponding `exdqlm_multivar_keep` runs:
- passed validation,
- passed deterministic-climate checks,
- use forecast precipitation after the cutoff,
- use forecast soil moisture after the cutoff,
- and keep the PCA/GDPC covariate in passthrough mode rather than forecasting it the same way.

These runs already provide:
- cutoff-window posterior-synthesis figures,
- cutoff-window quantile CSV exports,
- CRPS summary tables,
- and run-scoped manifests and input hashes.

Resolved gaps from this audit:
- the narrow `exAL-M-T1` replay path was completed with the required post-export fixes, so the representative selected-model outputs and posterior interpretation tables are now frozen locally in the revised article repo.
- the cutoff-dependent setup/support figures are now mirrored locally in the revised article repo through:
  - `artifacts/five_cutoff_setup_support/`
- the manuscript-facing `Figures/manuscript/` copies for `fig:sanlorenzo`, `fig:covariates`, `fig:retrospectives`, and `fig:ensembles` are now promoted from the representative `20221225_exal_m_t1` `v2` bundle through:
  - `MANUSCRIPT_ASSET_MANIFEST.json`
- the appendix univariate transfer-active reference synthesis and the historical-summary figures now share the current article-side provenance anchor:
  - `artifacts/historical_support_from_current_models/`
- In practice, this means:
  - `fig:synth1` is locked to the 2022-12-25 member of the five-cutoff synthesis family, while `tab:components_23_31`, `tab:gamma_sigma_intervals1`, and `tab:gamma_sigma_intervals2` remain locked to verified article-side representative selected-model bundles,
  - `fig:synth2` is preserved through the canonical `current_model_output_support` family,
  - `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components` remain selected-model interpretation diagnostics from the current representative selected-output authority,
  - and the four setup/support figures are preserved through the validated `v2` cutoff family, while older article-side support families have been removed.

## Exact Authority Handoff

The high-level provenance inventory in this file is paired with the run-level
artifact map and the workflow-side authority runbook:
- `docs/exal_m_t1_artifact_run_map.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/current_authority_refresh_runbook.md`

Use these files when:
- identifying the authoritative source run for a given cutoff,
- rerunning the selected specification associated with a published Table 1 CRPS value,
- verifying that the rerun reproduces the selected `exAL-M-T1` CRPS exactly,
- and checking whether the required figure and table artifacts were emitted.

## Current locked state

1. Section 4 remains the five-cutoff validation evidence.
   - `tab:benchmark_crps_models` is the current authoritative 28-day
     manuscript benchmark table.
   - `tab:benchmark_crps_models_nws_horizon` is the current authoritative
     common eight-day NWS-horizon companion table.
   - Future calibrated replacements are allowed, but only through the workflow
     manifest/overlay refresh path and the cross-repo validation gates.

2. Section 5 uses outputs from one representative final cutoff of the selected `exAL-M-T1` specification.
   - `fig:synth1`, sourced from `artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/`
   - `tab:components_23_31`

3. The appendix support tables remain tied to the same representative cutoff, but in a supplementary role.
   - `tab:gamma_sigma_intervals1`
   - `tab:gamma_sigma_intervals2`

4. The historical-summary objects remain workflow-linked descriptive support and are frozen locally in the article repo.
   - `fig:dry_quantile`
   - `fig:rainy_quantile`
   - `fig:80_components`

5. The corrections letter is synchronized to the same provenance split and current benchmark table values.

## Audit status summary

### Established in this pass
- the benchmark tables in the revised article are aligned with the frozen HE2
  publication manifest and treated as the current authoritative publication
  baseline,
- the representative selected-model outputs are refreshed from verified `exAL-M-T1` sources,
- the appendix support tables are explicitly demoted to a supplementary role,
- the historical-summary figures are workflow-linked, hash-verified, and frozen locally in the revised article repo, and
- the corrections letter is synchronized to the current article-side provenance split.

### Remaining optional work
- further aesthetic or publication-quality refreshes of historical-summary figures, if ever desired, should be treated as optional figure-improvement work rather than as unresolved provenance work.
