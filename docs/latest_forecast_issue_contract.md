# Latest Forecast Issue Contract

This note documents the manuscript-facing HE-7 forecast-issuance protocol.

At each rolling-origin cutoff, the revised article uses the latest forecast
products available at that origin. GloFAS contributes the daily issue associated
with the cutoff. NWS/NWM contributes the most recent available issuance for each
target time and ensemble member, after which the retained hourly values are
aggregated to daily resolution.

Older forecast issuances are not averaged into the publication forecast
matrices. The historical `weighted_daily` file names that remain in some
workflow manifests are compatibility aliases for latest-issue member matrices.

Machine-readable companion:

- `artifacts/latest_forecast_issue/latest_forecast_issue_manifest.json`

The workflow repository contains the executable validator and runtime alias
audit helper for this contract. The latest local alias audit checked the five
publication cutoffs for both NWS and GloFAS and found that the legacy
`*_weighted_daily.csv` aliases are byte-identical to the corresponding
member-level forecast matrices.
