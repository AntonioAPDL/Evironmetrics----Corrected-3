# HE2 Bayesian Publication Manifest

This report freezes the **current manuscript-facing HE2 Bayesian table** at the run level for all `9 x 5 = 45` cells.

Headline checks:
- published Bayesian HE2 cells documented: `45`
- cutoffs documented: `5`
- canonical-bundle promoted cells: `45`
- remaining transition cells: `0`
- required shared-input artifacts checked within each cutoff: `10`
- fit covariate contract observed: `PPT|SOIL|PCA`
- deterministic-climate enabled flags observed: `True`
- covariate-features enabled flags observed: `True`
- lag orders observed: `1|2|3`
- square terms observed: `True`
- interaction term observed: `True`
- likelihood modes observed: `al, exal, normal`
- full within-cutoff shared-input alignment checks passing: `50 / 50`

Special publication update:
- all nine benchmark families now resolve to canonical-bundle promoted roots.
- Final gate: the full 9-model manuscript benchmark table is ready for the current publication snapshot.

## Canonical-Bundle Promoted Rows

| Cutoff | Label | Mean CRPS | Run ID |
|---|---|---|---|
| 01/23/2021 | N-U-T1 | 0.3359 | multimodel_20210123_v8_he2pubgdpc1r1_ndlm_univar_keep |
| 01/23/2021 | N-M-T0 | 1.8433 | multimodel_20210123_v8_he2tbl1fix20260612_ndlm_main_drop |
| 01/23/2021 | N-M-T1 | 3.2149 | multimodel_20210123_v8_he2pubgdpc1r1_ndlm_main_keep |
| 01/23/2021 | AL-U-T1 | 0.2311 | multimodel_20210123_v8_he2pubgdpc1r1_dqlm_univar_al |
| 01/23/2021 | AL-M-T0 | 0.4680 | multimodel_20210123_v8_he2pubgdpc1r1_dqlm_multivar_al_drop |
| 01/23/2021 | AL-M-T1 | 0.1459 | multimodel_20210123_v8_he2grid_c04_eps365_dqlm_multivar_al_keep |
| 01/23/2021 | exAL-U-T1 | 0.2162 | multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_univar |
| 01/23/2021 | exAL-M-T0 | 0.7568 | multimodel_20210123_v8_he2tbl1fix20260612_exdqlm_multivar_drop |
| 01/23/2021 | exAL-M-T1 | 0.1397 | multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep |
| 11/12/2021 | N-U-T1 | 0.1706 | multimodel_20211112_v8_he2pubgdpc1r1_ndlm_univar_keep |
| 11/12/2021 | N-M-T0 | 0.3802 | multimodel_20211112_v8_he2pubgdpc1r1_ndlm_main_drop |
| 11/12/2021 | N-M-T1 | 0.8910 | multimodel_20211112_v8_he2pubgdpc1r1_ndlm_main_keep |
| 11/12/2021 | AL-U-T1 | 0.0779 | multimodel_20211112_v8_he2pubgdpc1r1_dqlm_univar_al |
| 11/12/2021 | AL-M-T0 | 0.1999 | multimodel_20211112_v8_he2pubgdpc1r1_dqlm_multivar_al_drop |
| 11/12/2021 | AL-M-T1 | 0.0555 | multimodel_20211112_v8_he2grid_c04_eps365_dqlm_multivar_al_keep |
| 11/12/2021 | exAL-U-T1 | 0.1019 | multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_univar |
| 11/12/2021 | exAL-M-T0 | 1.7214 | multimodel_20211112_v8_he2tbl1fix20260612_exdqlm_multivar_drop |
| 11/12/2021 | exAL-M-T1 | 0.0472 | multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep |
| 12/21/2021 | N-U-T1 | 1.1934 | multimodel_20211221_v8_he2tbl1fix20260612_ndlm_univar_keep |
| 12/21/2021 | N-M-T0 | 0.6596 | multimodel_20211221_v8_he2pubgdpc1r1_ndlm_main_drop |
| 12/21/2021 | N-M-T1 | 3.0436 | multimodel_20211221_v8_he2tbl1fix20260612_ndlm_main_keep |
| 12/21/2021 | AL-U-T1 | 0.8705 | multimodel_20211221_v8_he2pubgdpc1r1_dqlm_univar_al |
| 12/21/2021 | AL-M-T0 | 0.5867 | multimodel_20211221_v8_he2pubgdpc1r1_dqlm_multivar_al_drop |
| 12/21/2021 | AL-M-T1 | 0.2778 | multimodel_20211221_v8_he2grid_c03_eps030_dqlm_multivar_al_keep |
| 12/21/2021 | exAL-U-T1 | 0.8334 | multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_univar |
| 12/21/2021 | exAL-M-T0 | 0.9776 | multimodel_20211221_v8_he2tbl1fix20260612_exdqlm_multivar_drop |
| 12/21/2021 | exAL-M-T1 | 0.2604 | multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep |
| 05/11/2022 | N-U-T1 | 0.1508 | multimodel_20220511_v8_he2pubgdpc1r1_ndlm_univar_keep |
| 05/11/2022 | N-M-T0 | 0.6701 | multimodel_20220511_v8_he2pubgdpc1r1_ndlm_main_drop |
| 05/11/2022 | N-M-T1 | 0.8682 | multimodel_20220511_v8_he2pubgdpc1r1_ndlm_main_keep |
| 05/11/2022 | AL-U-T1 | 0.1051 | multimodel_20220511_v8_he2pubgdpc1r1_dqlm_univar_al |
| 05/11/2022 | AL-M-T0 | 0.0994 | multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop |
| 05/11/2022 | AL-M-T1 | 0.0547 | multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_keep |
| 05/11/2022 | exAL-U-T1 | 0.1245 | multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_univar |
| 05/11/2022 | exAL-M-T0 | 1.0209 | multimodel_20220511_v8_he2tbl1fix20260612_exdqlm_multivar_drop |
| 05/11/2022 | exAL-M-T1 | 0.0227 | multimodel_20220511_v8_he2partial20260623_exdqlm_multivar_keep |
| 12/25/2022 | N-U-T1 | 2.4997 | multimodel_20221225_v8_he2tbl1fix20260612_ndlm_univar_keep |
| 12/25/2022 | N-M-T0 | 0.6440 | multimodel_20221225_v8_he2pubgdpc1r1_ndlm_main_drop |
| 12/25/2022 | N-M-T1 | 3.8886 | multimodel_20221225_v8_he2pubgdpc1r1_ndlm_main_keep |
| 12/25/2022 | AL-U-T1 | 1.7338 | multimodel_20221225_v8_he2pubgdpc1r1_dqlm_univar_al |
| 12/25/2022 | AL-M-T0 | 1.3370 | multimodel_20221225_v8_he2tbl1fix20260612_dqlm_multivar_al_drop |
| 12/25/2022 | AL-M-T1 | 0.6276 | multimodel_20221225_v8_he2grid_c05_eps030_dqlm_multivar_al_keep |
| 12/25/2022 | exAL-U-T1 | 1.7055 | multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar |
| 12/25/2022 | exAL-M-T0 | 1.2113 | multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_drop |
| 12/25/2022 | exAL-M-T1 | 0.5381 | multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep |

