#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(values) {
  out <- list()
  i <- 1L
  while (i <= length(values)) {
    key <- values[[i]]
    if (!startsWith(key, "--")) stop(sprintf("Unexpected argument: %s", key), call. = FALSE)
    if (i == length(values)) stop(sprintf("Missing value for argument: %s", key), call. = FALSE)
    out[[substring(key, 3L)]] <- values[[i + 1L]]
    i <- i + 2L
  }
  out
}

opt <- parse_args(args)
required <- c("support-dir", "output-dir")
missing <- required[!vapply(required, function(k) !is.null(opt[[k]]) && nzchar(opt[[k]]), logical(1))]
if (length(missing) > 0L) {
  stop(sprintf("Missing required args: %s", paste(missing, collapse = ", ")), call. = FALSE)
}

support_dir <- normalizePath(opt[["support-dir"]], mustWork = TRUE)
out_dir <- normalizePath(opt[["output-dir"]], mustWork = FALSE)
workflow_root <- opt[["workflow-root"]]
display_flow_scale <- opt[["display-flow-scale"]]
if (is.null(display_flow_scale) || !nzchar(display_flow_scale)) display_flow_scale <- "log1p_cms"
metadata_support_dir <- opt[["metadata-support-dir"]]
if (is.null(metadata_support_dir) || !nzchar(metadata_support_dir)) metadata_support_dir <- support_dir

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

if (!is.null(workflow_root) && nzchar(workflow_root)) {
  style_path <- file.path(normalizePath(workflow_root, mustWork = TRUE), "scripts", "figure_style_contract.R")
  if (file.exists(style_path)) source(style_path)
}

if (!exists("theme_manuscript_standard", mode = "function")) {
  theme_manuscript_standard <- function(...) ggplot2::theme_bw(base_size = 13)
}
if (!exists("figure_flow_axis_label", mode = "function")) {
  figure_flow_axis_label <- function(scale) scale
}
if (!exists("figure_flood_label_df", mode = "function")) {
  figure_transform_flow_fallback <- function(x_cms, plot_scale) {
    vals <- suppressWarnings(as.numeric(x_cms))
    if (identical(plot_scale, "raw_cms")) return(vals)
    if (identical(plot_scale, "log1p_cms")) return(log1p(vals))
    stop(sprintf("Unknown plot scale: %s", plot_scale), call. = FALSE)
  }
  figure_current_rating_stage_reference_df <- function(
    plot_scale = "log1p_cms",
    levels = c("major", "minor")
  ) {
    refs <- data.frame(
      reference_level = c("action_monitor", "minor", "moderate", "major"),
      label = c("Action reference", "Minor reference", "Moderate reference", "Major reference"),
      stage_ft = c(14.00, 16.50, 19.50, 21.76),
      discharge_cfs = c(4864.84, 7402.38, 11302.95, 14895.73),
      stringsAsFactors = FALSE
    )
    refs$discharge_cms <- refs$discharge_cfs * 0.028316846592
    order_key <- match(tolower(levels), refs$reference_level)
    order_key <- order_key[is.finite(order_key)]
    refs <- refs[order_key, , drop = FALSE]
    refs$y <- figure_transform_flow_fallback(refs$discharge_cms, plot_scale)
    refs
  }
  figure_flood_label_df <- function(plot_scale = "log1p_cms", values = numeric()) {
    if (!identical(plot_scale, "log1p_cms")) {
      return(data.frame())
    }
    out <- figure_current_rating_stage_reference_df(plot_scale = plot_scale)
    vals <- suppressWarnings(as.numeric(values))
    vals <- vals[is.finite(vals)]
    span <- suppressWarnings(diff(range(c(vals, out$y), na.rm = TRUE)))
    if (!is.finite(span) || span <= 0) span <- 1
    offset <- max(0.03 * span, 0.04)
    out$label_y <- out$y + c(offset, -offset)
    out
  }
}
if (!exists("figure_flood_stage_style", mode = "function")) {
  figure_flood_stage_style <- function() {
    list(
      line_color = "#6B7280",
      line_width = 0.65,
      line_type = "dashed",
      label_color = "#4A5568",
      label_size = 3.3,
      label_face = "italic"
    )
  }
}

