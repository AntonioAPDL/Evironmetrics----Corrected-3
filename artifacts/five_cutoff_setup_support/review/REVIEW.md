# exAL-M-T1 Setup/Support v2 Review

This review bundle contains the corrected cutoff-specific setup/input/support figures rendered from the CRPS-linked `exAL-M-T1` run roots and the authoritative forecats/histfix bundles.

## Cutoff summary
| Cutoff | Slug | Bundle class | Requested history | Retrospective available from | Forecast window | Flow display scale | Published CRPS |
|---|---|---|---|---|---|---|---:|
| 2021-01-23 | `20210123_exal_m_t1` | `histfix_long_history_bundle` | 1987-05-29 to 2021-01-23 | 1987-05-29 | 2020-12-26 to 2021-02-20 | log1p_cms | 0.1569 |
| 2021-11-12 | `20211112_exal_m_t1` | `histfix_long_history_bundle` | 1987-05-29 to 2021-11-12 | 1987-05-29 | 2021-10-15 to 2021-12-10 | log1p_cms | 0.0284 |
| 2021-12-21 | `20211221_exal_m_t1` | `histfix_long_history_bundle` | 1987-05-29 to 2021-12-21 | 1987-05-29 | 2021-11-23 to 2022-01-18 | log1p_cms | 0.2369 |
| 2022-05-11 | `20220511_exal_m_t1` | `histfix_long_history_bundle` | 1987-05-29 to 2022-05-11 | 1987-05-29 | 2022-04-13 to 2022-06-08 | log1p_cms | 0.0210 |
| 2022-12-25 | `20221225_exal_m_t1` | `histfix_long_history_bundle` | 1987-05-29 to 2022-12-25 | 1987-05-29 | 2022-11-27 to 2023-01-22 | log1p_cms | 0.4375 |

## Policy summary
| Cutoff | NWS policy | GloFAS policy | Notes |
|---|---|---|---|
| 2021-01-23 | nws_retro_v21 with nws_retro_v30 tail fill after natural coverage end | glofas_hist_v21_htessel_cons | histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff |
| 2021-11-12 | nws_retro_v21 with nws_retro_v30 tail fill after natural coverage end | glofas_hist_v31_lisflood_cons | histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff |
| 2021-12-21 | nws_retro_v21 with nws_retro_v30 tail fill after natural coverage end | glofas_hist_v31_lisflood_cons | histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff |
| 2022-05-11 | nws_retro_v21 with nws_retro_v30 tail fill after natural coverage end | glofas_hist_v31_lisflood_cons | histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff |
| 2022-12-25 | nws_retro_v21 with nws_retro_v30 tail fill after natural coverage end | glofas_hist_v31_lisflood_cons | histfix lineage should show nws_retro_v21 early support and nws_retro_v30 tail fill near cutoff |

## Coverage audit
| Cutoff | USGS full history | PPT full history | SOIL full history | GDPC full history | Retros full history | Retros available start |
|---|---|---|---|---|---|---|
| 2021-01-23 | True | True | True | True | True | 1987-05-29 |
| 2021-11-12 | True | True | True | True | True | 1987-05-29 |
| 2021-12-21 | True | True | True | True | True | 1987-05-29 |
| 2022-05-11 | True | True | True | True | True | 1987-05-29 |
| 2022-12-25 | True | True | True | True | True | 1987-05-29 |

