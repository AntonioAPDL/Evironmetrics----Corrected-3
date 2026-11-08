#!/usr/bin/env Rscript

# Plot forecats figure from a self-contained bundle directory.
#
# Expected bundle layout:
#   <bundle_dir>/
#     meta.yaml
#     inputs/
#       usgs_daily.csv
#       retros_daily.csv
#       glofas_weighted_daily.csv
#       nws_weighted_daily.csv
#     figures/
#       forecats.png   (created)
#
# Input storage scales may be declared in meta.yaml under `storage_scales`.
# If omitted, all inputs default to raw cms (m^3/s).

suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
})

if (!exists("%||%", mode = "function")) {
  `%||%` <- function(x, y) {
    if (is.null(x) || length(x) == 0L) y else x
  }
}

if (!exists("figure_flow_axis_label", mode = "function") ||
    !exists("figure_date_label_format", mode = "function") ||
    !exists("theme_manuscript_standard", mode = "function") ||
    !exists("figure_product_palette", mode = "function") ||
    !exists("figure_default_retro_label", mode = "function") ||
    !exists("figure_retro_color_map", mode = "function") ||
    !exists("figure_retro_shape_map", mode = "function")) {
  project_root_env <- Sys.getenv("ENV_PROJECT_ROOT", unset = "")
  helper_path <- if (nzchar(project_root_env)) file.path(project_root_env, "scripts", "figure_style_contract.R") else NA_character_
  if (is.character(helper_path) && length(helper_path) == 1L && !is.na(helper_path) && file.exists(helper_path)) {
    source(helper_path, local = .GlobalEnv)
  }
}

if (!exists("figure_flow_axis_label", mode = "function")) {
  figure_flow_axis_label <- function(plot_scale) {
    switch(
      as.character(plot_scale %||% "log1p_cms"),
      raw_cms = bquote(River~flow~"["*m^3~s^-1*"]"),
      log1p_cms = bquote(River~flow~"["*log(1 + x)*";"~~x~"in"~~m^3~s^-1*"]"),
      log_log1p_cms = stop("log_log1p_cms is not allowed for current forecats plots; use log1p_cms.", call. = FALSE),
      as.character(plot_scale)
    )
  }
}
if (!exists("figure_date_label_format", mode = "function")) {
  figure_date_label_format <- function(dates) {
    date_vals <- as.Date(dates)
    span_days <- suppressWarnings(as.numeric(max(date_vals, na.rm = TRUE) - min(date_vals, na.rm = TRUE)))
    if (!is.finite(span_days)) {
      return("%Y-%m-%d")
    }
    if (span_days > 3650) return("%Y")
    if (span_days > 730) return("%Y-%m")
    "%Y-%m-%d"
  }
}
if (!exists("theme_manuscript_standard", mode = "function")) {
  theme_manuscript_standard <- function(base_size = 14, title_size = 16, legend_position = "bottom") {
    theme_minimal(base_size = base_size) +
      theme(
        plot.title = element_text(size = title_size, face = "bold", hjust = 0.5, margin = margin(b = 8)),
        axis.title = element_text(face = "bold"),
        axis.text = element_text(size = 11),
        panel.grid.minor = element_blank(),
        legend.position = legend_position
      )
  }
}
if (!exists("figure_product_palette", mode = "function")) {
  figure_product_palette <- function() {
    c(usgs = "#238b45", glofas = "#E67E22", nws = "#756bb1", usgs_future = "#B22222")
  }
}
if (!exists("figure_default_retro_label", mode = "function")) {
  figure_default_retro_label <- function(source_id, meta = NULL, cutoff_date = NULL, selected_run_root = NULL) {
    sid <- tolower(as.character(source_id %||% ""))
    switch(
      sid,
      nws_synth_retro_ens_mean = figure_selected_run_nws_label(cutoff_date),
      nws_retro_v12 = "NWS retrospective v1.2",
      nws_retro_v20 = "NWS retrospective v2.0",
      nws_retro_v21 = "NWS retrospective v2.1",
      nws_retro_v30 = "NWS retrospective v3.0",
      nws_selected_window_retro = figure_selected_run_nws_label(cutoff_date),
      glofas_hist_v21_htessel_cons = "GloFAS historical v2.1",
      glofas_hist_v31_lisflood_cons = "GloFAS historical v3.1",
      glofas_hist_v40_lisflood_cons = "GloFAS historical v4.0",
      glofas_legacy_reanalysis_v30 = "GloFAS legacy reanalysis v3.0",
      glofas_synth_retro_ens_mean = figure_glofas_version_label(cutoff_date),
      baseline_glofas = "GloFAS historical baseline",
      baseline_nws = "NWS retrospective baseline",
      sid
    )
  }
}
if (!exists("figure_retro_color_map", mode = "function")) {
  figure_retro_color_map <- function(labels) {
    labels <- unique(as.character(labels))
    palette <- figure_product_palette()
    out <- setNames(rep("#4d4d4d", length(labels)), labels)
    out[grepl("^GloFAS", labels)] <- palette[["glofas"]]
    out[grepl("^NWS", labels)] <- palette[["nws"]]
    out[grepl("^USGS", labels)] <- palette[["usgs"]]
    out
  }
}
if (!exists("figure_retro_shape_map", mode = "function")) {
  figure_retro_shape_map <- function(labels) {
    labels <- unique(as.character(labels))
    out <- setNames(rep(16L, length(labels)), labels)
    out
  }
}