suppressPackageStartupMessages({
  library(ggplot2)
})

read_support_manifest <- function(path) {
  manifest_path <- file.path(path, "authoritative_selected_support_manifest.json")
  if (!file.exists(manifest_path) || !requireNamespace("jsonlite", quietly = TRUE)) {
    return(list())
  }
  jsonlite::read_json(manifest_path, simplifyVector = FALSE)
}

first_nonempty <- function(...) {
  values <- list(...)
  for (value in values) {
    if (!is.null(value) && length(value) == 1L && !is.na(value) && nzchar(as.character(value))) {
      return(as.character(value))
    }
  }
  NA_character_
}

support_manifest <- read_support_manifest(support_dir)
source_support_generated_at_utc <- first_nonempty(
  support_manifest[["component_rebuild"]][["rebuilt_at_utc"]],
  support_manifest[["dynamics_rebuild"]][["rebuilt_at_utc"]],
  support_manifest[["generated_at_utc"]]
)

FIGURE_A1_COMPONENT <- 6L
FIGURE_A1_COMPONENT_CONTRACT <- "raw_state_component"
COMPONENT_6_PLUS_TREND_CONTRACT <- "component_6_plus_trend_component_1_samplewise"
COMPONENT_6_MINUS_TREND_CONTRACT <- "component_6_minus_trend_component_1_samplewise"
COMPONENT_ANALYSIS_LEGACY_EXCLUDED_CONTRACTS <- c(
  "component_6_shifted_by_posterior_mean_trend_component_1"
)

component_analysis_slug <- function(component, contract) {
  contract_slug <- gsub("[^A-Za-z0-9]+", "_", as.character(contract))
  contract_slug <- gsub("^_+|_+$", "", tolower(contract_slug))
  sprintf("component_%02d_%s.png", as.integer(component), contract_slug)
}

component_analysis_label <- function(component, contract) {
  component <- as.integer(component)
  contract <- as.character(contract)
  if (component == FIGURE_A1_COMPONENT && identical(contract, FIGURE_A1_COMPONENT_CONTRACT)) {
    return("Long-cycle seasonal component (about 82 months)")
  }
  if (identical(contract, COMPONENT_6_PLUS_TREND_CONTRACT)) {
    return("Component 6 plus trend component 1 (samplewise)")
  }
  if (identical(contract, COMPONENT_6_MINUS_TREND_CONTRACT)) {
    return("Component 6 minus trend component 1 (samplewise)")
  }
  if (identical(contract, "raw_state_component")) {
    return(sprintf("Raw state component %d", component))
  }
  sprintf("Component %d (%s)", component, contract)
}

