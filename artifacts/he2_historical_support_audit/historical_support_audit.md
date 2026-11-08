# HE2 Historical Support Audit

Date: 2026-05-07

## Purpose

This audit checks whether the published HE2 Bayesian model rows were fit with full historical support from `1987-05-29` up to each cutoff, or whether the effective shared-input support started later.

## Governing evidence

- Publication rows and run roots: `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- Within-cutoff shared-input congruence: `reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv`
- Effective common-date support per run: `inputs/shared/data_start_filter_summary.txt` in each selected run root
- Shared-input filtering logic: `R/unified/stages/stage_data_prep_shared.R:727-821`
- Multivariate fit merge logic: `R/environmetrics/10_data_inputs.R:203-208`

## Bottom line

- Full historical support from `1987-05-29` is preserved for all published Bayesian rows at cutoffs: `20211221`, `20220511`.
- Effective shared-input support starts later for all published Bayesian rows at cutoffs: `20210123` (`2018-02-08`), `20211112` (`2018-11-28`), `20221225` (`2020-01-10`).
- Because `retros`, `nws_forecast`, and `glofas_forecast` are hash-aligned within each cutoff, this applies across the whole Bayesian row family within that cutoff, not just `exAL-M-T1`.

## Cutoff-level verdict

| Cutoff | Effective common start | Full 1987 history? | Retros aligned across Bayesian rows? | NWS forecast aligned across Bayesian rows? | GloFAS forecast aligned across Bayesian rows? | USGS snapshot preserved across Bayesian rows? | Note |
|---|---|---|---|---|---|---|---|
| `20210123` | `2018-02-08` | No | True | True | True | False | short-window effective support despite data_start=1987-05-29 |
| `20211112` | `2018-11-28` | No | True | True | True | False | short-window effective support despite data_start=1987-05-29 |
| `20211221` | `1987-05-29` | Yes | True | True | True | False | full-history cutoff |
| `20220511` | `1987-05-29` | Yes | True | True | True | True | full-history cutoff |
| `20221225` | `2020-01-10` | No | True | True | True | True | short-window effective support despite data_start=1987-05-29 |

## Published Bayesian rows

### `20210123`

| Label | Family | CRPS | Effective common start | Full 1987 history? | Campaign |
|---|---|---:|---|---|---|
| `N-U-T1` | `ndlm_univar_keep` | `0.3520` | `2018-02-08` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T0` | `ndlm_main_drop` | `0.5311` | `2018-02-08` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T1` | `ndlm_main_keep` | `0.5275` | `2018-02-08` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `AL-U-T1` | `dqlm_univar_al` | `0.2449` | `2018-02-08` | No | `univar_featurecov_he2_rerun_20260422` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `0.3267` | `2018-02-08` | No | `featurecov_cf1_eps_sweep_20260416` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `0.1604` | `2018-02-08` | No | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-U-T1` | `exdqlm_univar` | `0.2229` | `2018-02-08` | No | `univar_featurecov_he2_rerun_20260422` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `0.3292` | `2018-02-08` | No | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `0.1569` | `2018-02-08` | No | `featurecov_cf1_eps_sweep_20260416` |

### `20211112`

| Label | Family | CRPS | Effective common start | Full 1987 history? | Campaign |
|---|---|---:|---|---|---|
| `N-U-T1` | `ndlm_univar_keep` | `0.2486` | `2018-11-28` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T0` | `ndlm_main_drop` | `0.0565` | `2018-11-28` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T1` | `ndlm_main_keep` | `0.0722` | `2018-11-28` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `AL-U-T1` | `dqlm_univar_al` | `0.1493` | `2018-11-28` | No | `univar_featurecov_he2_rerun_20260422` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `2.2435` | `2018-11-28` | No | `featurecov_cf1_eps_sweep_20260416` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `0.0391` | `2018-11-28` | No | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-U-T1` | `exdqlm_univar` | `0.1506` | `2018-11-28` | No | `univar_featurecov_he2_rerun_20260422` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `1.2744` | `2018-11-28` | No | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `0.0284` | `2018-11-28` | No | `featurecov_cf1_eps_sweep_20260416` |

### `20211221`

| Label | Family | CRPS | Effective common start | Full 1987 history? | Campaign |
|---|---|---:|---|---|---|
| `N-U-T1` | `ndlm_univar_keep` | `1.1768` | `1987-05-29` | Yes | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T0` | `ndlm_main_drop` | `1.5616` | `1987-05-29` | Yes | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T1` | `ndlm_main_keep` | `0.6071` | `1987-05-29` | Yes | `ndlm_featurecov_rerun_postfix_20260421` |
| `AL-U-T1` | `dqlm_univar_al` | `1.2283` | `1987-05-29` | Yes | `univar_featurecov_he2_rerun_20260422` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `0.6511` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `0.3482` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-U-T1` | `exdqlm_univar` | `1.2691` | `1987-05-29` | Yes | `univar_featurecov_he2_rerun_20260422` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `0.4720` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `0.2369` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |

### `20220511`

| Label | Family | CRPS | Effective common start | Full 1987 history? | Campaign |
|---|---|---:|---|---|---|
| `N-U-T1` | `ndlm_univar_keep` | `0.1572` | `1987-05-29` | Yes | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T0` | `ndlm_main_drop` | `0.0241` | `1987-05-29` | Yes | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T1` | `ndlm_main_keep` | `0.0416` | `1987-05-29` | Yes | `ndlm_featurecov_rerun_postfix_20260421` |
| `AL-U-T1` | `dqlm_univar_al` | `0.0551` | `1987-05-29` | Yes | `univar_featurecov_he2_rerun_20260422` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `0.0433` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `0.0214` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-U-T1` | `exdqlm_univar` | `0.0541` | `1987-05-29` | Yes | `univar_featurecov_he2_rerun_20260422` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `0.0694` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `0.0210` | `1987-05-29` | Yes | `featurecov_cf1_eps_sweep_20260416` |

### `20221225`

| Label | Family | CRPS | Effective common start | Full 1987 history? | Campaign |
|---|---|---:|---|---|---|
| `N-U-T1` | `ndlm_univar_keep` | `2.1451` | `2020-01-10` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T0` | `ndlm_main_drop` | `2.3485` | `2020-01-10` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `N-M-T1` | `ndlm_main_keep` | `0.5363` | `2020-01-10` | No | `ndlm_featurecov_rerun_postfix_20260421` |
| `AL-U-T1` | `dqlm_univar_al` | `1.1038` | `2020-01-10` | No | `univar_featurecov_he2_rerun_20260422` |
| `AL-M-T0` | `dqlm_multivar_al_drop` | `2.2601` | `2020-01-10` | No | `featurecov_cf1_eps_sweep_20260416` |
| `AL-M-T1` | `dqlm_multivar_al_keep` | `0.6186` | `2020-01-10` | No | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-U-T1` | `exdqlm_univar` | `1.1189` | `2020-01-10` | No | `univar_featurecov_he2_rerun_20260422` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `2.3365` | `2020-01-10` | No | `featurecov_cf1_eps_sweep_20260416` |
| `exAL-M-T1` | `exdqlm_multivar_keep` | `0.4375` | `2020-01-10` | No | `exalm_t1_discount_grid_exact_20260424:set09_override` |

## Interpretation

The shared-input prep stage date-filters all core inputs from `dates.data_start` forward, then intersects the core series (`retros`, `nws_forecast`, `glofas_forecast`) to form the effective common-date support. That logic is implemented in `R/unified/stages/stage_data_prep_shared.R:727-821`.

For multivariate environmetrics fits, the response/history matrix is then built by reading `RETROS_PATH` and merging it with the covariate history (`R/environmetrics/10_data_inputs.R:203-208`). So if `retros.csv` starts late, the fitted multivariate history also starts late, even when full-history USGS and covariate files exist separately.

## Family-level input semantics

- Multivariate environmetrics fits (`AL-M-*`, `exAL-M-*`) build the historical response matrix by reading `RETROS_PATH` and merging it with covariate history (`R/environmetrics/10_data_inputs.R:203-208`).
- Univariate exAL/AL legacy-bridge fits read the shared `retros.csv` and construct the target history from that file as well (`OptimalModelSLexAL.r:1029-1039`).
- NDLM main and NDLM univariate families both load historical target and retrospective source context from shared `retros.csv` (`R/unified/families/ndlm_main/01_inputs.R:68-123`, `R/unified/families/ndlm_univar/01_inputs.R:41-79`).

This means the cutoff-level retrospective support issue is not isolated to `exAL-M-T1`; it propagates across the published Bayesian panel within each affected cutoff.

## Serious implication

If the intended scientific contract was that **all published Bayesian model rows should be fit using all available historical support from `1987-05-29` to cutoff**, then the published rows at cutoffs `2021-01-23`, `2021-11-12`, and `2022-12-25` violate that intended contract across the full Bayesian panel.

## Scope note

This audit covers the 45 Bayesian publication rows in the HE2 table. The raw forecast reference rows (`RAW-GLOFAS`, `RAW-NWS`) are not fit-model rows and are therefore out of scope for this historical-support fit audit.
