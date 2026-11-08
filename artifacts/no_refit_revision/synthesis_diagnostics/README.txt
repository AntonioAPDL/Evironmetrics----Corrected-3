Optional own-fit/isotonic/final synthesis diagnostics from frozen predictions.
Own-fit anchors are empirical predictive quantiles, not latent state locations.
Final HE4 targets retain their existing values; other final targets use declared type8.
Anchor crossings describe separate quantile-fit curves, not joint posterior sample paths.
No pre-synthesis CRPS, clipping, fitting, draw generation or synthesis call occurs.
Portable replay uses compact anchors/observations; the original cubes are required only for first extraction.
From this directory, run into a fresh destination:
  Rscript --vanilla reproduce/build_no_refit_synthesis_diagnostics.R --inputs-dir inputs --output-dir /tmp/synthesis_replay
Read-only checksums:
  Rscript --vanilla reproduce/build_no_refit_synthesis_diagnostics.R --output-dir . --check
