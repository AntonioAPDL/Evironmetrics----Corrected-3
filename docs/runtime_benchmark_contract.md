# HE-1 Runtime Benchmark Contract

This document records the revised article-side runtime contract for the HE-1
computational-cost response.

The source runtime tree is:

`/data/jaguir26/local/src/exdqlm__wt__shared_fitforecast_v2_1p0p0/validation/fitforecast_v2/runs/20260515_exdqlm_dqlm_dynamic_fitforecast_v2_orchestrated_3500202605200353075941`

The compact manifest is:

`artifacts/runtime_benchmark/runtime_manifest.json`

The manuscript-facing claim is intentionally limited to a representative
end-to-end wall-clock benchmark. The reliable total runtime columns in the shared
interface are `runtime_sec_total` and `runtime_sec`; the component timing columns
`runtime_sec_fit` and `runtime_sec_forecast` were reported as mostly missing in
the runtime note. Therefore the manuscript and response should not claim a
separate fitting, forecasting, or post-processing decomposition.

The interface table is recorded as 1620 rows by 127 columns, with all interface
rows completed. The companion manifest status counts preserve the full planned
orchestration state, with 54 completed and 18 pending planned run units. The
runtime statement therefore applies to the completed measured validation outputs,
not to every planned orchestration row.

The representative claim used in the manuscript is that the single-site workflow
required about two hours end-to-end on a production Linux server with 64 cores and
approximately 503 GiB RAM, with seven quantile-specific fits dispatched in
parallel. This is a hardware- and implementation-dependent benchmark, not a
universal guarantee.