component_analysis_specs <- function(component_df) {
  if (!is.data.frame(component_df) || nrow(component_df) == 0L) return(data.frame())
  required <- c("component", "component_contract")
  missing <- setdiff(required, names(component_df))
  if (length(missing) > 0L) return(data.frame())

  rows <- list()
  raw_components <- sort(unique(as.integer(component_df$component[component_df$component_contract == "raw_state_component"])))
  raw_components <- raw_components[is.finite(raw_components)]
  for (component in raw_components) {
    rows[[length(rows) + 1L]] <- data.frame(
      component = as.integer(component),
      component_contract = "raw_state_component",
      display_label = component_analysis_label(component, "raw_state_component"),
      filename = component_analysis_slug(component, "raw_state_component"),
      include_in_manuscript = FALSE,
      stringsAsFactors = FALSE
    )
  }

  has_plus_trend_contract <- any(
    component_df$component == 6L &
      component_df$component_contract == COMPONENT_6_PLUS_TREND_CONTRACT,
    na.rm = TRUE
  )
  if (isTRUE(has_plus_trend_contract)) {
    rows[[length(rows) + 1L]] <- data.frame(
      component = 6L,
      component_contract = COMPONENT_6_PLUS_TREND_CONTRACT,
      display_label = component_analysis_label(6L, COMPONENT_6_PLUS_TREND_CONTRACT),
      filename = component_analysis_slug(6L, COMPONENT_6_PLUS_TREND_CONTRACT),
      include_in_manuscript = FALSE,
      stringsAsFactors = FALSE
    )
  }

  has_minus_contract <- any(
    component_df$component == 6L &
      component_df$component_contract == COMPONENT_6_MINUS_TREND_CONTRACT,
    na.rm = TRUE
  )
  if (isTRUE(has_minus_contract)) {
    rows[[length(rows) + 1L]] <- data.frame(
      component = 6L,
      component_contract = COMPONENT_6_MINUS_TREND_CONTRACT,
      display_label = component_analysis_label(6L, COMPONENT_6_MINUS_TREND_CONTRACT),
      filename = component_analysis_slug(6L, COMPONENT_6_MINUS_TREND_CONTRACT),
      include_in_manuscript = FALSE,
      stringsAsFactors = FALSE
    )
  }

  if (length(rows) == 0L) return(data.frame())
  out <- do.call(rbind, rows)
  out <- out[!(out$component_contract %in% COMPONENT_ANALYSIS_LEGACY_EXCLUDED_CONTRACTS), , drop = FALSE]
  out
}

component_analysis_axis_label <- function(contract) {
  if (identical(as.character(contract), "raw_state_component")) {
    return(sprintf("State component (%s)", display_flow_scale))
  }
  figure_flow_axis_label(display_flow_scale)
}

hydrologic_regime_periods <- function() {
  data.frame(
    xmin = as.Date(c("2012-01-01", "2017-01-01")),
    xmax = as.Date(c("2016-12-31", "2019-12-31")),
    period = c("Dry", "Wet"),
    fill = c("#fff0b3", "#cfe8f7"),
    stringsAsFactors = FALSE
  )
}

dynamics_path <- file.path(support_dir, "authoritative_usgs_quantile_dynamics_summary.csv")
component_path <- file.path(support_dir, "authoritative_component_summary.csv")
if (!file.exists(dynamics_path)) stop(sprintf("Missing dynamics support CSV: %s", dynamics_path), call. = FALSE)
if (!file.exists(component_path)) stop(sprintf("Missing component support CSV: %s", component_path), call. = FALSE)

dynamics <- utils::read.csv(dynamics_path, stringsAsFactors = FALSE, check.names = FALSE)
components <- utils::read.csv(component_path, stringsAsFactors = FALSE, check.names = FALSE)
dynamics$date <- as.Date(dynamics$date)
components$date <- as.Date(components$date)

