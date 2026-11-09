#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MANIFEST_FILENAME = 'MANUSCRIPT_ASSET_MANIFEST.json'

MANUSCRIPT_FIGURE_FILENAMES = {
    'fig:sanlorenzo': 'site_context_usgs.png',
    'fig:covariates': 'covariate_context_precip_soil_gdpc.png',
    'fig:retrospectives': 'retrospective_products_context.png',
    'fig:ensembles': 'forecast_products_context.png',
    'fig:dry_quantile': 'historical_summary_dry_period.png',
    'fig:rainy_quantile': 'historical_summary_wet_period.png',
    'fig:synth1': 'cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png',
    'fig:80_components': 'historical_component_80month.png',
    'fig:synth2': 'reference_synthesis_univariate.png',
}

APPENDIX_PANEL_FILENAMES = {
    '20210123_exal_m_t1': 'cutoff_2021_01_23_setup_support.png',
    '20211112_exal_m_t1': 'cutoff_2021_11_12_setup_support.png',
    '20211221_exal_m_t1': 'cutoff_2021_12_21_setup_support.png',
    '20220511_exal_m_t1': 'cutoff_2022_05_11_setup_support.png',
    '20221225_exal_m_t1': 'cutoff_2022_12_25_setup_support.png',
}

CUTOFF_FORECAST_CONTEXT_FILENAMES = {
    '20210123_exal_m_t1': 'cutoff_2021_01_23_forecast_context.png',
    '20211112_exal_m_t1': 'cutoff_2021_11_12_forecast_context.png',
    '20211221_exal_m_t1': 'cutoff_2021_12_21_forecast_context.png',
    '20220511_exal_m_t1': 'cutoff_2022_05_11_forecast_context.png',
    '20221225_exal_m_t1': 'cutoff_2022_12_25_forecast_context.png',
}

CUTOFF_MULTIVARIATE_SYNTHESIS_FILENAMES = {
    '20210123_exal_m_t1': 'cutoff_2021_01_23_multivariate_synthesis.png',
    '20211112_exal_m_t1': 'cutoff_2021_11_12_multivariate_synthesis.png',
    '20211221_exal_m_t1': 'cutoff_2021_12_21_multivariate_synthesis.png',
    '20220511_exal_m_t1': 'cutoff_2022_05_11_multivariate_synthesis.png',
    '20221225_exal_m_t1': 'cutoff_2022_12_25_multivariate_synthesis.png',
}

CUTOFF_MULTIVARIATE_SYNTHESIS_OVERLAY_FILENAMES = {
    '20210123_exal_m_t1': 'cutoff_2021_01_23_multivariate_synthesis_with_reference_ensembles.png',
    '20211112_exal_m_t1': 'cutoff_2021_11_12_multivariate_synthesis_with_reference_ensembles.png',
    '20211221_exal_m_t1': 'cutoff_2021_12_21_multivariate_synthesis_with_reference_ensembles.png',
    '20220511_exal_m_t1': 'cutoff_2022_05_11_multivariate_synthesis_with_reference_ensembles.png',
    '20221225_exal_m_t1': 'cutoff_2022_12_25_multivariate_synthesis_with_reference_ensembles.png',
}

CUTOFF_REFERENCE_SYNTHESIS_FILENAMES = {
    '20210123_exal_m_t1': 'cutoff_2021_01_23_reference_synthesis.png',
    '20211112_exal_m_t1': 'cutoff_2021_11_12_reference_synthesis.png',
    '20211221_exal_m_t1': 'cutoff_2021_12_21_reference_synthesis.png',
    '20220511_exal_m_t1': 'cutoff_2022_05_11_reference_synthesis.png',
    '20221225_exal_m_t1': 'cutoff_2022_12_25_reference_synthesis.png',
}

CUTOFF_REFERENCE_SYNTHESIS_OVERLAY_FILENAMES = {
    '20210123_exal_m_t1': 'cutoff_2021_01_23_reference_synthesis_with_reference_ensembles.png',
    '20211112_exal_m_t1': 'cutoff_2021_11_12_reference_synthesis_with_reference_ensembles.png',
    '20211221_exal_m_t1': 'cutoff_2021_12_21_reference_synthesis_with_reference_ensembles.png',
    '20220511_exal_m_t1': 'cutoff_2022_05_11_reference_synthesis_with_reference_ensembles.png',
    '20221225_exal_m_t1': 'cutoff_2022_12_25_reference_synthesis_with_reference_ensembles.png',
}

