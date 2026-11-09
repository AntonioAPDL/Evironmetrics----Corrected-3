#!/usr/bin/env Rscript
# Render the retained long-cycle summary with one reader-facing axis label.
# The plotting layers and style reproduce render_component_80month in
# render_authoritative_selected_model_support_figures.R. No fitted object is read.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Usage: render_editorial_long_cycle_figure.R INPUT.csv.gz OUTPUT_DIR")
input <- args[[1L]]
out_dir <- args[[2L]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
suppressPackageStartupMessages(library(ggplot2))
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is required")

# Exact style used for the original component panel; self-contained for replay.
theme_manuscript_standard <- function(
  base_size = 14, title_size = 16, subtitle_size = NULL,
  legend_position = "none", axis_text_size = 11,
  axis_text_y_size = axis_text_size, x_angle = 0,
  x_hjust = if (x_angle == 0) 0.5 else 1,
  x_vjust = if (x_angle == 0) 0.5 else 1,
  strip_text_size = NULL, major_grid_x = NULL, major_grid_y = NULL,
  plot_margin = NULL
) {
  th <- theme_minimal(base_size = base_size) + theme(
    plot.title = element_text(size = title_size, face = "bold", hjust = 0.5, margin = margin(b = 8)),
    axis.title = element_text(face = "bold"),
    axis.text = element_text(size = axis_text_size),
    axis.text.y = element_text(size = axis_text_y_size),
    axis.text.x = element_text(size = axis_text_size, angle = x_angle, hjust = x_hjust, vjust = x_vjust),
    panel.grid.minor = element_blank(), legend.position = legend_position
  )
  if (!is.null(subtitle_size)) th <- th + theme(plot.subtitle = element_text(size = subtitle_size, face = "italic", hjust = 0.5))
  if (!is.null(strip_text_size)) th <- th + theme(strip.text = element_text(size = strip_text_size, face = "bold", color = "black"), strip.background = element_blank())
  if (!is.null(major_grid_x)) th <- th + theme(panel.grid.major.x = if (isTRUE(major_grid_x)) element_line(linewidth = 0.3, color = "#e5e5e5") else element_blank())
  if (!is.null(major_grid_y)) th <- th + theme(panel.grid.major.y = if (isTRUE(major_grid_y)) element_line(linewidth = 0.4, color = "#e5e5e5") else element_blank())
  if (!is.null(plot_margin)) th <- th + theme(plot.margin = plot_margin)
  th
}

dd <- utils::read.csv(gzfile(input), stringsAsFactors = FALSE, check.names = FALSE)
dd$date <- as.Date(dd$date)
stopifnot(nrow(dd) > 0L, all(dd$component == 6L),
  all(dd$component_contract == "raw_state_component"),
  all(dd$quantile %in% c("q05", "q50", "q95")), !anyNA(dd$date),
  all(is.finite(dd$lower_025)), all(is.finite(dd$median_500)), all(is.finite(dd$upper_975)))
ylim <- range(c(dd$lower_025, dd$upper_975), na.rm = TRUE)
if (!all(is.finite(ylim)) || diff(ylim) <= 0) ylim <- c(0, 1)
ylim <- c(min(0, ylim[[1L]]), ylim[[2L]] + diff(ylim) * 0.08)
shade_periods <- data.frame(
  xmin = as.Date(c("2012-01-01", "2017-01-01")),
  xmax = as.Date(c("2016-12-31", "2019-12-31")),
  period = c("Dry", "Wet"), fill = c("#fff0b3", "#cfe8f7"),
  stringsAsFactors = FALSE
)
shade_periods <- shade_periods[shade_periods$xmax >= min(dd$date) & shade_periods$xmin <= max(dd$date), , drop = FALSE]
shade_periods$xmin <- pmax(shade_periods$xmin, min(dd$date))
shade_periods$xmax <- pmin(shade_periods$xmax, max(dd$date))
label_y <- ylim[[1L]] + 0.035 * diff(ylim)
col <- c(q05 = "#b2182b", q50 = "#238b45", q95 = "#2171b5")
fill <- c(q05 = "#fdbba1", q50 = "#b2df8a", q95 = "#a6bddb")
make_plot <- function(axis_label) {
  ggplot() +
    geom_rect(data = shade_periods, aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf, fill = period), alpha = 0.48, inherit.aes = FALSE, show.legend = FALSE) +
    geom_ribbon(data = dd, aes(x = date, ymin = lower_025, ymax = upper_975, fill = quantile), alpha = 0.12) +
    geom_line(data = dd, aes(x = date, y = median_500, color = quantile), linewidth = 0.45) +
    geom_line(data = dd, aes(x = date, y = lower_025, color = quantile), linewidth = 0.12) +
    geom_line(data = dd, aes(x = date, y = upper_975, color = quantile), linewidth = 0.12) +
    scale_color_manual(values = col, breaks = c("q05", "q50", "q95")) +
    scale_fill_manual(values = c(fill, setNames(shade_periods$fill, shade_periods$period))) +
    annotate("text", x = shade_periods$xmin + (shade_periods$xmax - shade_periods$xmin) / 2, y = label_y, label = shade_periods$period, size = 3.4, color = "#555555", fontface = "italic") +
    coord_cartesian(ylim = ylim) +
    scale_x_date(date_breaks = "24 months", date_labels = "%Y-%m") +
    labs(title = sprintf("Long-cycle seasonal component (about %.2f years)", 363.5854 * 6.8068493 / 365.2425), x = NULL, y = axis_label) +
    theme_manuscript_standard(base_size = 15, title_size = 16, legend_position = "none", axis_text_y_size = 12, x_angle = 35, major_grid_x = TRUE, major_grid_y = TRUE, plot_margin = margin(12, 12, 12, 12))
}
old <- make_plot("State component (log1p_cms)")
new <- make_plot("Long-cycle component on log(1+discharge) scale")
old_build <- ggplot_build(old)
new_build <- ggplot_build(new)
panel_snapshot <- function(build) {
  lapply(build$layout$panel_params, function(panel) list(
    x_range = panel$x.range, y_range = panel$y.range,
    x_limits = panel$x$limits, y_limits = panel$y$limits,
    x_breaks = panel$x$breaks, y_breaks = panel$y$breaks,
    x_minor_breaks = panel$x$minor_breaks, y_minor_breaks = panel$y$minor_breaks,
    x_tick_labels = panel$x$get_labels(), y_tick_labels = panel$y$get_labels()
  ))
}
stopifnot(identical(old_build$data, new_build$data),
  identical(panel_snapshot(old_build), panel_snapshot(new_build)),
  identical(old$theme, new$theme), identical(old$coordinates$limits, new$coordinates$limits))
ggsave(file.path(out_dir, "original_annotation_replay.png"), plot = old, width = 12, height = 6, units = "in", dpi = 350)
ggsave(file.path(out_dir, "editorial_long_cycle_component.png"), plot = new, width = 12, height = 6, units = "in", dpi = 350)
report <- list(
  rows = nrow(dd), rows_per_layer = vapply(new_build$data, nrow, integer(1)),
  identical_plotted_layer_data = TRUE, identical_panel_parameters = TRUE,
  identical_style = TRUE, identical_coordinate_limits = TRUE,
  coordinate_ylim = ylim, date_range = as.character(range(dd$date)),
  component = 6, component_contract = "raw_state_component",
  annotation_before = old$labels$y, annotation_after = new$labels$y,
  R_version = R.version.string,
  ggplot2_version = as.character(packageVersion("ggplot2")),
  jsonlite_version = as.character(packageVersion("jsonlite"))
)
jsonlite::write_json(report, file.path(out_dir, "render_verification.json"), pretty = TRUE, auto_unbox = TRUE, digits = 17)
