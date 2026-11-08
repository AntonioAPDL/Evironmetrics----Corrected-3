# HE3 ablation audit

This audit checks that each launched HE3 ablation row is a structural simplification
of the cutoff-specific winning full model rather than a different data/configuration run.

## Launch-row audit

| Cutoff | Variant | Config inheritance | Runtime input hashes | Target model id | Overall | Mean CRPS | Delta vs full | Delta vs HE2 drop | Notes |
|---|---|---|---|---|---|---:|---:|---:|---|
| 01/23/2021 | `noH1` | `True` | `True` | `True` | `True` | 1.278609 | 1.138900 |  | ok |
| 01/23/2021 | `noH2` | `True` | `True` | `True` | `True` | 0.726896 | 0.587187 |  | ok |
| 01/23/2021 | `noH3` | `True` | `True` | `True` | `True` | 1.082814 | 0.943105 |  | ok |
| 01/23/2021 | `noTF` | `True` | `True` | `True` | `True` | 1.736096 | 1.596387 | 0.979275 | ok |
| 01/23/2021 | `noTrend` | `True` | `True` | `True` | `True` | 1.051592 | 0.911883 |  | ok |
| 11/12/2021 | `noH1` | `True` | `True` | `True` | `True` | 1.601420 | 1.554184 |  | ok |
| 11/12/2021 | `noH2` | `True` | `True` | `True` | `True` | 1.046992 | 0.999756 |  | ok |
| 11/12/2021 | `noH3` | `True` | `True` | `True` | `True` | 1.035625 | 0.988388 |  | ok |
| 11/12/2021 | `noTF` | `True` | `True` | `True` | `True` | 1.714090 | 1.666854 | -0.007263 | ok |
| 11/12/2021 | `noTrend` | `True` | `True` | `True` | `True` | 0.723427 | 0.676191 |  | ok |
| 12/21/2021 | `noH1` | `True` | `True` | `True` | `True` | 2.830173 | 2.569726 |  | ok |
| 12/21/2021 | `noH2` | `True` | `True` | `True` | `True` | 2.965129 | 2.704682 |  | ok |
| 12/21/2021 | `noH3` | `True` | `True` | `True` | `True` | 2.583328 | 2.322882 |  | ok |
| 12/21/2021 | `noTF` | `True` | `True` | `True` | `True` | 2.328629 | 2.068182 | 1.351010 | ok |
| 12/21/2021 | `noTrend` | `True` | `True` | `True` | `True` | 2.517483 | 2.257036 |  | ok |
| 05/11/2022 | `noH1` | `True` | `True` | `True` | `True` | 1.099563 | 1.076835 |  | ok |
| 05/11/2022 | `noH2` | `True` | `True` | `True` | `True` | 0.911929 | 0.889201 |  | ok |
| 05/11/2022 | `noH3` | `True` | `True` | `True` | `True` | 0.686417 | 0.663689 |  | ok |
| 05/11/2022 | `noTF` | `True` | `True` | `True` | `True` | 2.477030 | 2.454302 | 1.456165 | ok |
| 05/11/2022 | `noTrend` | `True` | `True` | `True` | `True` | 0.532566 | 0.509838 |  | ok |
| 12/25/2022 | `noH1` | `True` | `True` | `True` | `True` | 4.458873 | 3.920818 |  | ok |
| 12/25/2022 | `noH2` | `True` | `True` | `True` | `True` | 4.647085 | 4.109030 |  | ok |
| 12/25/2022 | `noH3` | `True` | `True` | `True` | `True` | 4.438785 | 3.900730 |  | ok |
| 12/25/2022 | `noTF` | `True` | `True` | `True` | `True` | 2.172797 | 1.634741 | 0.961478 | ok |
| 12/25/2022 | `noTrend` | `True` | `True` | `True` | `True` | 4.058807 | 3.520751 |  | ok |

## Lead-bucket diagnostics

The table below summarizes mean lead-wise CRPS over four lead buckets.
This helps distinguish a true performance degradation from a malformed run.

### Cutoff 01/23/2021

| Variant | 01-07 | 08-14 | 15-21 | 22-28 |
|---|---:|---:|---:|---:|
| `full` | 0.245 | 0.077 | 0.121 | 0.116 |
| `noH1` | 1.730 | 1.294 | 1.079 | 1.012 |
| `noH2` | 1.177 | 0.707 | 0.540 | 0.483 |
| `noH3` | 1.588 | 1.165 | 0.829 | 0.749 |
| `noTF` | 1.816 | 1.714 | 1.719 | 1.695 |
| `noTrend` | 1.548 | 1.133 | 0.801 | 0.724 |

### Cutoff 11/12/2021

| Variant | 01-07 | 08-14 | 15-21 | 22-28 |
|---|---:|---:|---:|---:|
| `full` | 0.059 | 0.046 | 0.038 | 0.046 |
| `noH1` | 1.700 | 1.629 | 1.561 | 1.516 |
| `noH2` | 1.150 | 1.073 | 1.005 | 0.960 |
| `noH3` | 1.098 | 1.033 | 1.003 | 1.008 |
| `noTF` | 1.671 | 1.736 | 1.705 | 1.745 |
| `noTrend` | 0.781 | 0.716 | 0.693 | 0.704 |

### Cutoff 12/21/2021

| Variant | 01-07 | 08-14 | 15-21 | 22-28 |
|---|---:|---:|---:|---:|
| `full` | 0.621 | 0.222 | 0.074 | 0.125 |
| `noH1` | 3.719 | 3.118 | 2.443 | 2.041 |
| `noH2` | 3.818 | 3.258 | 2.591 | 2.193 |
| `noH3` | 3.470 | 2.869 | 2.197 | 1.797 |
| `noTF` | 2.184 | 2.286 | 2.403 | 2.442 |
| `noTrend` | 3.402 | 2.804 | 2.133 | 1.731 |

### Cutoff 05/11/2022

| Variant | 01-07 | 08-14 | 15-21 | 22-28 |
|---|---:|---:|---:|---:|
| `full` | 0.027 | 0.020 | 0.023 | 0.021 |
| `noH1` | 1.146 | 1.107 | 1.079 | 1.067 |
| `noH2` | 1.005 | 0.927 | 0.878 | 0.838 |
| `noH3` | 0.793 | 0.688 | 0.646 | 0.619 |
| `noTF` | 2.460 | 2.439 | 2.525 | 2.484 |
| `noTrend` | 0.660 | 0.527 | 0.486 | 0.457 |

### Cutoff 12/25/2022

| Variant | 01-07 | 08-14 | 15-21 | 22-28 |
|---|---:|---:|---:|---:|
| `full` | 0.660 | 0.272 | 0.816 | 0.404 |
| `noH1` | 3.764 | 4.424 | 5.353 | 4.295 |
| `noH2` | 3.898 | 4.589 | 5.558 | 4.544 |
| `noH3` | 3.724 | 4.388 | 5.336 | 4.308 |
| `noTF` | 2.316 | 2.154 | 2.041 | 2.181 |
| `noTrend` | 3.383 | 3.989 | 4.945 | 3.919 |