render_quantile_window <- function(start_date, end_date, title_text, out_file, ylim = c(0, 7)) {
  dd <- dynamics[
    dynamics$quantile %in% c("q05", "q50", "q95") &
      !is.na(dynamics$date) &
      dynamics$date >= as.Date(start_date) &
      dynamics$date <= as.Date(end_date),
    ,
    drop = FALSE
  ]
  if (nrow(dd) < 1L) stop(sprintf("No dynamics rows for %s to %s", start_date, end_date), call. = FALSE)
  obs <- dd[dd$quantile == "q50", c("date", "observed_usgs"), drop = FALSE]
  obs <- obs[is.finite(obs$observed_usgs), , drop = FALSE]
  col <- c(q05 = "#b2182b", q50 = "#238b45", q95 = "#2171b5")
  fill <- c(q05 = "#fdbba1", q50 = "#b2df8a", q95 = "#a6bddb")
  flood_df <- figure_flood_label_df(
    plot_scale = display_flow_scale,
    values = c(dd$lower_025, dd$upper_975, dd$median_500, obs$observed_usgs)
  )
  flood_style <- figure_flood_stage_style()
  p <- ggplot() +
    geom_ribbon(
      data = dd,
      aes(x = date, ymin = lower_025, ymax = upper_975, fill = quantile),
      alpha = 0.12
    ) +
    geom_line(
      data = dd,
      aes(x = date, y = median_500, color = quantile),
      linewidth = 0.45
    ) +
    geom_line(
      data = dd,
      aes(x = date, y = lower_025, color = quantile),
      linewidth = 0.12
    ) +
    geom_line(
      data = dd,
      aes(x = date, y = upper_975, color = quantile),
      linewidth = 0.12
    ) +
    geom_line(data = obs, aes(x = date, y = observed_usgs), color = "black", linewidth = 0.22) +
    geom_point(data = obs, aes(x = date, y = observed_usgs), color = "black", size = 0.35) +
    scale_color_manual(values = col, breaks = c("q05", "q50", "q95")) +
    scale_fill_manual(values = fill, breaks = c("q05", "q50", "q95")) +
    coord_cartesian(ylim = ylim) +
    scale_x_date(date_breaks = "1 year", date_labels = "%Y-%m") +
    labs(title = title_text, x = NULL, y = figure_flow_axis_label(display_flow_scale)) +
    theme_manuscript_standard(
      base_size = 14,
      title_size = 15,
      legend_position = "none",
      axis_text_y_size = 12,
      x_angle = 35,
      major_grid_x = TRUE,
      major_grid_y = TRUE,
      plot_margin = margin(12, 12, 12, 12)
    )
  if (!is.null(flood_df) && nrow(flood_df) > 0L) {
    p <- p +
      geom_hline(
        data = flood_df,
        aes(yintercept = y),
        linetype = flood_style$line_type,
        color = flood_style$line_color,
        linewidth = flood_style$line_width,
        alpha = 0.9
      ) +
      annotate(
        "text",
        x = as.Date(end_date),
        y = flood_df$label_y,
        label = flood_df$label,
        hjust = 1.02,
        vjust = 0.5,
        color = flood_style$label_color,
        fontface = flood_style$label_face,
        size = flood_style$label_size
      )
  }
  ggsave(out_file, plot = p, width = 12, height = 6, units = "in", dpi = 900)
}