parse_args <- function(argv) {
  out <- list()
  i <- 1
  while (i <= length(argv)) {
    a <- argv[[i]]
    if (startsWith(a, "--")) {
      key <- sub("^--", "", a)
      if (i == length(argv) || startsWith(argv[[i + 1]], "--")) {
        out[[key]] <- TRUE
        i <- i + 1
      } else {
        out[[key]] <- argv[[i + 1]]
        i <- i + 2
      }
    } else {
      i <- i + 1
    }
  }
  out
}

transform_flow <- function(x_cms, scale) {
  if (scale == "raw_cms") {
    return(x_cms)
  }
  if (scale == "log1p_cms") {
    # Guard against invalid values (shouldn't happen for discharge).
    out <- rep(NA_real_, length(x_cms))
    ok <- !is.na(x_cms) & (x_cms > -1)
    out[ok] <- log(x_cms[ok] + 1)
    return(out)
  }
  if (scale == "log_log1p_cms") {
    stop("log_log1p_cms is not allowed for current forecats plots; use log1p_cms.", call. = FALSE)
  }
  stop(paste("Unknown plot_scale:", scale))
}

inverse_transform_flow <- function(x_value, scale) {
  scale <- as.character(scale %||% "raw_cms")
  x_value <- suppressWarnings(as.numeric(x_value))
  if (scale == "raw_cms") {
    return(x_value)
  }
  if (scale == "log1p_cms") {
    return(expm1(x_value))
  }
  if (scale == "log_log1p_cms") {
    stop("log_log1p_cms is not allowed for current forecats bundles; use log1p_cms.", call. = FALSE)
  }
  stop(paste("Unknown storage scale:", scale))
}

transform_between_scales <- function(x_value, storage_scale, plot_scale) {
  raw_cms <- inverse_transform_flow(x_value, storage_scale %||% "raw_cms")
  transform_flow(raw_cms, plot_scale)
}

format_coverage_date <- function(x) {
  if (inherits(x, "Date")) return(format(x, "%Y-%m-%d"))
  x_chr <- as.character(x %||% "")
  if (!nzchar(x_chr) || x_chr == "NA") return(NA_character_)
  x_chr
}

wrap_legend_label <- function(x, width = 38) {
  paste(strwrap(as.character(x), width = width), collapse = "\n")
}

