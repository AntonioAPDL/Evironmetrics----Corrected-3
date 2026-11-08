from __future__ import annotations

import csv
import hashlib
import json
import re
import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from manuscript_text_contract import active_tex, cited_url, has_concepts, has_label, in_order, scientific_checks, structure_checks


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArticleA1AndTableContractTests(unittest.TestCase):
    def article_text(self) -> str:
        return active_tex((ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8"))

    def assertConcepts(self, article: str, *patterns: str) -> None:
        self.assertTrue(has_concepts(article, *patterns), f"Missing scientific concepts: {patterns}")

    def assertScientificChecks(self, article: str, names: list[str]) -> None:
        failed = [name for name, ok, _ in scientific_checks(article, names) if not ok]
        self.assertFalse(failed, failed)

    def test_software_availability_manifest_and_text_are_wired(self) -> None:
        manifest_path = ROOT / "artifacts" / "software_availability" / "software_availability_manifest.json"
        self.assertTrue(manifest_path.exists(), f"missing software availability manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("schema_version"), "revision_software_availability_v1")
        self.assertEqual(
            manifest.get("public_estimation_package", {}).get("cran_package_url"),
            "https://CRAN.R-project.org/package=exdqlm",
        )
        self.assertEqual(
            manifest.get("public_estimation_package", {}).get("package_doi"),
            "https://doi.org/10.32614/CRAN.package.exdqlm",
        )
        self.assertEqual(
            manifest.get("study_workflow_repository", {}).get("public_url"),
            "https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility",
        )
        self.assertEqual(
            manifest.get("study_workflow_repository", {}).get("release_readiness_files"),
            {
                "readme": "README.md",
                "citation": "CITATION.cff",
                "license_notice": "LICENSE",
                "validation_script": "scripts/validate_public_repository.py",
            },
        )
        self.assertEqual(
            manifest.get("archive_status", {}).get("workflow_archive_status"),
            "pending_final_release",
        )
        self.assertEqual(manifest.get("archive_status", {}).get("workflow_archive_doi"), "pending")
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn(r"CRAN R package \texttt{exdqlm}", article)
        self.assertIn("https://CRAN.R-project.org/package=exdqlm", article)
        self.assertIn("https://doi.org/10.32614/CRAN.package.exdqlm", article)
        self.assertTrue(cited_url(article, (ROOT / "wileyNJD-APA.bib").read_text(encoding="utf-8"), "https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility"))
        self.assertConcepts(article, r'reproducibility repository', r'staged inputs', r'provenance manifests')
        self.assertNotIn("workflow repository has been archived", article)

    def test_runtime_benchmark_manifest_and_text_are_wired(self) -> None:
        manifest_path = ROOT / "artifacts" / "runtime_benchmark" / "runtime_manifest.json"
        self.assertTrue(manifest_path.exists(), f"missing runtime benchmark manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("schema_version"), "he1_runtime_benchmark_v1")
        self.assertEqual(manifest.get("interface_table", {}).get("row_count"), 1620)
        self.assertEqual(manifest.get("interface_table", {}).get("column_count"), 127)
        self.assertEqual(
            manifest.get("interface_table", {}).get("practical_total_runtime_columns"),
            ["runtime_sec_total", "runtime_sec"],
        )
        self.assertEqual(
            manifest.get("interface_table", {}).get("mostly_missing_decomposition_columns"),
            ["runtime_sec_fit", "runtime_sec_forecast"],
        )
        planned = manifest.get("planned_run_manifest", {})
        self.assertEqual((planned.get("planned_run_units"), planned.get("done"), planned.get("pending")), (72, 54, 18))
        self.assertFalse(manifest.get("claims_policy", {}).get("report_fit_forecast_decomposition"))

        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("about two hours end-to-end", article)
        self.assertScientificChecks(article, ["runtime"])
        self.assertNotIn(r"\texttt{runtime\_sec", article)
        self.assertConcepts(article, r'hardware', r'implementation', r'depends|dependent')
        self.assertNotIn("100 minutes for fitting", article)
        self.assertNotIn("20 minutes for post-processing", article)

    def test_forecast_design_manifest_and_text_are_wired(self) -> None:
        manifest_path = ROOT / "artifacts" / "forecast_design" / "forecast_design_manifest.json"
        self.assertTrue(manifest_path.exists(), f"missing forecast-design manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("schema_version"), "he6_forecast_design_v1")
        self.assertEqual(
            manifest.get("rolling_origin_design", {}).get("held_out_target"),
            "post_cutoff_usgs_only",
        )
        fair_assessment = manifest.get("rolling_origin_design", {}).get("fair_assessment", {})
        self.assertEqual(
            fair_assessment.get("cross_validation_analogue"),
            "time_ordered_rolling_origin_folds",
        )
        self.assertEqual(fair_assessment.get("fold_unit"), "forecast_origin_cutoff")
        self.assertFalse(fair_assessment.get("dense_overlapping_origins_claimed"))
        self.assertIn("version", fair_assessment.get("dense_origin_policy", ""))
        self.assertIn("overrepresent", fair_assessment.get("dense_origin_policy", ""))
        self.assertEqual(
            manifest.get("forecast_origin_inputs", {}).get("forecast_products", {}).get("timing"),
            "latest_issued_at_or_before_cutoff",
        )
        self.assertEqual(
            manifest.get("forecast_origin_inputs", {}).get("local_covariates", {}).get("names"),
            ["precipitation", "soil_moisture"],
        )
        precipitation_handling = (
            manifest.get("forecast_origin_inputs", {})
            .get("local_covariates", {})
            .get("precipitation_handling", {})
        )
        self.assertFalse(precipitation_handling.get("censoring_model"))
        self.assertFalse(precipitation_handling.get("zero_inflation_model"))
        self.assertFalse(precipitation_handling.get("occurrence_intensity_model"))
        self.assertEqual(
            precipitation_handling.get("zero_precipitation_policy"),
            "retained_as_zero_in_supplied_covariate_path",
        )
        self.assertEqual(
            precipitation_handling.get("model_role"),
            "external_transfer_covariate_and_deterministic_engineered_terms",
        )
        gdpc = manifest.get("forecast_origin_inputs", {}).get("gdpc_pca", {})
        self.assertEqual(gdpc.get("workflow_slot"), "PCA")
        self.assertEqual(gdpc.get("canonical_name"), "GDPC1")
        self.assertFalse(gdpc.get("operational_forecast_product"))
        self.assertFalse(gdpc.get("verification_target"))
        self.assertFalse(manifest.get("claims_policy", {}).get("post_cutoff_usgs_used_for_fit_or_update"))
        self.assertFalse(manifest.get("claims_policy", {}).get("continuous_daily_post_2022_hindcast_claimed"))

        self.assertTrue((ROOT / "docs" / "forecast_design_contract.md").exists())
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertScientificChecks(article, ['transfer_inputs', 'climate_covariates', 'verification', 'data_roles', 'origin_design'])
        self.assertConcepts(article, r'precipitation', r'dry days', r'no separate precipitation occurrence or intensity model', r'deterministic', r'nonlinear')
        self.assertNotIn("GDPC forecast product", article)

    def test_selected_prior_and_discount_text_are_manifest_backed(self) -> None:
        manifest_path = ROOT / "artifacts" / "he2_publication_freeze" / "he2_bayesian_publication_manifest.csv"
        self.assertTrue(manifest_path.exists(), f"missing HE2 publication manifest: {manifest_path}")
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            rows = [
                row
                for row in csv.DictReader(handle)
                if row["manuscript_label"] == "exAL-M-T1"
            ]
        self.assertEqual(len(rows), 5)
        for row in rows:
            state = json.loads(row["state_evolution_json"])
            prior = json.loads(row["prior_json"])
            self.assertEqual(float(state["lambda"]), 0.97)
            forecast_cov = prior.get("forecast_cov", {})
            self.assertIn("epsilon", forecast_cov, row["run_id"])
            self.assertEqual(float(forecast_cov.get("c_factor")), 1.0)

        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertRegex(article, r"\\lambda\s*=\s*0\.97")
        self.assertRegex(article, r"(?<![A-Za-z])c\s*=\s*1")
        self.assertRegex(article, r"\\epsilon\s*=\s*1")
        self.assertScientificChecks(article, ['prior_weighting'])
        self.assertConcepts(article, r'pre.cutoff observational window', r'held fixed|fixed persistence')
        self.assertNotIn("c = 10^2", article)
        self.assertNotIn("epsilon = T", article)
        self.assertNotIn(r"\lambda=0.8995", article)

    def test_latest_forecast_issue_manifest_and_text_are_wired(self) -> None:
        manifest_path = ROOT / "artifacts" / "latest_forecast_issue" / "latest_forecast_issue_manifest.json"
        self.assertTrue(manifest_path.exists(), f"missing latest-forecast manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("schema_version"), "he7_latest_forecast_issue_v1")
        protocol = manifest.get("protocol", {})
        self.assertEqual(protocol.get("name"), "latest_forecast_only")
        self.assertEqual(protocol.get("publication_weighting_scheme"), "latest")
        self.assertFalse(protocol.get("cross_issue_weighting_used"))
        self.assertTrue(protocol.get("legacy_weighted_daily_filenames_are_aliases"))
        self.assertEqual(
            manifest.get("sources", {}).get("glofas", {}).get("selection_rule"),
            "issue_date_equals_cutoff",
        )
        self.assertEqual(
            manifest.get("sources", {}).get("nws", {}).get("selection_rule"),
            "latest_issue_datetime_per_target_hour_member_then_daily_mean",
        )

        self.assertTrue((ROOT / "docs" / "latest_forecast_issue_contract.md").exists())
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertScientificChecks(article, ['latest_issue', 'verification'])
        self.assertConcepts(article, r'GloFAS issues daily forecasts|GloFAS.{0,30}daily', r'hourly NWS|NWS.{0,30}hourly', r'latest available issuance', r'target time and member', r'aggregat')
        self.assertNotIn("weighted combination of prior forecasts", article)

    def test_reviewer1_overview_forecasting_emphasis_is_wired(self) -> None:
        article = self.article_text()
        self.assertFalse([name for name, ok, _ in structure_checks(article) if not ok])
        self.assertConcepts(article, r'forecast', r'uncertainty', r'five', r'CRPS', r'quantile', r'illustrat')
        for retired in ["General Results", "Model A", "Model B", "Model C", "forecasting component is limited"]:
            self.assertNotIn(retired, article)

    def test_reviewer1_conceptual_model_practicality_is_wired(self) -> None:
        self.assertScientificChecks(self.article_text(), ['physical_models'])

    def test_reviewer1_flexile_typo_is_absent_from_article(self) -> None:
        article = self.article_text()
        self.assertScientificChecks(article, ['likelihood'])
        self.assertNotIn("flexile", article.lower())

    def test_reviewer1_expanded_forecast_evidence_is_wired(self) -> None:
        article = self.article_text()
        self.assertScientificChecks(article, ['origin_design', 'verification', 'scores'])
        for label in ['sec:forecastvalidation', 'subsec:synthillustration', 'sec:interpretation']:
            self.assertTrue(has_label(article, label), label)
        for table in ['benchmark_crps_main_table.tex', 'benchmark_crps_nws_horizon_table.tex', 'he4_quantile_check_loss_main_table.tex']:
            self.assertIn(r'\input{tables/generated_tex/' + table + '}', article)

    def test_reviewer1_fair_forecast_assessment_is_wired(self) -> None:
        article = self.article_text()
        self.assertScientificChecks(article, ['origin_design', 'verification', 'archive_work'])
        self.assertNotIn("random K-fold cross-validation", article)

    def test_reviewer1_uncertainty_sources_are_distinguished(self) -> None:
        article = self.article_text()
        self.assertConcepts(article, r'hydrolog\w* uncertainty', r'structur', r'parameters?', r'states?', r'observations?')
        self.assertConcepts(article, r'meteorolog\w* uncertainty', r'precipitation', r'forc')
        self.assertScientificChecks(article, ['climate_covariates', 'data_roles'])
        self.assertNotIn("local hydrological covariates", article)

    def test_submission_repo_points_to_clean_reproducibility_bundle(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "software_availability_contract.md").read_text(encoding="utf-8")
        self.assertIn("san-lorenzo-exdqlm-reproducibility", readme)
        self.assertIn("san-lorenzo-exdqlm-reproducibility", contract)

    def test_reviewer1_era5_reanalysis_uncertainty_is_wired(self) -> None:
        article = self.article_text()
        self.assertConcepts(article, r'ERA5.Land', r'reanalysis', r'covariate', r'verification')

    def test_reviewer1_usgs_target_and_data_roles_are_wired(self) -> None:
        article = self.article_text()
        self.assertTrue(has_label(article, 'sec:data'))
        self.assertTrue(in_order(article, r'\label{sec:data}', r'\label{sec:methodology}'))
        self.assertScientificChecks(article, ['data_roles'])

    def test_reviewer1_model_formulation_links_to_results(self) -> None:
        article = self.article_text()
        self.assertScientificChecks(article, ['variants'])
        self.assertTrue(in_order(article, r'\label{sec:methodology}', r'\label{sec:evaluation}', r'\label{sec:forecastvalidation}'))
        for retired in ["Model A", "Model B", "Model C", "General Results"]:
            self.assertNotIn(retired, article)

    def test_figure_a1_renderer_uses_samplewise_component_contract(self) -> None:
        script = ROOT / "scripts" / "render_authoritative_selected_model_support_figures.R"
        text = script.read_text(encoding="utf-8")
        self.assertIn("FIGURE_A1_COMPONENT <- 6L", text)
        self.assertIn(
            'FIGURE_A1_COMPONENT_CONTRACT <- "raw_state_component"',
            text,
        )
        self.assertIn(
            'COMPONENT_6_PLUS_TREND_CONTRACT <- "component_6_plus_trend_component_1_samplewise"',
            text,
        )
        self.assertIn(
            'COMPONENT_6_MINUS_TREND_CONTRACT <- "component_6_minus_trend_component_1_samplewise"',
            text,
        )
        self.assertIn("hydrologic_regime_periods <- function()", text)
        self.assertIn('"2012-01-01"', text)
        self.assertIn('"2016-12-31"', text)
        self.assertIn('"2017-01-01"', text)
        self.assertIn('"2019-12-31"', text)
        self.assertNotIn(
            'components$component_contract == "component_6_shifted_by_posterior_mean_trend_component_1"',
            text,
        )
        self.assertIn("component_analysis_specs <- function(component_df)", text)
        self.assertIn("COMPONENT_ANALYSIS_LEGACY_EXCLUDED_CONTRACTS", text)
        self.assertIn("include_in_manuscript = FALSE", text)

    def test_figure_a1_render_metadata_records_contract_and_periods(self) -> None:
        meta_path = (
            ROOT
            / "artifacts"
            / "representative_selected_model_2022_12_25"
            / "authoritative_support"
            / "figures"
            / "render_metadata.json"
        )
        self.assertTrue(meta_path.exists(), f"missing render metadata: {meta_path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(meta.get("figure_a1_component"), 6)
        self.assertEqual(
            meta.get("figure_a1_component_contract"),
            "raw_state_component",
        )
        self.assertEqual(
            meta.get("figure_a1_article_display_label"),
            "long-cycle seasonal component only (about 6.78 years)",
        )
        self.assertIn(meta.get("render_contract_version"), ["authoritative_selected_model_support_figures_v2", "authoritative_selected_model_support_figures_v3"])
        self.assertAlmostEqual(meta.get("long_cycle_period_days"), 363.5854 * 6.8068493, places=3)
        self.assertAlmostEqual(meta.get("long_cycle_period_years"), meta["long_cycle_period_days"] / 365.2425, places=3)
        if meta.get("render_contract_version").endswith("_v2"):
            revision = meta.get("component_label_revision", {})
            self.assertTrue(revision.get("component_only"))
            self.assertEqual(revision.get("renderer_contract"), "authoritative_selected_model_support_figures_v3")
        self.assertIn("source_support_generated_at_utc", meta)
        self.assertNotIn("render_staging_support_dir", meta)
        self.assertNotIn("generated_at_utc", meta)
        periods = meta.get("hydrologic_regime_periods")
        self.assertIsInstance(periods, list)
        self.assertEqual(
            [(row.get("period"), row.get("start"), row.get("end")) for row in periods],
            [("Dry", "2012-01-01", "2016-12-31"), ("Wet", "2017-01-01", "2019-12-31")],
        )
        component_analysis = meta.get("component_analysis")
        self.assertIsInstance(component_analysis, dict)
        self.assertEqual(component_analysis.get("figure_count"), 9)
        self.assertIn(
            "component_06_raw_state_component.png",
            component_analysis.get("files", []),
        )
        self.assertIn(
            "component_06_component_6_plus_trend_component_1_samplewise.png",
            component_analysis.get("files", []),
        )
        self.assertIn(
            "component_06_component_6_minus_trend_component_1_samplewise.png",
            component_analysis.get("files", []),
        )

    def test_selected_support_manifest_records_current_rdata_rebuild(self) -> None:
        support_dir = (
            ROOT
            / "artifacts"
            / "representative_selected_model_2022_12_25"
            / "authoritative_support"
        )
        with (support_dir / "manifest.csv").open(newline="", encoding="utf-8") as handle:
            manifest_rows = list(csv.DictReader(handle))
        manifest_row = next(row for row in manifest_rows if row["filename"] == "authoritative_selected_support_manifest.json")
        external_manifest = Path(manifest_row["source_absolute_path"])
        self.assertTrue(external_manifest.exists(), f"missing external support manifest: {external_manifest}")
        payload = json.loads(external_manifest.read_text(encoding="utf-8"))
        self.assertIn("authoritative_rdata_retained_current_20260623", payload.get("run_id", ""))
        self.assertIn("dynamics_rebuild", payload)
        self.assertIn("component_rebuild", payload)
        self.assertEqual(
            payload.get("dynamics_rebuild", {}).get("usgs_location_source"),
            "row 1 of exps/exps2",
        )
        self.assertEqual(payload.get("component_rows"), 389850)
        self.assertEqual(payload.get("dynamics_rows"), 38985)

    def test_component_analysis_gallery_is_analysis_only(self) -> None:
        support_dir = (
            ROOT
            / "artifacts"
            / "representative_selected_model_2022_12_25"
            / "authoritative_support"
        )
        manifest_path = support_dir / "analysis_figures" / "component_evolution" / "component_analysis_manifest.csv"
        self.assertTrue(manifest_path.exists(), f"missing component analysis manifest: {manifest_path}")
        text = manifest_path.read_text(encoding="utf-8")
        self.assertIn("component_01_raw_state_component.png", text)
        self.assertIn("component_07_raw_state_component.png", text)
        self.assertIn("component_06_component_6_plus_trend_component_1_samplewise.png", text)
        self.assertIn("component_06_component_6_minus_trend_component_1_samplewise.png", text)
        self.assertNotIn("component_6_shifted_by_posterior_mean_trend_component_1", text)
        self.assertIn("source_support_generated_at_utc", text)
        self.assertNotIn("rendered_at_utc", text)
        self.assertNotIn("TRUE", text)

        manuscript_manifest = json.loads((ROOT / "MANUSCRIPT_ASSET_MANIFEST.json").read_text(encoding="utf-8"))
        manifest_blob = json.dumps(manuscript_manifest)
        self.assertNotIn("analysis_figures/component_evolution", manifest_blob)
        bundle_manifest = (support_dir / "manifest.csv").read_text(encoding="utf-8")
        self.assertIn("analysis_component", bundle_manifest)

    def test_reviewer1_figure_variance_explanation_and_lineage_are_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertScientificChecks(article, ['uncertainty_estimands', 'synthesis'])
        self.assertConcepts(article, r'1/6.8068493', r'363.5854', r'2[,.]?474.871|2474.87')

        manifest = json.loads((ROOT / "MANUSCRIPT_ASSET_MANIFEST.json").read_text(encoding="utf-8"))
        by_label = {row["label"]: row for row in manifest["figures"]}
        expected_selected = {
            "fig:dry_quantile": "artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_quantile_dry_period.png",
            "fig:rainy_quantile": "artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_quantile_wet_period.png",
            "fig:80_components": "artifacts/representative_selected_model_2022_12_25/authoritative_support/figures/selected_model_component_80month.png",
            "fig:synth1": "artifacts/five_cutoff_main_model_synthesis/20221225_exal_m_t1/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png",
        }
        for label, source_path in expected_selected.items():
            self.assertEqual(by_label[label]["source_path"], source_path)
            self.assertEqual(by_label[label]["source_class"], "current_selected_model_representative")
            self.assertTrue(by_label[label]["current_model_output_wired"])

        self.assertEqual(
            by_label["fig:synth2"]["source_path"],
            "artifacts/historical_support_from_current_models/figures/reference_synthesis_univariate.png",
        )
        self.assertEqual(by_label["fig:synth2"]["source_class"], "current_model_output_support")
        fig_synth2_source = ROOT / by_label["fig:synth2"]["source_path"]
        fig_synth2_manuscript = ROOT / by_label["fig:synth2"]["manuscript_path"]
        fig_synth2_cutoff_family = (
            ROOT / "Figures" / "reference_synthesis_by_cutoff" / "cutoff_2022_12_25_reference_synthesis.png"
        )
        fig_synth2_legacy_mirror = (
            ROOT / "Figures" / "manuscript" / "reference_synthesis_univariate.png"
        )
        for path in [
            fig_synth2_source,
            fig_synth2_manuscript,
            fig_synth2_cutoff_family,
            fig_synth2_legacy_mirror,
        ]:
            self.assertTrue(path.exists(), f"missing Figure A2/reference-synthesis asset: {path}")
        expected_digest = sha256(fig_synth2_cutoff_family)
        self.assertEqual(sha256(fig_synth2_source), expected_digest)
        self.assertEqual(sha256(fig_synth2_manuscript), expected_digest)
        self.assertEqual(sha256(fig_synth2_legacy_mirror), expected_digest)

        provenance = (ROOT / "docs" / "figure_table_provenance.md").read_text(encoding="utf-8")
        self.assertIn("selected_model_quantile_dry_period.png", provenance)
        self.assertIn("selected_model_quantile_wet_period.png", provenance)
        self.assertIn("selected_model_component_80month.png", provenance)
        self.assertIn("not full posterior predictive distributions", provenance)

    def test_cutoff_appendix_uses_multivariate_synthesis_overlays(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("{Figures/multivariate_synthesis_by_cutoff/}", article)
        self.assertIn("Additional Cutoff-Specific Predictive Synthesis Panels", article)
        for name in [
            "cutoff_2021_01_23_multivariate_synthesis_with_reference_ensembles.png",
            "cutoff_2021_11_12_multivariate_synthesis_with_reference_ensembles.png",
            "cutoff_2021_12_21_multivariate_synthesis_with_reference_ensembles.png",
            "cutoff_2022_05_11_multivariate_synthesis_with_reference_ensembles.png",
            "cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png",
        ]:
            self.assertIn(name, article)
        for retired in [
            "cutoff_2021_01_23_setup_support.png",
            "cutoff_2021_11_12_setup_support.png",
            "cutoff_2021_12_21_setup_support.png",
            "cutoff_2022_05_11_setup_support.png",
        ]:
            self.assertNotIn(retired, article)

    def test_selected_model_quantile_figures_use_current_rating_references(self) -> None:
        renderer = (ROOT / "scripts" / "render_authoritative_selected_model_support_figures.R").read_text(encoding="utf-8")
        self.assertIn("figure_flood_label_df", renderer)
        self.assertIn("figure_flood_stage_style", renderer)
        self.assertIn("geom_hline", renderer)
        self.assertIn("7402.38", renderer)
        self.assertIn("14895.73", renderer)
        self.assertIn("Minor reference", renderer)
        self.assertIn("Major reference", renderer)
        self.assertNotIn("5.20948615", renderer)
        self.assertNotIn("6.06378521", renderer)

    def test_overleaf_bundle_excludes_large_compact_support_data(self) -> None:
        support_dir = (
            ROOT
            / "artifacts"
            / "representative_selected_model_2022_12_25"
            / "authoritative_support"
        )
        forbidden = [
            "authoritative_component_summary.csv",
            "authoritative_component_summary.rds",
            "authoritative_usgs_quantile_dynamics_summary.csv",
            "authoritative_usgs_quantile_dynamics_summary.rds",
            "authoritative_selected_support_manifest.json",
            "authoritative_selected_support_lineage.csv",
        ]
        for filename in forbidden:
            self.assertFalse((support_dir / filename).exists(), f"large support payload should stay external: {filename}")

        refresh_script = (ROOT / "scripts" / "refresh_authoritative_selected_model_support_figures.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("tempfile.TemporaryDirectory", refresh_script)
        self.assertIn("external_support_data", refresh_script)
        self.assertNotIn("copy_required_support", refresh_script)

    def test_generated_table_builder_uses_single_five_decimal_policy(self) -> None:
        script = ROOT / "scripts" / "build_generated_table_includes.py"
        text = script.read_text(encoding="utf-8")
        self.assertIn("DISPLAY_DIGITS = 5", text)
        self.assertNotIn(":.4f", text)
        self.assertNotIn(", 3)", text)
        self.assertIn("fmt_display", text)
        self.assertIn("table-format=-1.5", text)
        self.assertIn("BENCHMARK_LONG_HORIZON_DAYS = 28", text)
        self.assertIn("BENCHMARK_NWS_COMMON_HORIZON_DAYS = 8", text)
        self.assertIn("BENCHMARK_LONG_RAW_ROW_ORDER = ['RAW-GLOFAS']", text)

    def test_benchmark_tables_separate_28_day_and_nws_common_horizons(self) -> None:
        table_dir = ROOT / "tables" / "generated_tex"
        long_table = table_dir / "benchmark_crps_main_table.tex"
        short_table = table_dir / "benchmark_crps_nws_horizon_table.tex"
        source_csv = table_dir / "benchmark_crps_horizon_summary.csv"
        self.assertTrue(long_table.exists(), f"missing 28-day table: {long_table}")
        self.assertTrue(short_table.exists(), f"missing NWS-horizon table: {short_table}")
        self.assertTrue(source_csv.exists(), f"missing horizon audit CSV: {source_csv}")

        long_text = long_table.read_text(encoding="utf-8")
        short_text = short_table.read_text(encoding="utf-8")
        self.assertIn("Mean 28-day forecast-window CRPS", long_text)
        self.assertIn("RAW-GLOFAS", long_text)
        self.assertNotIn("RAW-NWS &", long_text)
        self.assertIn("normal dynamic linear model baselines", long_text)
        self.assertIn("Mean CRPS over the common eight-day NWS forecast horizon", short_text)
        self.assertIn("RAW-GLOFAS", short_text)
        self.assertIn("RAW-NWS", short_text)
        self.assertIn("forecast leads 1--8", short_text)

        source_text = source_csv.read_text(encoding="utf-8")
        self.assertIn("tab:benchmark_crps_models,RAW-GLOFAS,20210123,28", source_text)
        self.assertNotIn("tab:benchmark_crps_models,RAW-NWS", source_text)
        self.assertIn("tab:benchmark_crps_models_nws_horizon,RAW-NWS,20210123,8", source_text)

    def test_he3_ablation_tables_separate_28_day_and_nws_common_horizons(self) -> None:
        table_dir = ROOT / "tables" / "generated_tex"
        long_table = table_dir / "he3_ablation_crps_main_table.tex"
        short_table = table_dir / "he3_ablation_crps_nws_horizon_table.tex"
        source_csv = table_dir / "he3_ablation_crps_horizon_summary.csv"
        self.assertTrue(long_table.exists(), f"missing HE3 28-day table: {long_table}")
        self.assertTrue(short_table.exists(), f"missing HE3 NWS-horizon table: {short_table}")
        self.assertTrue(source_csv.exists(), f"missing HE3 horizon audit CSV: {source_csv}")

        long_text = long_table.read_text(encoding="utf-8")
        short_text = short_table.read_text(encoding="utf-8")
        self.assertIn("Component-removal sensitivity analysis for 28-day forecast-window CRPS", long_text)
        self.assertIn("RAW-GLOFAS", long_text)
        self.assertNotIn("RAW-NWS &", long_text)
        self.assertIn("noH3", long_text)
        self.assertIn("1/6.8068493", long_text)
        self.assertIn("Component-removal sensitivity analysis over the common eight-day NWS forecast horizon", short_text)
        self.assertIn("RAW-GLOFAS", short_text)
        self.assertIn("RAW-NWS", short_text)
        self.assertIn("forecast leads 1--8", short_text)

        article_text = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn(r"Appendix~\ref{app:he3ablation}", article_text)
        self.assertIn(r"\label{app:he3ablation}", article_text)
        self.assertIn("1/6.8068493", article_text)
        self.assertLess(
            article_text.index(r"\appendix"),
            article_text.index(r"\input{tables/generated_tex/he3_ablation_crps_main_table.tex}"),
        )
        self.assertEqual(
            article_text.count(r"\input{tables/generated_tex/he3_ablation_crps_main_table.tex}"),
            1,
        )
        self.assertEqual(
            article_text.count(r"\input{tables/generated_tex/he3_ablation_crps_nws_horizon_table.tex}"),
            1,
        )

        source_text = source_csv.read_text(encoding="utf-8")
        self.assertIn("tab:he3_ablation_crps,RAW-GLOFAS,20210123,28", source_text)
        self.assertNotIn("tab:he3_ablation_crps,RAW-NWS", source_text)
        self.assertIn("tab:he3_ablation_crps_nws_horizon,RAW-NWS,20210123,8", source_text)

    def test_reviewer1_math_detail_is_streamlined(self) -> None:
        article = self.article_text()
        self.assertScientificChecks(article, ['synthesis', 'scores', 'uncertainty_estimands'])
        for label in ['subsec:quantilesynthesis', 'app:stateconstruction', 'app:augmentation']:
            self.assertTrue(has_label(article, label), label)
        for technical in [r'\label{app:stateconstruction}', r'\label{app:augmentation}', r'\section{Markov Chain Monte Carlo Algorithms}', r'\section{Variational Bayes Algorithms}']:
            self.assertTrue(in_order(article, r'\appendix', technical), technical)
        self.assertConcepts(article, r'isotonic regression', r'monotone rearrangement', r'u_s=s/\(S\+1\)', r'point mass')
        for forbidden in ['probability integral transform', 'PITs are described in detail', 'two-step method', 'resolve quantile crossing']:
            self.assertNotIn(forbidden, article)

    def test_generated_table_decimal_cells_have_five_places(self) -> None:
        table_dir = ROOT / "tables" / "generated_tex"
        self.assertTrue(table_dir.exists(), f"missing generated table dir: {table_dir}")
        decimal = re.compile(r"(?<![A-Za-z0-9/])-?\d+\.(\d+)")
        bad: list[str] = []
        for path in sorted(table_dir.glob("*.tex")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if "&" not in line or line.lstrip().startswith("%"):
                    continue
                if line.startswith("Model &") or line.startswith("RAW-"):
                    pass
                for match in decimal.finditer(line):
                    if len(match.group(1)) != 5:
                        bad.append(f"{path.relative_to(ROOT)}:{lineno}:{match.group(0)}")
        self.assertEqual(bad, [])

    def test_posterior_table_center_policy_matches_export_contract(self) -> None:
        support_root = ROOT / "artifacts" / "representative_selected_model_2022_12_25"
        export_readme = (support_root / "posterior_table_exports_README.md").read_text(encoding="utf-8")
        self.assertIn("gamma_summary.csv: gamma by source x quantile with center=posterior median", export_readme)
        self.assertIn("sigma_summary.csv: sigma by source x quantile with center=posterior median", export_readme)
        self.assertIn("covariate_effects_summary.csv: transfer-function covariate effects with center=posterior mean", export_readme)

        table_dir = ROOT / "tables" / "generated_tex"
        covariates = (table_dir / "representative_covariate_effects_table.tex").read_text(encoding="utf-8")
        gamma = (table_dir / "appendix_gamma_summary_table.tex").read_text(encoding="utf-8")
        sigma = (table_dir / "appendix_sigma_summary_table.tex").read_text(encoding="utf-8")

        self.assertIn("Selected Posterior Means and 95\\% Credible Intervals for Transfer-Function Covariates", covariates)
        self.assertIn(r"\textbf{Mean}", covariates)
        self.assertIn("Posterior means and 95\\% credible intervals", covariates)

        self.assertIn("Posterior Medians and 95\\% Credible Intervals for the Source-Specific Skewness Parameters", gamma)
        self.assertIn("Posterior Medians and 95\\% Credible Intervals for the Source-Specific Scale Parameters", sigma)
        self.assertNotIn("Posterior Means and 95\\% Credible Intervals for the Source-Specific", gamma)
        self.assertNotIn("Posterior Means and 95\\% Credible Intervals for the Source-Specific", sigma)
        self.assertIn(r"\textbf{Median}", gamma)
        self.assertIn(r"\textbf{Median}", sigma)
        self.assertIn("Posterior medians and 95\\% credible intervals", gamma)
        self.assertIn("Posterior medians and 95\\% credible intervals", sigma)


if __name__ == "__main__":
    unittest.main()
