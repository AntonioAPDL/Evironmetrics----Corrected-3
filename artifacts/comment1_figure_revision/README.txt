Comment 1: completed figure/style and presentation-lineage revision
November 7, 2026, America/Los_Angeles

Status
All seven requested figure panels have been rendered, visually inspected and
promoted to the isolated article. PNG and vector PDF pairs are available. The
original selected research run directories were read only. No model was fitted,
no research process was changed, and no numerical source/cache/CSV was rewritten.

Changes
The focus publication renderer now supplies combined keys reproducing the actual
line patterns and markers. History uses filled circles/solid lines; verification
uses open circles/dashed lines. GloFAS and NWM retrospectives use different dash
patterns and square/triangle markers; the ensemble sources use solid/dotted lines.
Full-opacity keys remain readable while ensemble members stay faint in the plot.
The mean is named as the predictive mean on the plotted log1p discharge scale.
The interval is named as a pointwise central 95% predictive interval and still
uses exact complete-cache 0.025/0.975 type-8 quantiles. The mean still uses the
complete predictive matrices. The direct renderer emits an explicit numerical
contract CSV showing precisely the columns supplied to the plot.

All six synthesis panels retain ten deterministic saved predictive sample paths.
These paths have an explicit key; they are not identified as seven quantile lines.
The render_sample_paths flag and sample_path_cap now actually control this focus
renderer, with tests confirming disabled paths/cap changes leave summaries intact.
The focus renderer requires model_mean and refuses to label a median as a mean.

The vertical boundary consistently marks forecast origin T; the first forecast
is T+1. No decorative forecast shading is added. Common synthesis limits 0..6.5
are retained across all five origins and the December univariate reference.
Production output is 6.23 inches wide. Legend/axis text is 8.5 pt, subtitle 8.5 pt,
caption 8 pt; plot annotations are about 8.2 pt. All five multivariate
PDF panels, the univariate reference and context were inspected in color;
representative PDF proofs were also rasterized in grayscale for inspection.
Final PDF review identified a clipped January date label from an automatic tick
beyond the saved window. Explicit interior date ticks corrected it; all six
synthesis runs were rerendered and every panel inspected with the new labels. Both providers and roles
remain distinguishable in grayscale. No sample-path simplification was needed.

Guide-level provenance
Preexisting guide values differ between context and synthesis displays. They are
preserved, labeled generically Lower/Upper flow reference and recorded explicitly:
  synthesis: log1p levels 5.20948615 / 6.06378521 (about 182/429 m3/s);
  context: original rating 40.0 equivalents 7402.38/14895.73 cfs
           (209.612/421.800 m3/s).
These labels do not assert identical flood thresholds across the two displays.

Bounded rendering and promotion
scripts/render_comment1_publication_figures.py uses the frozen readiness snapshot
as the run-selection authority. Before any output/copy/render it verifies all
seven numerical inputs for each selected run against captured snapshot hashes.
It copies compact CSVs, two predictive RDS matrices per selected run and adapters
to a separate output root and rebases mutable manifests there. It refuses an
existing output root or a root inside any authoritative run.
The explicit context configuration is exal_m_t1_setup_support_by_cutoff_v2_20260516.json;
only the December slug is requested. The context renderer now accepts explicit
existing factor/metadata inputs, so isolated rendering need not construct or
write an absent local data tree. A PDF is exported alongside the context PNG.
The final render records 67 input files / 21,639,583 bytes and confirms identical
source/copy hashes afterward. All selected summary means/intervals are present.

Initial full rendering command from workflow root:
  python3 -B scripts/render_comment1_publication_figures.py \
    --snapshot docs/environmetrics_comment1_plan_20261107/readiness/baseline_snapshot.json \
    --output-root /tmp/NEW_comment1_render
The output root must be new. This creates proof assets and never writes article.

scripts/promote_comment1_figure_assets.py validates snapshot digest, the exact
planned five multivariate plus December univariate selection, current frozen IDs,
all available snapshot input hashes, source hashes and all twelve corresponding
article quantile/sample CSVs before promotion. It promotes the seven manuscript
panels plus paired PDFs and consistent primary/overlay companions from the same
six renders. It does not render the other four univariate origins. It updates the
exact article source artifact copies, style/provenance manifests and SHA lists.

Minimal initial promotion syntax (requires no existing presentation registry):
  python3 -B scripts/promote_comment1_figure_assets.py \
    --render-root /tmp/environmetrics_comment1_implementation_20261107/figure_final \
    --article-root /tmp/environmetrics_comment1_implementation_20261107/workflow/Evironmetrics---REVISED-DOC-Corrected-2
The complete final promotion argument vector is recorded under promotion_command
in figure_delivery/render_manifest.json. The helper accepts --additional-provenance and repeated
--additional-target for the inspected component-title revision. The final promotion included that revision's
six inspected assets/metadata files and three durable input guards, producing
one final registry after the bounded-date-axis rerender. Existing registries deliberately
cannot be silently replaced by this initial-promotion command.

Durable wiring
A presentation-only registry is necessary because existing refresh scripts copy
old PNGs from untouched runtime outputs. Article scripts/comment1_figure_revision.py
verifies the six original frozen selected IDs, 67 durable source-input hashes,
twelve local numerical CSV hashes, and every reviewed archive hash before its
first copy. It restores 105 allowed image/style/metadata files, including the root
agent's six component-title files. Archives occupy approximately 13 MiB and contain
no fit objects. A changed/missing numerical source, changed selection or corrupted
archive fails closed. Five relevant refresh entrypoints preverify and reapply:
cutoff_synthesis_families, setup_support_by_cutoff_v2,
current_model_output_support_figures, authoritative_selected_model_support_figures,
and all_generated_assets. Cutoff reapplication precedes compatibility mirroring.

Check current registry:
  python3 -B Evironmetrics---REVISED-DOC-Corrected-2/scripts/comment1_figure_revision.py --check
The registry and display/reference provenance are in article
artifacts/comment1_figure_revision. Original stable source paths and run identities
are retained. Exact six code files used to render the final images are archived
under renderer_sources. The final render executed the complete guarded code,
including the no-median-fallback check and bounded axis labels. All six numerical
summary contracts are byte-identical to the earlier full-path proofs.

Verification
R publication tests: 48 passed, 0 failed, 0 warnings. Includes complete-cache mean and
0.025/0.975 endpoint checks, true sample control, origin dates and unchanged
summaries under display changes. The former hardcoded style-version assertion
now checks the actual selected style and manifest version.
New workflow guard tests: 2 passed (changed numeric source and changed snapshot
content rejected before output/article writes).
New article registry tests: 4 passed (byte-identical restoration without changing
numeric input; changed input, changed selected ID/path escape, or corrupted
archive rejected before any presentation copy).
Article figure-path validator: 13 includes resolve to uppercase canonical Figures.
Dedicated authoritative output lineage validator:passed.
Actual six-run frozen input preflight:passed; existing-output guard stopped the
check before rendering/copying.
The root agent runs final integrated freeze/readiness/PDF checks separately.

Key review outputs
figure_delivery/render_manifest.json
figure_delivery/article_assets/Figures/...
figure_delivery/december_grayscale_proof.png
figure_delivery/context_grayscale_proof.png
figure_tests_final.log
figure_lineage_checks_final/AUTHORITATIVE_OUTPUT_LINEAGE_VALIDATION.md