render_component_80month <- function(out_file) {
  dd <- components[
    components$quantile %in% c("q05", "q50", "q95") &
    components$component == FIGURE_A1_COMPONENT &
      components$component_contract == FIGURE_A1_COMPONENT_CONTRACT &
      !is.na(components$date),
    ,
    drop = FALSE
  ]
  if (nrow(dd) < 1L) {
    stop(
      sprintf("No component-%d rows found for required contract `%s` in authoritative component summary.", FIGURE_A1_COMPONENT, FIGURE_A1_COMPONENT_CONTRACT),
      call. = FALSE
    )
  }
  min_time <- ceiling(max(dd$time_index, na.rm = TRUE) / 10)
  dd <- dd[dd$time_index >= min_time, , drop = FALSE]
  ylim <- range(c(dd$lower_025, dd$upper_975), na.rm = TRUE)
  if (!all(is.finite(ylim)) || diff(ylim) <= 0) ylim <- c(0, 1)
  ylim <- c(min(0, ylim[[1L]]), ylim[[2L]] + diff(ylim) * 0.08)
  shade_periods <- hydrologic_regime_periods()
  shade_periods <- shade_periods[shade_periods$xmax >= min(dd$date, na.rm = TRUE) & shade_periods$xmin <= max(dd$date, na.rm = TRUE), , drop = FALSE]
  shade_periods$xmin <- pmax(shade_periods$xmin, min(dd$date, na.rm = TRUE))
  shade_periods$xmax <- pmin(shade_periods$xmax, max(dd$date, na.rm = TRUE))
  label_y <- ylim[[1L]] + 0.035 * diff(ylim)
  col <- c(q05 = "#b2182b", q50 = "#238b45", q95 = "#2171b5")
  fill <- c(q05 = "#fdbba1", q50 = "#b2df8a", q95 = "#a6bddb")
  p <- ggplot() +
    geom_rect(
      data = shade_periods,
      aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf, fill = period),
      alpha = 0.48,
      inherit.aes = FALSE,
      show.legend = FALSE
    ) +
    geom_ribbon(
      data = dd,
      aes(x = date, ymin = lower_025, ymax = upper_975, fill = quantile),
      alpha = 0.12
    ) +
    geom_line(data = dd, aes(x = date, y = median_500, color = quantile), linewidth = 0.45) +
    geom_line(data = dd, aes(x = date, y = lower_025, color = quantile), linewidth = 0.12) +
    geom_line(data = dd, aes(x = date, y = upper_975, color = quantile), linewidth = 0.12) +
    scale_color_manual(values = col, breaks = c("q05", "q50", "q95")) +
    scale_fill_manual(values = c(fill, setNames(shade_periods$fill, shade_periods$period))) +
    annotate(
      "text",
      x = shade_periods$xmin + (shade_periods$xmax - shade_periods$xmin) / 2,
      y = label_y,
      label = shade_periods$period,
      size = 3.4,
      color = "#555555",
      fontface = "italic"
    ) +
    coord_cartesian(ylim = ylim) +
    scale_x_date(date_breaks = "24 months", date_labels = "%Y-%m") +
    labs(
      title = "Long-cycle seasonal component (about 82 months): selected 2022-12-25 model",
      x = NULL,
      y = component_analysis_axis_label(FIGURE_A1_COMPONENT_CONTRACT)
    ) +
    theme_manuscript_standard(
      base_size = 15,
      title_size = 16,
      legend_position = "none",
      axis_text_y_size = 12,
      x_angle = 35,
      major_grid_x = TRUE,
      major_grid_y = TRUE,
      plot_margin = margin(12, 12, 12, 12)
    )
  ggsave(out_file, plot = p, width = 12, height = 6, units = "in", dpi = 350)
}