TABLE_TEX_FILENAMES = {
    'benchmark_rows': 'benchmark_crps_raw_rows.tex',
    'benchmark_bayesian_rows': 'benchmark_crps_bayesian_rows.tex',
    'benchmark_body': 'benchmark_crps_body.tex',
    'benchmark_block': 'benchmark_crps_main_table.tex',
    'benchmark_nws_horizon_raw_rows': 'benchmark_crps_nws_horizon_raw_rows.tex',
    'benchmark_nws_horizon_bayesian_rows': 'benchmark_crps_nws_horizon_bayesian_rows.tex',
    'benchmark_nws_horizon_body': 'benchmark_crps_nws_horizon_body.tex',
    'benchmark_nws_horizon_block': 'benchmark_crps_nws_horizon_table.tex',
    'components_rows': 'representative_covariate_effects_rows.tex',
    'components_block': 'representative_covariate_effects_table.tex',
    'gamma_rows': 'appendix_gamma_rows.tex',
    'gamma_block': 'appendix_gamma_summary_table.tex',
    'sigma_rows': 'appendix_sigma_rows.tex',
    'sigma_block': 'appendix_sigma_summary_table.tex',
    'he4_rows': 'he4_quantile_check_loss_rows.tex',
    'he4_block': 'he4_quantile_check_loss_main_table.tex',
    'he3_ablation_body': 'he3_ablation_crps_body.tex',
    'he3_ablation_block': 'he3_ablation_crps_main_table.tex',
    'he3_ablation_nws_horizon_body': 'he3_ablation_crps_nws_horizon_body.tex',
    'he3_ablation_nws_horizon_block': 'he3_ablation_crps_nws_horizon_table.tex',
}


