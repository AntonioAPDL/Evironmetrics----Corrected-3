# Authoritative Selected-Model Support

This bundle contains compact posterior support artifacts and rendered figures for the representative `2022-12-25 exAL-M-T1` selected model. These figures are sourced from the same selected-output authority as the synthesis figure. Figure A1 is article-labeled as the long-cycle seasonal component, with period approximately 6.81 years, or about 82 months, and is rendered from raw state component 6 only with dry/wet period overlays. The `analysis_figures/component_evolution/` subfolder is an analysis-only component gallery rendered from the same support CSVs; it is checksummed here but intentionally not registered as a manuscript figure family. It also includes samplewise component-6-plus-trend and component-6-minus-trend diagnostics when the support summary provides those contracts.

The support bundle is tied to the same current `2022-12-25` selected `exAL-M-T1` output authority used by the representative synthesis figure.

The current compact support root rebuilds the fitted quantile-dynamics summaries and component summaries from retained selected-model `.RData` objects; the previous compact support root is used only to recover dates and observed USGS values for plotting.

Large compact support CSV/RDS files are intentionally not persisted in this Overleaf-facing article repository. The manifest records their external runtime source paths and hashes; the refresh script stages those files in a temporary directory only while rendering figures.

- run id: `multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep`
- cutoff: `2022-12-25`
- runtime output root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623/runs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep/post/outputs/multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep`

Refresh entrypoint:
- `scripts/refresh_authoritative_selected_model_support_figures.py`