render_component_analysis_figure <- function(spec, out_file) {
  dd <- components[
    components$quantile %in% c("q05", "q50", "q95") &
      components$component == spec$component[[1L]] &
      components$component_contract == spec$component_contract[[1L]] &
      !is.na(components$date),
    ,
    drop = FALSE
  ]
  if (nrow(dd) < 1L) {
    stop(sprintf("No component rows found for analysis figure `%s`.", spec$display_label[[1L]]), call. = FALSE)
  }
  min_time <- ceiling(max(dd$time_index, na.rm = TRUE) / 10)
  dd <- dd[dd$time_index >= min_time, , drop = FALSE]
  if (nrow(dd) < 1L) {
    stop(sprintf("No component rows remain after warm-history trim for `%s`.", spec$display_label[[1L]]), call. = FALSE)
  }

  obs <- dynamics[dynamics$quantile == "q50", c("date", "observed_usgs"), drop = FALSE]
  obs <- obs[!is.na(obs$date) & is.finite(obs$observed_usgs), , drop = FALSE]
  obs <- obs[obs$date >= min(dd$date, na.rm = TRUE) & obs$date <= max(dd$date, na.rm = TRUE), , drop = FALSE]

  ylim <- range(c(dd$lower_025, dd$upper_975, obs$observed_usgs), na.rm = TRUE)
  if (!all(is.finite(ylim)) || diff(ylim) <= 0) ylim <- c(0, 1)
  ylim <- c(min(0, ylim[[1L]]), ylim[[2L]] + diff(ylim) * 0.08)

  shade_periods <- hydrologic_regime_periods()
  shade_periods <- shade_periods[shade_periods$xmax >= min(dd$date, na.rm = TRUE) & shade_periods$xmin <= max(dd$date, na.rm = TRUE), , drop = FALSE]
  shade_periods$xmin <- pmax(shade_periods$xmin, min(dd$date, na.rm = TRUE))
  shade_periods$xmax <- pmin(shade_periods$xmax, max(dd$date, na.rm = TRUE))
  label_y <- ylim[[1L]] + 0.035 * diff(ylim)
  col <- c(q05 = "#b2182b", q50 = "#238b45", q95 = "#2171b5")
  fill <- c(q05 = "#fdbba1", q50 = "#b2df8a", q95 = "#a6bddb")
  p <- ggplot() +
    geom_rect(
      data = shade_periods,
      aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf, fill = period),
      alpha = 0.48,
      inherit.aes = FALSE,
      show.legend = FALSE
    ) +
    geom_ribbon(
      data = dd,
      aes(x = date, ymin = lower_025, ymax = upper_975, fill = quantile),
      alpha = 0.12
    ) +
    geom_line(data = dd, aes(x = date, y = median_500, color = quantile), linewidth = 0.45) +
    geom_line(data = dd, aes(x = date, y = lower_025, color = quantile), linewidth = 0.12) +
    geom_line(data = dd, aes(x = date, y = upper_975, color = quantile), linewidth = 0.12) +
    geom_line(data = obs, aes(x = date, y = observed_usgs), color = "black", linewidth = 0.12) +
    geom_point(data = obs, aes(x = date, y = observed_usgs), color = "black", size = 0.1, alpha = 0.9) +
    scale_color_manual(values = col, breaks = c("q05", "q50", "q95")) +
    scale_fill_manual(values = c(fill, setNames(shade_periods$fill, shade_periods$period))) +
    annotate(
      "text",
      x = shade_periods$xmin + (shade_periods$xmax - shade_periods$xmin) / 2,
      y = label_y,
      label = shade_periods$period,
      size = 3.4,
      color = "#555555",
      fontface = "italic"
    ) +
    coord_cartesian(ylim = ylim) +
    scale_x_date(date_breaks = "24 months", date_labels = "%Y-%m") +
    labs(
      title = sprintf("%s: selected 2022-12-25 model", spec$display_label[[1L]]),
      x = NULL,
      y = component_analysis_axis_label(spec$component_contract[[1L]])
    ) +
    theme_manuscript_standard(
      base_size = 15,
      title_size = 16,
      legend_position = "none",
      axis_text_y_size = 12,
      x_angle = 35,
      major_grid_x = TRUE,
      major_grid_y = TRUE,
      plot_margin = margin(12, 12, 12, 12)
    )
  ggsave(out_file, plot = p, width = 12, height = 6, units = "in", dpi = 350)
  invisible(TRUE)
}

write_component_analysis_readme <- function(analysis_dir, manifest) {
  writeLines(
    c(
      "# Component Evolution Analysis Gallery",
      "",
      "These PNG files are rendered from the same compact authoritative selected-model support bundle as Figure A1.",
      "They are analysis-only diagnostics and are intentionally not added to `MANUSCRIPT_ASSET_MANIFEST.json`.",
      "",
      "Included contracts:",
      "",
      sprintf("- `raw_state_component` for each retained state component available in the support CSV; component %d is the audited Figure A1 construction.", FIGURE_A1_COMPONENT),
      sprintf("- `%s`, the samplewise long-cycle component plus trend diagnostic.", COMPONENT_6_PLUS_TREND_CONTRACT),
      sprintf("- `%s`, the samplewise long-cycle component minus trend diagnostic.", COMPONENT_6_MINUS_TREND_CONTRACT),
      "",
      "Excluded by default:",
      "",
      "- `component_6_shifted_by_posterior_mean_trend_component_1`, the older shifted diagnostic contract.",
      "",
      sprintf("Rendered figures: %d", as.integer(nrow(manifest)))
    ),
    con = file.path(analysis_dir, "README.md")
  )
}