@dataclass(frozen=True)
class ArticleRepoLayout:
    root: Path

    @property
    def manifest_path(self) -> Path:
        return self.root / MANIFEST_FILENAME

    @property
    def figures_dir(self) -> Path:
        return self.root / 'Figures'

    @property
    def publication_figures_dir(self) -> Path:
        return self.root / 'Figures'

    @property
    def manuscript_figures_dir(self) -> Path:
        return self.figures_dir / 'manuscript'

    @property
    def appendix_cutoff_panels_dir(self) -> Path:
        return self.publication_figures_dir / 'appendix_cutoff_panels'

    @property
    def cutoff_forecast_context_dir(self) -> Path:
        return self.publication_figures_dir / 'forecast_context_by_cutoff'

    @property
    def cutoff_multivariate_synthesis_dir(self) -> Path:
        return self.publication_figures_dir / 'multivariate_synthesis_by_cutoff'

    @property
    def cutoff_reference_synthesis_dir(self) -> Path:
        return self.publication_figures_dir / 'reference_synthesis_by_cutoff'

    @property
    def tables_dir(self) -> Path:
        return self.root / 'tables'

    @property
    def generated_tex_dir(self) -> Path:
        return self.tables_dir / 'generated_tex'

    @property
    def artifacts_dir(self) -> Path:
        return self.root / 'artifacts'

    @property
    def representative_selected_model_dir(self) -> Path:
        return self.artifacts_dir / 'representative_selected_model_2022_12_25'

    @property
    def five_cutoff_crps_validation_dir(self) -> Path:
        return self.artifacts_dir / 'five_cutoff_crps_validation_sources'

    @property
    def historical_support_dir(self) -> Path:
        return self.artifacts_dir / 'historical_support_from_current_models'

    @property
    def five_cutoff_setup_support_dir(self) -> Path:
        return self.artifacts_dir / 'five_cutoff_setup_support'

    @property
    def five_cutoff_main_model_synthesis_dir(self) -> Path:
        return self.artifacts_dir / 'five_cutoff_main_model_synthesis'

    @property
    def five_cutoff_reference_synthesis_dir(self) -> Path:
        return self.artifacts_dir / 'five_cutoff_reference_synthesis'

    @property
    def he2_publication_freeze_dir(self) -> Path:
        return self.artifacts_dir / 'he2_publication_freeze'

    @property
    def he2_historical_support_audit_dir(self) -> Path:
        return self.artifacts_dir / 'he2_historical_support_audit'

    @property
    def reports_dir(self) -> Path:
        return self.root / 'reports'

    @property
    def manuscript_asset_review_dir(self) -> Path:
        return self.reports_dir / 'manuscript_asset_review'

    @property
    def manuscript_figure_selection_dir(self) -> Path:
        return self.reports_dir / 'manuscript_figure_selection'

    @property
    def five_cutoff_setup_support_review_dir(self) -> Path:
        return self.reports_dir / 'five_cutoff_setup_support_review'

    @property
    def five_cutoff_synthesis_review_dir(self) -> Path:
        return self.reports_dir / 'five_cutoff_synthesis_review'

    @property
    def representative_setup_selection_dir(self) -> Path:
        return self.reports_dir / 'representative_setup_selection'

    @property
    def docs_dir(self) -> Path:
        return self.root / 'docs'

    @property
    def figure_table_provenance_doc(self) -> Path:
        return self.docs_dir / 'figure_table_provenance.md'

    @property
    def artifact_run_map_doc(self) -> Path:
        return self.docs_dir / 'exal_m_t1_artifact_run_map.md'

    @property
    def repository_structure_doc(self) -> Path:
        return self.docs_dir / 'article_repository_structure.md'

    def manuscript_figure_path(self, label: str) -> Path:
        if label == 'fig:synth1':
            return self.cutoff_multivariate_synthesis_overlay_path('20221225_exal_m_t1')
        return self.manuscript_figures_dir / MANUSCRIPT_FIGURE_FILENAMES[label]

    def appendix_panel_path(self, slug: str) -> Path:
        return self.appendix_cutoff_panels_dir / APPENDIX_PANEL_FILENAMES[slug]

    def cutoff_forecast_context_path(self, slug: str) -> Path:
        return self.cutoff_forecast_context_dir / CUTOFF_FORECAST_CONTEXT_FILENAMES[slug]

    def cutoff_multivariate_synthesis_path(self, slug: str) -> Path:
        return self.cutoff_multivariate_synthesis_dir / CUTOFF_MULTIVARIATE_SYNTHESIS_FILENAMES[slug]

    def cutoff_multivariate_synthesis_overlay_path(self, slug: str) -> Path:
        return self.cutoff_multivariate_synthesis_dir / CUTOFF_MULTIVARIATE_SYNTHESIS_OVERLAY_FILENAMES[slug]

    def cutoff_reference_synthesis_path(self, slug: str) -> Path:
        return self.cutoff_reference_synthesis_dir / CUTOFF_REFERENCE_SYNTHESIS_FILENAMES[slug]

    def cutoff_reference_synthesis_overlay_path(self, slug: str) -> Path:
        return self.cutoff_reference_synthesis_dir / CUTOFF_REFERENCE_SYNTHESIS_OVERLAY_FILENAMES[slug]

    def ensure_base_dirs(self) -> None:
        for path in [
            self.figures_dir,
            self.manuscript_figures_dir,
            self.appendix_cutoff_panels_dir,
            self.cutoff_forecast_context_dir,
            self.cutoff_multivariate_synthesis_dir,
            self.cutoff_reference_synthesis_dir,
            self.tables_dir,
            self.generated_tex_dir,
            self.artifacts_dir,
            self.representative_selected_model_dir,
            self.five_cutoff_crps_validation_dir,
            self.historical_support_dir,
            self.five_cutoff_setup_support_dir,
            self.five_cutoff_main_model_synthesis_dir,
            self.five_cutoff_reference_synthesis_dir,
            self.he2_publication_freeze_dir,
            self.he2_historical_support_audit_dir,
            self.reports_dir,
            self.manuscript_asset_review_dir,
            self.manuscript_figure_selection_dir,
            self.five_cutoff_setup_support_review_dir,
            self.five_cutoff_synthesis_review_dir,
            self.representative_setup_selection_dir,
            self.docs_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


def build_layout(article_root: Path) -> ArticleRepoLayout:
    return ArticleRepoLayout(article_root.resolve())
