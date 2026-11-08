# Five-Cutoff CRPS Validation Sources

This artifact bundle freezes the five current publication-authority `exAL-M-T1` run roots used by the revised article benchmark table refresh.

Refresh script:
- `scripts/refresh_exal_m_t1_generated_assets.py`

For each cutoff, the local freeze contains:
- `summary.json`
- `compare_report.json`
- `crps_forecast_summary.csv`

- `crps_forecast_per_time.csv`

These files are copied from the current HE2 publication freeze. Some cutoffs may remain on the original canonical-grid roots, while promoted cutoffs point to clean replay roots.