render_component_analysis_gallery <- function(analysis_dir) {
  dir.create(analysis_dir, recursive = TRUE, showWarnings = FALSE)
  specs <- component_analysis_specs(components)
  if (!is.data.frame(specs) || nrow(specs) == 0L) {
    stop("No component analysis figure specifications were available.", call. = FALSE)
  }

  rows <- list()
  for (i in seq_len(nrow(specs))) {
    spec <- specs[i, , drop = FALSE]
    out_file <- file.path(analysis_dir, spec$filename[[1L]])
    render_component_analysis_figure(spec, out_file)
    rows[[length(rows) + 1L]] <- data.frame(
      component = as.integer(spec$component[[1L]]),
      component_contract = spec$component_contract[[1L]],
      display_label = spec$display_label[[1L]],
      filename = spec$filename[[1L]],
      relative_path = file.path("analysis_figures", "component_evolution", spec$filename[[1L]]),
      include_in_manuscript = FALSE,
      source_support_generated_at_utc = source_support_generated_at_utc,
      stringsAsFactors = FALSE
    )
  }
  manifest <- do.call(rbind, rows)
  utils::write.csv(manifest, file.path(analysis_dir, "component_analysis_manifest.csv"), row.names = FALSE)
  write_component_analysis_readme(analysis_dir, manifest)
  manifest
}

render_quantile_window(
  "2012-01-01",
  "2016-12-31",
  "Selected-model Quantile Dynamics: 2012-2016",
  file.path(out_dir, "selected_model_quantile_dry_period.png"),
  ylim = c(0, 7)
)
render_quantile_window(
  "2017-01-01",
  "2019-12-31",
  "Selected-model Quantile Dynamics: 2017-2019",
  file.path(out_dir, "selected_model_quantile_wet_period.png"),
  ylim = c(0, 7)
)
render_component_80month(file.path(out_dir, "selected_model_component_80month.png"))
analysis_dir <- file.path(dirname(out_dir), "analysis_figures", "component_evolution")
component_analysis_manifest <- render_component_analysis_gallery(analysis_dir)

meta <- list(
  support_dir = metadata_support_dir,
  output_dir = out_dir,
  display_flow_scale = display_flow_scale,
  render_contract_version = "authoritative_selected_model_support_figures_v2",
  source_support_generated_at_utc = source_support_generated_at_utc,
  figure_a1_component = FIGURE_A1_COMPONENT,
  figure_a1_component_contract = FIGURE_A1_COMPONENT_CONTRACT,
  figure_a1_article_display_label = "long-cycle seasonal component only (about 82 months)",
  hydrologic_regime_periods = lapply(seq_len(nrow(hydrologic_regime_periods())), function(i) {
    row <- hydrologic_regime_periods()[i, , drop = FALSE]
    list(
      period = row$period[[1L]],
      start = as.character(row$xmin[[1L]]),
      end = as.character(row$xmax[[1L]]),
      fill = row$fill[[1L]]
    )
  }),
  rendered_files = c(
    "selected_model_quantile_dry_period.png",
    "selected_model_quantile_wet_period.png",
    "selected_model_component_80month.png"
  ),
  component_analysis = list(
    directory = file.path("analysis_figures", "component_evolution"),
    manifest = file.path("analysis_figures", "component_evolution", "component_analysis_manifest.csv"),
    figure_count = as.integer(nrow(component_analysis_manifest)),
    files = as.character(component_analysis_manifest$filename)
  )
)
if (requireNamespace("jsonlite", quietly = TRUE)) {
  jsonlite::write_json(meta, file.path(out_dir, "render_metadata.json"), auto_unbox = TRUE, pretty = TRUE)
}
message("Rendered authoritative selected-model support figures.")
