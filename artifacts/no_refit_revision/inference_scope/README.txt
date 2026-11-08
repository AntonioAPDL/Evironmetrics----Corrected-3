Inference scope and optional precision audit

This bundle records the mathematical scope of the manuscript's historical
conditional sampling displays and the interpretation of its reported VB output.
The existing article results remain unchanged.

scope_audit.json maps the displayed algorithms and inference objects to their
supported scope. historical_conditional_derivation.txt derives the historical
augmentation and scale kernels and explains the conditional state path draw.
The deterministic verification script checks these identities against direct
density/Gaussian calculations, using fixed synthetic inputs and no random draws.

No matching full-model MCMC result is supplied. Parameter intervals describe
approximate variational marginals. Optimizer traces and draws from fitted
Gaussian/Laplace factors do not constitute a Markov chain comparison.

precision_gate_ledger.json records the optional source-precision decision:
OPTIONAL_SKIPPED_SOURCE_CONTRACT. Source/phase correspondence is not sufficiently
established for numerical precision-share interpretation. The array metadata
checks do not resolve that correspondence. No precision shares are published,
and the optional skip does not block the working-likelihood explanation or the
descriptive raw-product diagnostics.

saved_output_independent_review.json records an independent read-only review of
the distribution-score and calibration outputs. It binds the 14 reviewed CSV
files, direct pairwise raw-ensemble score checks, case/skill summaries, quantile
events, interval partitions, and descriptive source summaries. The inherited
log-scale event definitions also apply after inverse transformation; this keeps
the declared forecast event unchanged at floating-point ties.

source_provenance.json binds the inspected source versions and surviving compact
CSV evidence. External absolute paths identify evidence; the standalone
conditional identity checks require only the script and NumPy.

Replay:
  python3 -B artifacts/no_refit_revision/inference_scope/verify_conditional_identities.py

The replay prints its report and writes no files unless --output is supplied.
SOURCE_MANIFEST.json binds every other file in this directory, plus the companion
docs/no_refit_inference_scope.txt. It does not hash itself.
