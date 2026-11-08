# Posterior Table Exports

This folder contains machine-readable posterior summary tables generated during post-processing.

Files:
- gamma_summary.csv: gamma by source x quantile with center=posterior median and 95% CI
- sigma_summary.csv: sigma by source x quantile with center=posterior median and 95% CI
- covariate_effects_summary.csv: transfer-function covariate effects with center=posterior mean and 95% CI at final time index
- crps_forecast_per_time*.csv: lead-wise forecast CRPS using quantile/check-loss approximation
- crps_forecast_summary*.csv: mean and dispersion CRPS summaries by forecast model

Optional LaTeX snippets:
- gamma_summary.tex
- sigma_summary.tex
- covariate_effects_summary.tex

CI string precision: 5 decimal places.
Table formats: csv
The numeric columns are the source of truth for downstream table generation.