## Within-Cutoff Input Congruence

| Cutoff | Artifact Checks Passing | Result |
|---|---|---|
| 01/23/2021 | 10 / 10 | Aligned |
| 11/12/2021 | 10 / 10 | Aligned |
| 12/21/2021 | 10 / 10 | Aligned |
| 05/11/2022 | 10 / 10 | Aligned |
| 12/25/2022 | 10 / 10 | Aligned |

Archival caveat:
- `usgs_daily.csv` was not preserved inside some older multivariate quantile run roots, so the strict within-cutoff congruence table is evaluated on the **10 fit/forecast/blended-covariate artifacts** rather than on the auxiliary USGS cache file.
- Input congruence is now a final-pass claim across the 10 fit/forecast/blended-covariate artifacts required for the Bayesian benchmark rows.

## Publication Rows

| Cutoff | Label | CRPS | Run ID | Campaign | Note |
|---|---|---|---|---|---|
| 01/23/2021 | N-U-T1 | 0.3359 | multimodel_20210123_v8_he2pubgdpc1r1_ndlm_univar_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 01/23/2021 | N-M-T0 | 1.8433 | multimodel_20210123_v8_he2tbl1fix20260612_ndlm_main_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 01/23/2021 | N-M-T1 | 3.2149 | multimodel_20210123_v8_he2pubgdpc1r1_ndlm_main_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 01/23/2021 | AL-U-T1 | 0.2311 | multimodel_20210123_v8_he2pubgdpc1r1_dqlm_univar_al | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 01/23/2021 | AL-M-T0 | 0.4680 | multimodel_20210123_v8_he2pubgdpc1r1_dqlm_multivar_al_drop | dqlm_multivar_al_drop_p5_production_20260606:canonical_bundle_promoted | canonical-bundle promoted |
| 01/23/2021 | AL-M-T1 | 0.1459 | multimodel_20210123_v8_he2grid_c04_eps365_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 01/23/2021 | exAL-U-T1 | 0.2162 | multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_univar | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 01/23/2021 | exAL-M-T0 | 0.7568 | multimodel_20210123_v8_he2tbl1fix20260612_exdqlm_multivar_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 01/23/2021 | exAL-M-T1 | 0.1397 | multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |
| 11/12/2021 | N-U-T1 | 0.1706 | multimodel_20211112_v8_he2pubgdpc1r1_ndlm_univar_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | N-M-T0 | 0.3802 | multimodel_20211112_v8_he2pubgdpc1r1_ndlm_main_drop | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | N-M-T1 | 0.8910 | multimodel_20211112_v8_he2pubgdpc1r1_ndlm_main_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | AL-U-T1 | 0.0779 | multimodel_20211112_v8_he2pubgdpc1r1_dqlm_univar_al | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 11/12/2021 | AL-M-T0 | 0.1999 | multimodel_20211112_v8_he2pubgdpc1r1_dqlm_multivar_al_drop | dqlm_multivar_al_drop_p5_production_20260606:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | AL-M-T1 | 0.0555 | multimodel_20211112_v8_he2grid_c04_eps365_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 11/12/2021 | exAL-U-T1 | 0.1019 | multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_univar | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 11/12/2021 | exAL-M-T0 | 1.7214 | multimodel_20211112_v8_he2tbl1fix20260612_exdqlm_multivar_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 11/12/2021 | exAL-M-T1 | 0.0472 | multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep | exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner | canonical-bundle promoted |
| 12/21/2021 | N-U-T1 | 1.1934 | multimodel_20211221_v8_he2tbl1fix20260612_ndlm_univar_keep | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 12/21/2021 | N-M-T0 | 0.6596 | multimodel_20211221_v8_he2pubgdpc1r1_ndlm_main_drop | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 12/21/2021 | N-M-T1 | 3.0436 | multimodel_20211221_v8_he2tbl1fix20260612_ndlm_main_keep | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 12/21/2021 | AL-U-T1 | 0.8705 | multimodel_20211221_v8_he2pubgdpc1r1_dqlm_univar_al | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 12/21/2021 | AL-M-T0 | 0.5867 | multimodel_20211221_v8_he2pubgdpc1r1_dqlm_multivar_al_drop | dqlm_multivar_al_drop_p5_production_20260606:canonical_bundle_promoted | canonical-bundle promoted |
| 12/21/2021 | AL-M-T1 | 0.2778 | multimodel_20211221_v8_he2grid_c03_eps030_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/21/2021 | exAL-U-T1 | 0.8334 | multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_univar | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 12/21/2021 | exAL-M-T0 | 0.9776 | multimodel_20211221_v8_he2tbl1fix20260612_exdqlm_multivar_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 12/21/2021 | exAL-M-T1 | 0.2604 | multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep | exdqlm_multivar_keep_partial_authority_refresh_20260623:clean_replay | targeted repair replacement |
| 05/11/2022 | N-U-T1 | 0.1508 | multimodel_20220511_v8_he2pubgdpc1r1_ndlm_univar_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 05/11/2022 | N-M-T0 | 0.6701 | multimodel_20220511_v8_he2pubgdpc1r1_ndlm_main_drop | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 05/11/2022 | N-M-T1 | 0.8682 | multimodel_20220511_v8_he2pubgdpc1r1_ndlm_main_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 05/11/2022 | AL-U-T1 | 0.1051 | multimodel_20220511_v8_he2pubgdpc1r1_dqlm_univar_al | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 05/11/2022 | AL-M-T0 | 0.0994 | multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 05/11/2022 | AL-M-T1 | 0.0547 | multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_keep | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 05/11/2022 | exAL-U-T1 | 0.1245 | multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_univar | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 05/11/2022 | exAL-M-T0 | 1.0209 | multimodel_20220511_v8_he2tbl1fix20260612_exdqlm_multivar_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 05/11/2022 | exAL-M-T1 | 0.0227 | multimodel_20220511_v8_he2partial20260623_exdqlm_multivar_keep | exdqlm_multivar_keep_partial_authority_refresh_20260623:clean_replay | targeted repair replacement |
| 12/25/2022 | N-U-T1 | 2.4997 | multimodel_20221225_v8_he2tbl1fix20260612_ndlm_univar_keep | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 12/25/2022 | N-M-T0 | 0.6440 | multimodel_20221225_v8_he2pubgdpc1r1_ndlm_main_drop | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 12/25/2022 | N-M-T1 | 3.8886 | multimodel_20221225_v8_he2pubgdpc1r1_ndlm_main_keep | ndlm_publication_promotion_20260607:canonical_bundle_promoted | canonical-bundle promoted |
| 12/25/2022 | AL-U-T1 | 1.7338 | multimodel_20221225_v8_he2pubgdpc1r1_dqlm_univar_al | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 12/25/2022 | AL-M-T0 | 1.3370 | multimodel_20221225_v8_he2tbl1fix20260612_dqlm_multivar_al_drop | he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair | targeted repair replacement |
| 12/25/2022 | AL-M-T1 | 0.6276 | multimodel_20221225_v8_he2grid_c05_eps030_dqlm_multivar_al_keep | dqlm_multivar_al_keep_from_exal_winners_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/25/2022 | exAL-U-T1 | 1.7055 | multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar | he2_univar_al_exal_scale_repair_20260629:log1p_scale_repair | targeted repair replacement |
| 12/25/2022 | exAL-M-T0 | 1.2113 | multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_drop | exdqlm_multivar_drop_current_relaunch_q50repair_20260602:canonical_bundle_promoted | canonical-bundle promoted |
| 12/25/2022 | exAL-M-T1 | 0.5381 | multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep | exdqlm_multivar_keep_partial_authority_refresh_20260623:clean_replay | targeted repair replacement |

## Outputs

- manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- inputs: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_inputs.csv`
- alignment: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv`

