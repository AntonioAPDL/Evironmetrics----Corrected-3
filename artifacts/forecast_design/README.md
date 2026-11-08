# HE-6 Forecast Design Artifact

This directory contains a compact machine-readable contract for the
rolling-origin out-of-sample forecast validation described in the revised
article and corrections response.

The manifest records that post-cutoff USGS observations are held out for
verification only, that forecast products are restricted to the latest products
issued at or before each cutoff, and that the workflow-facing `PCA` covariate is
the canonical GDPC1 compatibility alias rather than an operational forecast
product.

Authoritative manifest:

- `forecast_design_manifest.json`
