# HE-1 Runtime Benchmark Artifact

This directory stores the compact article-side runtime benchmark manifest used for
the HE-1 computational-cost response.

The full runtime worktree is not copied into the article repository. The compact
manifest records the source path, row counts, runtime-column interpretation,
planned-run status counts, and manuscript-safe claims policy. The manuscript and
corrections response should report only the end-to-end wall-clock timing from
`runtime_sec_total` / `runtime_sec`; the available metadata do not support a
separate fitting/forecasting/post-processing decomposition.

