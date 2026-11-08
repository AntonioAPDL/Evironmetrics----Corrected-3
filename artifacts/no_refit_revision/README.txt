Additive verification from existing selected predictive outputs

Start with docs/no_refit_revision.txt for scope, estimands, exact replay commands,
verified findings and remaining inference-dependent work.

inputs/: immutable compact prediction matrices, observations, existing target
quantiles and the source/checksum registry. No fitted state objects are required.
results/: complete unrounded case registries, scores, targeted-quantile hits and
losses, predictive intervals, origin/horizon and pooled summaries, source-lead
diagnostics, support audit, original-score parity and the reliability plot.
reproduce/: exact R builder, helper and configuration used by the derivation.
verification/: executed-source hashes, counts, tolerances and session details.
reporting/: exact configured/effective settings, feature dictionary, source-string
preserved summaries, estimands, extraction proof and portable metadata replay.
inference_scope/: historical conditional derivation, deterministic identity
checks, independent diagnostic review and the optional precision gate ledger.
synthesis_diagnostics/: compact own-anchor/isotonic/final-quantile comparison
and separate extraction and portable-replay provenance, where available.
manifest.json: release hashes for this bundle, its new five TeX table files,
reliability figure and dedicated article validation/generation entrypoints.

The primary new score is exact empirical-distribution CRPS of the saved
representation. The original quantile-grid scores remain distinct and unchanged.
The iid-adjusted score is qualified by representation type and never substituted
for an inapplicable deterministic score. No adjusted skill score is published.
No fitting, baseline training, predictive resampling or new posterior draws are
part of this release. Conditional omissions and later inference are recorded
explicitly rather than presented as completed empirical comparisons.
