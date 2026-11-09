#!/usr/bin/env Rscript

parse_args <- function(argv) {
  out <- list()
  i <- 1L
  while (i <= length(argv)) {
    key <- argv[[i]]
    if (!startsWith(key, "--")) {
      i <- i + 1L
      next
    }
    key <- sub("^--", "", key)
    key <- gsub("-", "_", key, fixed = TRUE)
    if (i == length(argv) || startsWith(argv[[i + 1L]], "--")) {
      out[[key]] <- TRUE
      i <- i + 1L
    } else {
      out[[key]] <- argv[[i + 1L]]
      i <- i + 2L
    }
  }
  out
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
project_root <- normalizePath(getwd(), mustWork = FALSE)
source(file.path(project_root, "R", "unified", "post_publication_figures.R"))

outputs_dir <- args$outputs_dir %||% ""
model_id <- args$model_id %||% ""
if (!nzchar(outputs_dir) || !nzchar(model_id)) {
  stop("Provide --outputs-dir and --model-id", call. = FALSE)
}
outputs_dir <- normalizePath(outputs_dir, mustWork = TRUE)
style <- post_publication_load_style(project_root, args$style_config %||% file.path(project_root, "config", "post_publication_figures.yaml"))
style_snapshot_path <- post_publication_write_style_snapshot(outputs_dir, style)

quant_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_quantiles.csv", model_id))
sample_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_sample_subset.csv", model_id))
png_path <- file.path(outputs_dir, sprintf("%s_cutoff_window_posterior_samples.png", model_id))
pdf_path <- sub("\\.png$", ".pdf", png_path)
with_ens_png <- file.path(outputs_dir, sprintf("%s_cutoff_window_posterior_samples_with_raw_ensembles.png", model_id))
with_ens_pdf <- sub("\\.png$", ".pdf", with_ens_png)

quant_df <- post_publication_read_contract_csv(
  quant_path,
  required_cols = c("model_id", "date", "segment", "observed"),
  context = sprintf("quantiles contract for %s", model_id)
)
sample_df <- post_publication_read_contract_csv(
  sample_path,
  required_cols = c("model_id", "draw_id", "sample_index", "date", "segment", "value"),
  context = sprintf("sample subset contract for %s", model_id)
)

quant_focus <- post_publication_apply_exact_cache_interval(
  quant_df = quant_df,
  hist_cache_path = args$hist_cache,
  forecast_cache_path = args$forecast_cache,
  probs = c(0.025, 0.975),
  low_col = "interval_low",
  high_col = "interval_high"
)
quant_focus <- post_publication_apply_exact_cache_mean(
  quant_df = quant_focus,
  hist_cache_path = args$hist_cache,
  forecast_cache_path = args$forecast_cache,
  mean_col = "model_mean"
)

# Auditable numbers supplied to both display variants; no quantile CSV is rewritten.
post_publication_write_csv(quant_focus, file.path(outputs_dir, sprintf("%s_focus_render_numeric_contract.csv", model_id)))

manifest_path <- file.path(outputs_dir, "figure_manifest.csv")
manifest <- utils::read.csv(manifest_path, stringsAsFactors = FALSE, check.names = FALSE)
source_run <- if (any(manifest$model_id == model_id)) manifest$source_run[match(model_id, manifest$model_id)] else ""

post_publication_render_focus_posterior_plot(
  model_id = model_id,
  quant_df = quant_focus,
  sample_df = sample_df,
  png_path = png_path,
  pdf_path = pdf_path,
  style = style,
  source_run = source_run,
  interval_low_col = "interval_low",
  interval_high_col = "interval_high",
  interval_label = "Pointwise central 95% predictive interval",
  ensemble_df = NULL,
  retrospective_df = NULL
)

nws_df <- post_publication_read_member_forecasts(args$nws_path, "NWS/NWM")
glofas_df <- post_publication_read_member_forecasts(args$glofas_path, "GloFAS")
ensemble_df <- rbind(nws_df, glofas_df)
retrospective_df <- if (!is.null(args$retros_path) && nzchar(args$retros_path)) {
  post_publication_read_retrospectives(args$retros_path)
} else {
  post_root <- post_publication_find_post_root(outputs_dir)
  context_paths <- post_publication_resolve_context_input_paths(post_root)
  if (!is.null(context_paths$retros_path)) post_publication_read_retrospectives(context_paths$retros_path) else NULL
}
post_publication_render_focus_posterior_plot(
  model_id = model_id,
  quant_df = quant_focus,
  sample_df = sample_df,
  png_path = with_ens_png,
  pdf_path = with_ens_pdf,
  style = style,
  source_run = source_run,
  interval_low_col = "interval_low",
  interval_high_col = "interval_high",
  interval_label = "Pointwise central 95% predictive interval",
  ensemble_df = ensemble_df,
  retrospective_df = retrospective_df
)

add_rows <- rbind(
  post_publication_manifest_row(
    model_id = model_id,
    plot_type = "cutoff_window_posterior_samples_with_raw_ensembles",
    path = with_ens_png,
    source_run = source_run,
    note = sprintf("style=%s; exact_interval=95_from_cache; includes_adapter_scale_retrospectives_and_ensemble_references", style$version)
  ),
  post_publication_manifest_row(
    model_id = model_id,
    plot_type = "cutoff_window_posterior_samples_with_raw_ensembles_pdf",
    path = with_ens_pdf,
    source_run = source_run,
    note = sprintf("paired_with=cutoff_window_posterior_samples_with_raw_ensembles; style=%s", style$version)
  )
)
update_rows <- rbind(
  post_publication_manifest_row(
    model_id = model_id,
    plot_type = "cutoff_window_posterior_samples",
    path = png_path,
    source_run = source_run,
    note = sprintf("style=%s; exact_interval=95_from_cache; observed_split=fit_vs_heldout", style$version)
  )
)
invisible(post_publication_update_main_manifest(manifest_path, rows_to_add = add_rows, png_note_updates = update_rows))

pub_manifest_path <- file.path(outputs_dir, "publication_figure_manifest.csv")
pub_rows <- data.frame(
  model_id = c(model_id, model_id),
  source_plot_type = c("cutoff_window_posterior_samples_focus", "cutoff_window_posterior_samples_with_raw_ensembles"),
  canonical_png = c(normalizePath(png_path, mustWork = FALSE), normalizePath(with_ens_png, mustWork = FALSE)),
  pdf_path = c(normalizePath(pdf_path, mustWork = FALSE), normalizePath(with_ens_pdf, mustWork = FALSE)),
  quantiles_path = c(normalizePath(quant_path, mustWork = FALSE), normalizePath(quant_path, mustWork = FALSE)),
  sample_subset_path = c(normalizePath(sample_path, mustWork = FALSE), normalizePath(sample_path, mustWork = FALSE)),
  style_version = rep(style$version, 2L),
  style_source_path = c(style$style_source_path, style$style_source_path),
  style_snapshot_path = c(style_snapshot_path, style_snapshot_path),
  rewritten_canonical_png = c(TRUE, FALSE),
  rendered_at_utc = c(post_publication_iso_utc(), post_publication_iso_utc()),
  source_run = c(source_run, source_run),
  stringsAsFactors = FALSE
)
if (file.exists(pub_manifest_path)) {
  current_pub <- utils::read.csv(pub_manifest_path, stringsAsFactors = FALSE, check.names = FALSE)
  pub_rows <- post_publication_merge_manifest_rows(current_pub, pub_rows)
}
invisible(post_publication_write_csv(pub_rows, pub_manifest_path))

cat(sprintf("WROTE canonical=%s\n", png_path))
cat(sprintf("WROTE overlay=%s\n", with_ens_png))
