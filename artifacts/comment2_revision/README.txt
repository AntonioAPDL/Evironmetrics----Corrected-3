Major comment 2: external comparisons and saved-fit evidence

The new external baselines are additive. All original model scores, selected run
identities, numerical tables and reviewed figures remain unchanged. The current
six-section manuscript organization is retained.

external_baselines/ contains the sealed output of the baseline builder. It includes
1,440 unchanged existing per-time score rows, 420 new baseline rows, 140 per-lead
EMOS parameter sets and 560 optimizer-start diagnostics. Original-date scores,
pooled horizon scores and climatology-relative skill are in per_time.csv,
by_origin_horizon.csv and aggregate.csv. Predictions are the exact 2,000-point grids;
parameters and compact input features make them reproducible.

Methods
CLIM-SEASONAL: empirical pre-origin USGS history from 1987-05-29, using a fixed
+/-15-slot calendar window in reference leap year 2000. February 29 has its own
slot. Type 1 empirical inverse CDF evaluated at k/2001, k=1,...,2000.
PERSISTENCE: point mass at the origin's USGS observation, repeated across leads.
Its reported CRPS equals absolute error on log1p(cms).
EMOS-GLOFAS: normal law on transformed discharge, truncated below zero, with
mu=a+b*mean(log1p members), sigma²=c+d*sample_variance(log1p members),c>0,b>=0,d>=0.
Each lead uses a predeclared 365-day issued-forecast training rule and only
matured observations available by that origin, within the applicable operational
version family. At least 100 cases are required. Actual counts are 143--364.
Four deterministic L-BFGS-B starts minimize analytic truncated-normal CRPS using
training data alone. The lowest converged training objective is selected. All 140
fits and 560 starts converge; numerical bounds are inactive. Training-based
coordinate scaling and independent projected-gradient checks are recorded.

Reporting evaluates all added distributions with the unchanged current numerical
quantile CRPS convention. Analytic CRPS is the fitting objective/verification aid,
not a replacement for existing reported scores. CRPSS is1-aggregate(method score)/
aggregate(seasonal-climatology score), over matching cases/horizons. No averaging
of daily or origin-specific skill ratios is used for pooled skill.

Interpretation
The selected quantile configuration has lower pooled CRPS than the three added
references over both horizons; its mean CRPS reductions versus climatology are
68.6% and59.0%. EMOS has lower CRPS in May 2022 at both horizons, and raw NWS
remains competitive over its eight-day horizon. These five origins establish
case-specific comparisons, not universal dominance or evidence of superiority
under identical information inputs: EMOS uses GloFAS alone.

component_diagnostics/ contains the saved-text audit of 70 existing runs and 400
fits:16 criterion-supported stops, 314 iteration-budget-limited fits, 70 fits
without sufficient recorded joint-criterion evidence. Good reference and poor
reduced configurations share budget-limited status. These findings qualify
component-removal interpretation rather than replacing any numerical result.
A convergence label is not proof of predictive validity; a budget limit is not
proof that a reported forecast is unusable. Terminal guards, frozen updates and
sampling completion are separate fields. Reporting-only R-expression comparison
confirms that the future status-message repair changes no numerical expression.

Checks and regeneration from the article directory
  python3 -B scripts/comment2_revision.py --check
  python3 -B scripts/comment2_revision.py
The first command writes nothing and verifies frozen hashes, protected original
assets, imported scores, score/skill arithmetic, target alignment, training
eligibility, distribution summaries, exact diagnostic identities and table text.
The second command regenerates only the three additional TeX tables after the
same checks. The main asset manifest and refresh entrypoint retain this wiring.

Portable baseline replay from the article directory
  Rscript --vanilla artifacts/comment2_revision/reproduce/scripts/build_comment2_external_baselines.R \
    --input-bundle artifacts/comment2_revision/external_baselines/inputs \
    --output-root /tmp/NEW_comment2_baseline_replay
Choose a new output directory. It requires R packages jsonlite, digest and
scoringRules; exact executed versions are in external_baselines/run_manifest.json.
Curated features, pre-origin USGS history, verification and immutable old score
rows are sufficient; the original raw-data paths are not accessed. Archived
source/config are in reproduce/. Their hashes agree with the sealed executed run.
All numerical output files and predictive grids reproduce byte for byte.

Saved-diagnostic audit requires the current companion runtime text diagnostics.
The archived command, source hashes, parsed terminal evidence and observed limits
are in component_diagnostics/. Large fit RData are not needed or read. These runtime
sources are distinct from the portable baseline replay inputs.

verification/ records execution, independent score/formula/date checks, raw-source
hash checks, replay agreement and tests. manifest.json covers all bundled files
and protected original article assets. The full refined plan, departures,
commands, clause checklist, PDF review and completion record are in the companion
workflow repository at docs/environmetrics_comment2_revision_20261107/.
