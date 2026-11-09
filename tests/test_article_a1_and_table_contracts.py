from __future__ import annotations

import csv
import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArticleA1AndTableContractTests(unittest.TestCase):
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
        self.assertIn("https://github.com/AntonioAPDL/san-lorenzo-exdqlm-reproducibility", article)
        self.assertIn("clean reproducibility repository for this study", article)
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
        self.assertIn(r"\texttt{runtime\_sec\_total}", article)
        self.assertIn(r"\texttt{runtime\_sec}", article)
        self.assertIn("hardware- and implementation-dependent", article)
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
        self.assertIn("forecast-window precipitation and soil-moisture covariates", article)
        self.assertIn("Precipitation is not modeled through a separate censoring", article)
        self.assertIn("zero-inflation, or occurrence/intensity layer", article)
        self.assertIn("dry days are retained in the supplied covariate path", article)
        self.assertIn("deterministic engineered terms", article)
        self.assertIn("the model is fit using USGS observations and retrospective products available through", article)
        self.assertIn("The forecast-window predictive distributions are then synthesized using the latest forecast products", article)
        self.assertIn("canonical GDPC climate-index factor", article)
        self.assertIn("Post-cutoff USGS observations are reserved strictly for verification", article)
        self.assertIn("not treated as an operational forecast product or verification target", article)
        self.assertNotIn("GDPC forecast product", article)
        self.assertNotIn("GDPC/PCA climate-index factor", article)
        self.assertNotIn("the model is fit using forecast products issued at or before", article)

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
        self.assertIn(r"\lambda=0.97", article)
        self.assertIn(r"\(c=1\)", article)
        self.assertIn("pre-cutoff observational window", article)
        self.assertIn("fixed calibrated specification", article)
        self.assertIn(r"\(\epsilon=1\)", article)
        self.assertIn("controls the prior weight assigned to the covariance structure learned before the cutoff", article)
        self.assertNotIn("c = 10^2", article)
        self.assertNotIn("epsilon = T", article)
        self.assertNotIn(r"\lambda=0.8995", article)
        self.assertNotIn("forecast-window CRPS for the synthesized predictive distribution", article)

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
        self.assertIn("using the latest forecast products issued at or before", article)
        self.assertIn("GloFAS issues forecast products daily, whereas NWS issues them hourly", article)
        self.assertIn("For GloFAS, the forecast matrix is the daily issue associated with the cutoff", article)
        self.assertIn("For NWS, we first restrict to issuances available by the cutoff", article)
        self.assertIn("retain the most recent available issuance for each target time and ensemble member", article)
        self.assertIn("older forecast issuances are not averaged into the publication forecast matrices", article)
        self.assertIn("kept only for workflow file-name compatibility", article)
        self.assertNotIn("weighted combination of prior forecasts", article)

    def test_reviewer1_overview_forecasting_emphasis_is_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("The empirical focus is forecasting performance and uncertainty quantification", article)
        self.assertIn("rather than only historical fit or methodological development in isolation", article)
        self.assertIn(r"Section~\ref{sec:forecastvalidation} reports the out-of-sample forecast validation results", article)
        self.assertIn(r"\section{FORECAST VALIDATION RESULTS}", article)
        self.assertIn(r"\section{INTERPRETATION OF THE SELECTED SPECIFICATION}", article)
        self.assertIn("five-cutoff rolling-origin forecast comparison", article)
        self.assertIn("supporting interpretation for the selected specification", article)
        self.assertIn("comparative forecast evaluation remains the main empirical evidence", article)
        self.assertIn("These figures are interpretation diagnostics", article)
        self.assertIn("It illustrates how the fitted quantile-specific forecasts combine into one predictive distribution", article)
        self.assertNotIn("General Results", article)
        self.assertNotIn("Model A", article)
        self.assertNotIn("Model B", article)
        self.assertNotIn("Model C", article)
        self.assertNotIn("forecasting component is limited", article)

    def test_reviewer1_conceptual_model_practicality_is_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("conceptual or physically based models", article)
        self.assertIn("Conceptual formulations remain especially practical for prediction", article)
        self.assertIn("easier to specify, calibrate, and deploy operationally", article)
        self.assertNotIn("Hydrological predictions are often produced using physical models", article)

    def test_reviewer1_flexile_typo_is_absent_from_article(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn(r"\subsection{Extended Asymmetric Laplace Likelihood}", article)
        self.assertNotIn("flexile", article.lower())

    def test_reviewer1_expanded_forecast_evidence_is_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("five cutoff-specific, version-consistent staged datasets that span contrasting hydrological conditions", article)
        self.assertIn("relatively low-flow windows as well as winter high-flow episodes", article)
        self.assertIn("not a continuous daily hindcast over the full post-2022 period", article)
        self.assertIn("Post-cutoff USGS observations are reserved strictly for verification", article)
        self.assertIn("Forecast skill is evaluated from the resulting posterior predictive distributions by the mean continuous ranked probability score", article)
        self.assertIn("targeted quantile diagnostics", article)
        self.assertIn("Its role is illustrative", article)
        self.assertIn("comparative forecast evaluation remains the main empirical evidence", article)
        self.assertNotIn("only one short forecast has been evaluated", article)

    def test_reviewer1_fair_forecast_assessment_is_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("five cutoff-specific, version-consistent staged datasets", article)
        self.assertIn("uses only information available at that origin to fit seven quantile-specific models", article)
        self.assertNotIn("time-ordered analogue of cross-validation", article)
        self.assertIn("uses only information available at that origin", article)
        self.assertIn("scores that distribution against future USGS observations held out over the forecast window", article)
        self.assertIn("Constructing one staged dataset requires more than shifting the cutoff date", article)
        self.assertIn("archive-feasible, version-consistent origins that span contrasting hydrological settings", article)
        self.assertIn("avoid dense overlaps that would overrepresent the same episode", article)
        self.assertNotIn("random K-fold cross-validation", article)

    def test_reviewer1_uncertainty_sources_are_distinguished(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("These two uncertainty sources are related but distinct", article)
        self.assertIn(
            "Hydrological uncertainty arises from model structure, parameters, states, and observations",
            article,
        )
        self.assertIn(
            "meteorological uncertainty enters through imperfect precipitation and related atmospheric forcing fields",
            article,
        )
        self.assertIn("A useful statistical forecasting framework should keep these roles clear", article)
        self.assertIn("local hydrometeorological covariates", article)
        self.assertIn("precipitation from the PRISM Climate Group", article)
        self.assertIn("soil moisture from ECMWF ERA5-Land", article)
        self.assertNotIn("local hydrological covariates", article)
        self.assertNotIn("does not currently distinguish meteorological and hydrological uncertainty", article)
        self.assertNotIn("meteorological and hydrological concepts are mixed", article)

    def test_submission_repo_points_to_clean_reproducibility_bundle(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "software_availability_contract.md").read_text(encoding="utf-8")
        self.assertIn("san-lorenzo-exdqlm-reproducibility", readme)
        self.assertIn("san-lorenzo-exdqlm-reproducibility", contract)

    def test_reviewer1_era5_reanalysis_uncertainty_is_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("reanalysis-based model inputs", article)
        self.assertIn("rather than direct observations or uncertainty-free measurements", article)
        self.assertIn("ERA5/ERA5-Land variables may include short forecast components", article)
        self.assertIn("not verification observations", article)

    def test_reviewer1_usgs_target_and_data_roles_are_wired(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn(r"\section{APPLICATION DATA AND FORECASTING DESIGN}", article)
        self.assertIn(r"\subsection{Study Setting and Observations}", article)
        self.assertIn("Our target series is", article)
        self.assertIn("USGS target series", article)
        self.assertIn("three additional information sources", article)
        self.assertIn("Each source plays a different role", article)
        self.assertIn("retrospective products are used to learn source-specific discrepancies", article)
        self.assertIn("relative to the USGS target series", article)

    def test_reviewer1_model_formulation_links_to_results(self) -> None:
        article = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")
        self.assertIn("single state-space model", article)
        self.assertIn(r"where \(L\in\{\mathrm{N},\mathrm{AL},\mathrm{exAL}\}\)", article)
        self.assertIn(r"\(S\in\{\mathrm{U},\mathrm{M}\}\)", article)
        self.assertIn(r"\(T\in\{\mathrm{T0},\mathrm{T1}\}\)", article)
        self.assertIn("nine Bayesian variants of the common state-space framework", article)
        self.assertIn("Because exAL-M-T1 is the selected extended-likelihood multivariate specification", article)
        self.assertNotIn("Model A", article)
        self.assertNotIn("Model B", article)
        self.assertNotIn("Model C", article)
        self.assertNotIn("General Results", article)

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
            "long-cycle seasonal component only (about 82 months)",
        )
        self.assertEqual(meta.get("render_contract_version"), "authoritative_selected_model_support_figures_v2")
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
        self.assertIn("uncertainty around fitted quantile-location curves", article)
        self.assertIn("synthesized posterior predictive distribution", article)
        self.assertIn("fitted quantile-specific forecasts combine into one predictive distribution", article)
        self.assertIn("posterior predictive envelope can vary across the forecast window", article)
        self.assertIn("approximately 6.81 years, or about 82 months", article)
        self.assertNotIn("approximately 81-month", article)

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
        self.assertIn("{figures/multivariate_synthesis_by_cutoff/}", article)
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
        article_text = (ROOT / "wileyNJD-APA.tex").read_text(encoding="utf-8")

        self.assertNotIn("probability integral transform", article_text)
        self.assertNotIn("PIT", article_text)
        self.assertIn(
            "For reproducibility, implementation pseudocode for the VB algorithm is provided",
            article_text,
        )
        self.assertIn("It illustrates how the fitted quantile-specific forecasts combine into one predictive distribution", article_text)
        self.assertIn("risk of quantile crossing", article_text)
        self.assertIn("Posterior Predictive Synthesis Across Quantiles", article_text)
        self.assertIn("Predictive Scoring by CRPS", article_text)
        self.assertIn("primary score for forecast-window predictive distributions", article_text)
        self.assertIn("generic empirical predictive distribution", article_text)
        self.assertIn("provide the strongest performance in the 28-day synthesis comparison", article_text)
        self.assertIn("dynamic decomposition into source-specific corrections, trend, seasonal structure, and transfer effects", article_text)
        self.assertIn("The five-cutoff evaluation is not a dense continuous hindcast", article_text)
        self.assertIn("isotonic regression", article_text)
        self.assertIn("monotone rearrangement", article_text)
        self.assertIn(r"u_s=s/(S+1)", article_text)
        self.assertIn("point mass", article_text)
        self.assertNotIn("deterministic forecast", article_text)
        self.assertNotIn(r"{\mathbb E}_G|Y - y|", article_text)
        self.assertNotIn("empirical CRPS estimator", article_text)
        self.assertEqual(article_text.count("quantile crossing"), 1)
        self.assertLess(
            article_text.index(r"\appendix"),
            article_text.index(r"\section{Markov Chain Monte Carlo Algorithms}"),
        )
        self.assertLess(
            article_text.index(r"\appendix"),
            article_text.index(r"\section{Variational Bayes Algorithms}"),
        )
        for forbidden in [
            "PITs are described in detail",
            "two-step method",
            "resolve quantile crossing",
            "Posterior Predictive Synthesis part",
        ]:
            self.assertNotIn(forbidden, article_text)

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