plot_forecats_bundle <- function(bundle_dir) {
  bundle_dir <- normalizePath(bundle_dir, mustWork = TRUE)
  meta_path <- file.path(bundle_dir, "meta.yaml")
  if (!file.exists(meta_path)) stop(paste("Missing meta.yaml:", meta_path))
  meta <- yaml::read_yaml(meta_path)

  inputs_dir <- file.path(bundle_dir, "inputs")
  figures_dir <- file.path(bundle_dir, "figures")
  dir.create(figures_dir, showWarnings = FALSE, recursive = TRUE)

  usgs_path <- file.path(inputs_dir, meta$paths$usgs_daily)
  retros_path <- file.path(inputs_dir, meta$paths$retros_daily)
  glofas_path <- file.path(inputs_dir, meta$paths$glofas_weighted_daily)
  nws_path <- file.path(inputs_dir, meta$paths$nws_weighted_daily)

  plot_scale <- meta$transforms$plot_scale
  storage_scales <- meta$storage_scales %||% list()
  cutoff_date <- as.Date(meta$dates$cutoff_date)
  forecast_start <- as.Date(meta$dates$forecast_start_date)
  plot_start <- as.Date(meta$dates$plot_start)
  plot_end <- as.Date(meta$dates$plot_end)
  plot_title <- as.character(meta$plot$title %||% "Observed and Retrospective River Flow")
  plot_title <- gsub("\\\\n", "\n", plot_title)

  # -------------------------
  # Load inputs
  # -------------------------
  usgs <- readr::read_csv(usgs_path, show_col_types = FALSE) %>%
    mutate(date = as.Date(date)) %>%
    mutate(discharge_cms = as.numeric(discharge_cms)) %>%
    filter(date >= plot_start & date <= plot_end) %>%
    mutate(
      obs_type = ifelse(date >= forecast_start, "After", "Before"),
      value = transform_between_scales(discharge_cms, storage_scales$usgs_daily %||% "raw_cms", plot_scale)
    )

  retros_raw <- readr::read_csv(retros_path, show_col_types = FALSE) %>%
    mutate(date = as.Date(date))

  has_long_schema <- all(c("source_id", "source_label", "discharge_cms") %in% names(retros_raw))
  retros_long <- if (has_long_schema) {
    retros_raw %>%
      transmute(
        date = as.Date(date),
        source_id = as.character(source_id),
        source_label = as.character(source_label),
        discharge_cms = as.numeric(discharge_cms)
      )
  } else {
    # Backward-compatible fallback for older bundles.
    retros_old <- retros_raw %>%
      mutate(
        glofas_cms = as.numeric(glofas_cms),
        nws_cms = as.numeric(nws_cms)
      )
    retros_old %>%
      select(date, glofas_cms, nws_cms) %>%
      pivot_longer(cols = c(glofas_cms, nws_cms), names_to = "source_id", values_to = "discharge_cms") %>%
      mutate(
        source_id = recode(source_id, glofas_cms = "glofas_synth_retro_ens_mean", nws_cms = "nws_synth_retro_ens_mean"),
        source_label = source_id
      )
  }

  retros_long <- retros_long %>%
    mutate(
      source_id = tolower(as.character(source_id)),
      source_label = vapply(seq_len(n()), function(i) {
        figure_default_retro_label(
          source_id = source_id[[i]],
          meta = meta,
          cutoff_date = cutoff_date,
          selected_run_root = selected_run_root
        ) %||% source_label[[i]] %||% source_id[[i]]
      }, character(1))
    )

  retros_long <- retros_long %>%
    filter(date >= plot_start & date < forecast_start) %>%
    mutate(value = transform_between_scales(discharge_cms, storage_scales$retros_daily %||% "raw_cms", plot_scale))

  # Forecast ensembles (wide -> long)
  read_ens_long <- function(path, provider_label) {
    provider_scale <- if (identical(provider_label, "GloFAS")) {
      storage_scales$glofas_weighted_daily %||% "raw_cms"
    } else {
      storage_scales$nws_weighted_daily %||% "raw_cms"
    }
    df <- readr::read_csv(path, show_col_types = FALSE) %>%
      mutate(target_date = as.Date(target_date)) %>%
      filter(target_date >= forecast_start & target_date <= plot_end)

    long <- df %>%
      pivot_longer(cols = -target_date, names_to = "member", values_to = "cms") %>%
      mutate(
        provider = provider_label,
        cms = as.numeric(cms),
        value = transform_between_scales(cms, provider_scale, plot_scale)
      )
    long
  }

  glofas_ens_long <- read_ens_long(glofas_path, "GloFAS")
  nws_ens_long <- read_ens_long(nws_path, "NWS")

  # -------------------------
  # Styling
  # -------------------------
  palette <- figure_product_palette()
  glofas_color <- unname(palette[["glofas"]])
  nws_color <- unname(palette[["nws"]])
  usgs_color <- unname(palette[["usgs"]])

  coverage_entries <- meta$retrospective_coverage
  coverage_df <- NULL
  if (!is.null(coverage_entries) && length(coverage_entries) > 0) {
    coverage_df <- dplyr::bind_rows(lapply(coverage_entries, function(x) {
      source_id <- as.character(x$source_id %||% "")
      source_label_raw <- as.character(x$source_label %||% source_id)
      tibble::tibble(
        source_label = figure_default_retro_label(
          source_id = source_id,
          meta = meta,
          cutoff_date = cutoff_date,
          selected_run_root = selected_run_root
        ) %||% source_label_raw,
        coverage_start = format_coverage_date(x$coverage_start),
        coverage_end = format_coverage_date(x$coverage_end)
      )
    })) %>%
      filter(nzchar(source_label))
  }

  retro_labels_from_coverage <- if (!is.null(coverage_df)) unique(coverage_df$source_label) else character(0)
  retro_labels_from_window <- unique(as.character(retros_long$source_label))
  retro_labels <- unique(c(retro_labels_from_coverage, retro_labels_from_window))

  observed_fit_label <- "USGS history"
  observed_future_label <- "USGS verification"
  glofas_forecast_label <- if (nrow(glofas_ens_long) > 0L) {
    "GloFAS ensemble"
  } else {
    character(0)
  }
  nws_forecast_label <- if (nrow(nws_ens_long) > 0L) {
    "NWM ensemble"
  } else {
    character(0)
  }
  if (nrow(glofas_ens_long) > 0L) glofas_ens_long$legend_label <- glofas_forecast_label
  if (nrow(nws_ens_long) > 0L) nws_ens_long$legend_label <- nws_forecast_label

  retro_color_map <- figure_retro_color_map(retro_labels)
  color_map <- c(
    setNames(usgs_color, observed_fit_label),
    setNames(unname(palette[["usgs_future"]]), observed_future_label),
    retro_color_map,
    setNames(glofas_color, glofas_forecast_label),
    setNames(nws_color, nws_forecast_label)
  )
  legend_levels <- c(observed_fit_label, observed_future_label, retro_labels, glofas_forecast_label, nws_forecast_label)
  shape_map <- figure_retro_shape_map(legend_levels)
  shape_map[glofas_forecast_label] <- NA_integer_
  shape_map[nws_forecast_label] <- NA_integer_
  linetype_map <- setNames(rep("solid", length(legend_levels)), legend_levels)
  linetype_map[[observed_future_label]] <- "22"
  shape_map[[observed_future_label]] <- 21L
  linetype_map[retro_labels[grepl("^GloFAS", retro_labels)]] <- "dotdash"
  linetype_map[retro_labels[grepl("^NWS", retro_labels)]] <- "longdash"
  linetype_map[nws_forecast_label] <- "dotted"

  usgs_before <- usgs %>% filter(obs_type == "Before") %>% mutate(Source = observed_fit_label)
  usgs_after <- usgs %>% filter(obs_type == "After") %>% mutate(Source = observed_future_label)

  present_labels <- retros_long %>%
    filter(!is.na(value)) %>%
    distinct(source_label) %>%
    pull(source_label) %>%
    as.character()

  retro_coverage_map <- list()
  if (!is.null(coverage_df) && nrow(coverage_df) > 0) {
    cov_agg <- coverage_df %>%
      mutate(
        coverage_start = as.Date(coverage_start),
        coverage_end = as.Date(coverage_end)
      ) %>%
      group_by(source_label) %>%
      summarise(
        coverage_start = min(coverage_start, na.rm = TRUE),
        coverage_end = max(coverage_end, na.rm = TRUE),
        .groups = "drop"
      )
    retro_coverage_map <- split(cov_agg, cov_agg$source_label)
  } else if (nrow(retros_long) > 0) {
    cov_agg <- retros_long %>%
      group_by(source_label) %>%
      summarise(
        coverage_start = min(as.Date(date), na.rm = TRUE),
        coverage_end = max(as.Date(date), na.rm = TRUE),
        .groups = "drop"
      )
    retro_coverage_map <- split(cov_agg, cov_agg$source_label)
  }

  format_retro_legend <- function(lbl) wrap_legend_label(lbl, width = 34)

  legend_label_map <- setNames(rep("", length(legend_levels)), legend_levels)
  legend_label_map[[observed_fit_label]] <- observed_fit_label
  legend_label_map[[observed_future_label]] <- observed_future_label
  if (length(retro_labels) > 0) {
    legend_label_map[retro_labels] <- vapply(retro_labels, format_retro_legend, character(1))
  }
  legend_label_map[glofas_forecast_label] <- glofas_forecast_label
  legend_label_map[nws_forecast_label] <- nws_forecast_label
  legend_label_map <- gsub("NWS", "NWM", legend_label_map)
  legend_label_map <- gsub("GloFAS historical", "GloFAS retrospective", legend_label_map)
  forecast_labels_shown <- c(
    if (nrow(glofas_ens_long) > 0L) glofas_forecast_label,
    if (nrow(nws_ens_long) > 0L) nws_forecast_label
  )
  legend_levels_shown <- c(
    observed_fit_label,
    if (nrow(usgs_after) > 0L) observed_future_label,
    retro_labels[retro_labels %in% present_labels],
    forecast_labels_shown
  )

  # Current-rating NWS stage-category references.
  # Values are discharge equivalents from USGS 11160500 rating 40.0,
  # not historical flood-stage classifications for daily-mean flow.
  all_vals <- c(usgs$value, retros_long$value, glofas_ens_long$value, nws_ens_long$value)
  flood_df <- figure_flood_label_df(plot_scale = plot_scale, values = all_vals)
  flood_style <- figure_flood_stage_style()
  flood_df$label <- ifelse(flood_df$reference_level == "minor", "Lower flow reference", "Upper flow reference")

  # -------------------------
  # Plot
  # -------------------------
  y_lab <- figure_flow_axis_label(plot_scale)

  p <- ggplot() +
    geom_vline(
      xintercept = cutoff_date,
      color = "#6B7280",
      linetype = "22",
      linewidth = 0.45,
      alpha = 0.9
    ) +
    # Flood stage horizontal lines + labels (if configured)
    {if (!is.null(flood_df) && nrow(flood_df) > 0) geom_hline(
      data = flood_df,
      aes(yintercept = y),
      linetype = flood_style$line_type,
      color = flood_style$line_color,
      linewidth = flood_style$line_width
    )} +
    {if (!is.null(flood_df) && nrow(flood_df) > 0) annotate(
      "text",
      x = plot_end,
      y = flood_df$label_y,
      label = flood_df$label,
      hjust = 1.02,
      vjust = 0.5,
      color = flood_style$label_color,
      fontface = flood_style$label_face,
      size = 2.9
    )} +
    # Retrospective/historical/reanalysis before cutoff.
    geom_line(
      data = retros_long,
      aes(x = date, y = value, color = source_label, linetype = source_label, group = source_id),
      linewidth = 0.5,
      alpha = 0.85,
      na.rm = TRUE
    ) +
    geom_point(
      data = retros_long,
      aes(x = date, y = value, color = source_label, shape = source_label, group = source_id),
      size = 1.6,
      alpha = 0.9,
      na.rm = TRUE
    ) +
    # USGS before
    geom_line(
      data = usgs_before,
      aes(x = date, y = value, color = Source, linetype = Source),
      linewidth = 0.5,
      na.rm = TRUE
    ) +
    geom_point(
      data = usgs_before,
      aes(x = date, y = value, color = Source, shape = Source),
      size = 1.4,
      na.rm = TRUE
    ) +
    # Forecast ensembles after (thin, no legend)
    geom_line(
      data = glofas_ens_long,
      aes(x = target_date, y = value, group = member, color = legend_label, linetype = legend_label),
      alpha = 0.22,
      linewidth = 0.5,
      na.rm = TRUE
    ) +
    geom_line(
      data = nws_ens_long,
      aes(x = target_date, y = value, group = member, color = legend_label, linetype = legend_label),
      alpha = 0.22,
      linewidth = 0.5,
      na.rm = TRUE
    ) +
    # USGS after (dashed)
    geom_line(
      data = usgs_after,
      aes(x = date, y = value, color = Source, linetype = Source),
      linewidth = 0.5,
      na.rm = TRUE
    ) +
    geom_point(
      data = usgs_after,
      aes(x = date, y = value, color = Source, shape = Source),
      fill = "white",
      size = 1.8,
      na.rm = TRUE
    ) +
    scale_color_manual(
      name = "Series",
      values = color_map,
      breaks = legend_levels_shown,
      labels = legend_label_map[legend_levels_shown]
    ) +
    scale_linetype_manual(
      name = "Series",
      values = linetype_map,
      breaks = legend_levels_shown,
      labels = legend_label_map[legend_levels_shown]
    ) +
    scale_shape_manual(
      name = "Series",
      values = shape_map,
      breaks = legend_levels_shown,
      labels = legend_label_map[legend_levels_shown]
    ) +
    scale_x_date(date_breaks = "2 weeks", date_labels = "%b %d") +
    labs(
      title = "Hydrologic products and observed discharge",
      subtitle = sprintf("Forecast origin: %s | first forecast: %s", cutoff_date, forecast_start),
      x = "Date",
      y = y_lab
    ) +
    guides(
      color = guide_legend(
        override.aes = list(
          size = 2.0,
          linetype = unname(linetype_map[legend_levels_shown]),
          shape = unname(shape_map[legend_levels_shown]),
          linewidth = 0.9,
          alpha = 1
        ),
        ncol = 2,
        byrow = TRUE
      ),
      linetype = "none",
      shape = "none"
    ) +
    theme_manuscript_standard(base_size = 10, title_size = 11, legend_position = "bottom") +
    theme(
      legend.title = element_blank(),
      plot.subtitle = element_text(size = 8.5),
      axis.text = element_text(size = 8.5),
      legend.text = element_text(size = 8.5),
      legend.key.width = grid::unit(25, "pt"),
      legend.key.height = grid::unit(9, "pt"),
      plot.margin = margin(6, 7, 4, 5)
    )

  # Optional markers
  if (!is.null(meta$plot$markers) && length(meta$plot$markers) > 0) {
    for (m in meta$plot$markers) {
      d <- as.Date(m$date)
      if (!is.na(d) && !is.na(cutoff_date) && d == cutoff_date) {
        next
      }
      p <- p +
        geom_vline(
          xintercept = d,
          color = m$color %||% "gray40",
          linetype = "dashed",
          linewidth = 0.5,
          alpha = 0.8
        )
      if (!is.null(m$label) && m$label != "") {
        p <- p + annotate(
          "text",
          x = d,
          y = min(usgs$value, na.rm = TRUE) - 0.15,
          label = m$label,
          color = m$color %||% "gray40",
          vjust = 4,
          hjust = -0.1,
          fontface = "bold",
          size = 3.5
        )
      }
    }
  }

  out_path <- file.path(figures_dir, "forecats.png")
  ggsave(filename = out_path, plot = p, width = 6.23, height = 4.4, units = "in", dpi = 320)
  ggsave(filename = sub("\\.png$", ".pdf", out_path), plot = p, width = 6.23, height = 4.4, units = "in", device = grDevices::pdf)
  message("Wrote: ", out_path)
  invisible(out_path)
}

`%||%` <- function(x, y) if (is.null(x)) y else x

if (sys.nframe() == 0) {
  argv <- commandArgs(trailingOnly = TRUE)
  args <- parse_args(argv)
  if (is.null(args$`bundle-dir`)) {
    stop("Usage: scripts/forecats_plot_bundle.R --bundle-dir <path>")
  }
  plot_forecats_bundle(args$`bundle-dir`)
}
