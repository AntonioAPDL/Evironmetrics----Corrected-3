# unified/post_publication_figures.R

`%||%` <- function(x, y) {
  if (is.null(x) || identical(x, "") || (length(x) == 1L && is.na(x))) y else x
}

post_publication_iso_utc <- function(x = Sys.time()) {
  format(as.POSIXct(x, tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
}

post_publication_default_style <- function() {
  list(
    version = "publication_focus_v2",
    png = list(width_in = 11, height_in = 5.8, dpi = 320),
    pdf = list(width_in = 11, height_in = 5.8),
    labels = list(
      y = "River flow [log(1 + x); x in m^3 s^-1]",
      y_scale_id = "log1p_cms"
    ),
    theme = list(
      base_family = "sans",
      base_size = 12.5,
      title_size = 15,
      subtitle_size = 11.5,
      caption_size = 9.5,
      legend_position = "right",
      grid_major = "#DCE3EA",
      grid_minor = "#EEF2F6",
      forecast_window_fill = "#F7F1E6",
      forecast_window_alpha = 0.9
    ),
    colors = list(
      observed = "#238B45",
      median = "#8C2D5B",
      interval_outer = "#F2B6CF",
      interval_inner = "#D97AA5",
      sample_paths = "#C79AB2",
      cutoff = "#6B7280"
    ),
    intervals = list(
      outer = c(5, 95),
      inner = c(20, 80)
    ),
    posterior = list(
      render_sample_paths = TRUE,
      sample_path_cap = 12,
      sample_line_alpha = 0.16,
      sample_line_width = 0.35,
      show_inner_interval = FALSE
    ),
    predictive = list(
      show_inner_interval = FALSE
    ),
    y_limits = c(0, 6.5),
    y_limits_by_cutoff = list()
  )
}

post_publication_flow_axis_label <- function(scale_id = "log1p_cms") {
  switch(
    as.character(scale_id %||% "log1p_cms"),
    raw_cms = bquote(River~flow~"["*m^3~s^-1*"]"),
    log1p_cms = bquote(River~flow~"["*log(1 + x)*";"~~x~"in"~~m^3~s^-1*"]"),
    log_log1p_cms = stop("post publication figures must stay on log1p_cms in the current workflow.", call. = FALSE),
    as.character(scale_id)
  )
}

post_publication_subtitle <- function(cutoff_date, subtitle_role) {
  bquote("Cutoff"~.(as.character(cutoff_date))~"|"~.(subtitle_role))
}

post_publication_product_palette <- function() {
  c(
    usgs = "#238B45",
    usgs_future = "#B22222",
    glofas = "#E67E22",
    nws = "#756BB1"
  )
}

post_publication_flood_stage_df <- function() {
  data.frame(
    stage = c("minor", "major"),
    label = c("Lower flow reference", "Upper flow reference"),
    y = c(5.20948615, 6.06378521),
    stringsAsFactors = FALSE
  )
}

post_publication_flood_label_df <- function(x_date) {
  out <- post_publication_flood_stage_df()
  out$x <- as.Date(x_date)
  out
}

post_publication_merge_lists <- function(base, override) {
  if (!is.list(override) || length(override) == 0L) {
    return(base)
  }
  out <- base
  for (nm in names(override)) {
    if (is.list(out[[nm]]) && is.list(override[[nm]])) {
      out[[nm]] <- post_publication_merge_lists(out[[nm]], override[[nm]])
    } else {
      out[[nm]] <- override[[nm]]
    }
  }
  out
}

post_publication_load_style <- function(project_root, config_path = NULL) {
  style <- post_publication_default_style()
  path <- config_path %||% file.path(project_root, "config", "post_publication_figures.yaml")
  path <- normalizePath(path, mustWork = FALSE)
  if (file.exists(path) && requireNamespace("yaml", quietly = TRUE)) {
    override <- yaml::read_yaml(path)
    style <- post_publication_merge_lists(style, override)
  }
  style$style_source_path <- path
  style
}

post_publication_write_style_snapshot <- function(outputs_dir, style) {
  if (!requireNamespace("yaml", quietly = TRUE)) {
    return("")
  }
  path <- file.path(outputs_dir, "publication_style_used.yaml")
  snapshot <- style
  snapshot$style_source_path <- NULL
  yaml::write_yaml(snapshot, path)
  path
}

post_publication_note_append <- function(note, token) {
  note <- as.character(note %||% "")
  token <- as.character(token %||% "")
  if (!nzchar(token)) return(note)
  if (grepl(token, note, fixed = TRUE)) return(note)
  parts <- c(trimws(note), token)
  parts <- parts[nzchar(parts)]
  paste(parts, collapse = "; ")
}

post_publication_pretty_model_id <- function(model_id) {
  label <- gsub("_", " ", as.character(model_id %||% "model"), fixed = TRUE)
  label <- gsub("(^| )exdqlm", "\\1exDQLM", label, perl = TRUE)
  label <- gsub("(^| )dqlm", "\\1DQLM", label, perl = TRUE)
  label <- gsub("(^| )ndlm", "\\1NDLM", label, perl = TRUE)
  label <- gsub("(^| )al($| )", "\\1AL\\2", label, perl = TRUE)
  trimws(label)
}

post_publication_model_title <- function(model_id, wrap_width = 56L) {
  title_map <- c(
    ndlm_univar_synth_keep = "Univariate NDLM Forecast Synthesis",
    ndlm_main_synth_drop = "Multivariate NDLM Forecast Synthesis",
    ndlm_main_synth_keep = "Multivariate NDLM Forecast Synthesis",
    dqlm_univar_al_synth = "Univariate DQLM via AL Forecast Synthesis",
    dqlm_multivar_al_synth_drop = "Multivariate DQLM via AL Forecast Synthesis",
    dqlm_multivar_al_synth_keep = "Multivariate DQLM via AL Forecast Synthesis",
    exdqlm_univar_synth = "exDQLM - Synthesis",
    exdqlm_multivar_synth_drop = "exDQLM - Synthesis",
    exdqlm_multivar_synth_keep = "exDQLM - Synthesis"
  )
  label <- unname(title_map[[as.character(model_id)]]) %||% post_publication_pretty_model_id(model_id)
  wrapped <- strwrap(label, width = as.integer(wrap_width))
  paste(wrapped, collapse = "\n")
}

post_publication_write_csv <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  if (exists("post_write_csv_deterministic", inherits = TRUE)) {
    post_write_csv_deterministic(df, path, numeric_digits = 15L)
  } else {
    utils::write.csv(df, path, row.names = FALSE)
  }
  path
}

post_publication_read_contract_csv <- function(path, required_cols, context) {
  if (!file.exists(path)) {
    stop(sprintf("%s missing: %s", context, path), call. = FALSE)
  }
  df <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  missing <- setdiff(required_cols, names(df))
  if (length(missing) > 0L) {
    stop(sprintf("%s missing required columns: %s", context, paste(missing, collapse = ", ")), call. = FALSE)
  }
  df
}

post_publication_quantile_col <- function(q) {
  sprintf("q%02d", as.integer(q))
}

post_publication_pick_quantile_cols <- function(quant_df, probs) {
  cols <- vapply(probs, post_publication_quantile_col, character(1))
  cols[cols %in% names(quant_df)]
}

post_publication_sample_subset <- function(sample_df, cap) {
  if (is.null(sample_df) || nrow(sample_df) == 0L) {
    return(sample_df)
  }
  if (!("sample_index" %in% names(sample_df))) {
    return(sample_df)
  }
  uniq <- unique(sample_df$sample_index)
  uniq <- uniq[order(uniq, method = "radix")]
  if (length(uniq) <= cap) {
    return(sample_df)
  }
  idx <- unique(round(seq(1, length(uniq), length.out = cap)))
  keep <- uniq[idx]
  sample_df[sample_df$sample_index %in% keep, , drop = FALSE]
}

post_publication_common_data <- function(quant_df) {
  out <- quant_df
  out$date <- as.Date(out$date)
  out$segment <- factor(out$segment, levels = c("history", "forecast"))
  out <- out[order(out$date, out$segment, method = "radix"), , drop = FALSE]
  rownames(out) <- NULL
  out
}

post_publication_caption <- function(cutoff_date, source_run, has_draws) {
  forecast_start <- as.Date(cutoff_date) + 1L
  parts <- c(
    sprintf(
      "Vertical dashed line marks the first forecast date (%s; cutoff %s).",
      as.character(forecast_start),
      as.character(as.Date(cutoff_date))
    ),
    if (isTRUE(has_draws)) "Posterior draws use a deterministic saved subset." else "Bands are rendered from saved post-stage quantile contracts."
  )
  paste(parts[nzchar(parts)], collapse = " ")
}

post_publication_base_theme <- function(style) {
  ggplot2::theme_minimal(base_size = style$theme$base_size, base_family = style$theme$base_family) +
    ggplot2::theme(
      plot.title = ggplot2::element_text(size = style$theme$title_size, face = "bold", color = "#18202A"),
      plot.subtitle = ggplot2::element_text(size = style$theme$subtitle_size, color = "#3D4852"),
      plot.caption = ggplot2::element_text(size = style$theme$caption_size, color = "#52606D", hjust = 0),
      axis.title = ggplot2::element_text(face = "bold", color = "#243B53"),
      axis.text = ggplot2::element_text(color = "#334E68"),
      panel.grid.major = ggplot2::element_line(color = style$theme$grid_major, linewidth = 0.35),
      panel.grid.minor = ggplot2::element_line(color = style$theme$grid_minor, linewidth = 0.18),
      legend.position = style$theme$legend_position,
      legend.title = ggplot2::element_blank(),
      legend.text = ggplot2::element_text(color = "#243B53"),
      legend.box = "vertical",
      plot.margin = ggplot2::margin(10, 16, 10, 10)
    )
}

post_publication_y_label <- function(style) {
  scale_id <- style$labels$y_scale_id %||% "log1p_cms"
  post_publication_flow_axis_label(scale_id)
}

post_publication_save_plot <- function(plot_obj, png_path, pdf_path, style) {
  dir.create(dirname(png_path), recursive = TRUE, showWarnings = FALSE)
  ggplot2::ggsave(
    filename = png_path,
    plot = plot_obj,
    width = style$png$width_in,
    height = style$png$height_in,
    units = "in",
    dpi = style$png$dpi,
    bg = "white"
  )
  if (nzchar(pdf_path %||% "")) {
    ggplot2::ggsave(
      filename = pdf_path,
      plot = plot_obj,
      width = style$pdf$width_in,
      height = style$pdf$height_in,
      units = "in",
      device = grDevices::pdf,
      bg = "white"
    )
  }
}

post_publication_render_posterior_plot <- function(model_id, quant_df, sample_df, png_path, pdf_path, style, source_run) {
  quant_df <- post_publication_common_data(quant_df)
  sample_df <- if (!is.null(sample_df)) sample_df else data.frame()
  if (nrow(sample_df) > 0L) {
    sample_df$date <- as.Date(sample_df$date)
    sample_df <- sample_df[order(sample_df$segment, sample_df$sample_index, sample_df$date, method = "radix"), , drop = FALSE]
    sample_df <- post_publication_sample_subset(sample_df, cap = as.integer(style$posterior$sample_path_cap))
  }

  outer_low <- post_publication_quantile_col(style$intervals$outer[[1L]])
  outer_high <- post_publication_quantile_col(style$intervals$outer[[2L]])
  inner_low <- post_publication_quantile_col(style$intervals$inner[[1L]])
  inner_high <- post_publication_quantile_col(style$intervals$inner[[2L]])
  center_col <- if ("q50" %in% names(quant_df)) "q50" else names(quant_df)[grepl("^q", names(quant_df))][ceiling(sum(grepl("^q", names(quant_df))) / 2)]

  has_history <- any(quant_df$segment == "history", na.rm = TRUE)
  has_forecast <- any(quant_df$segment == "forecast", na.rm = TRUE)
  cutoff_date <- if (has_history) max(quant_df$date[quant_df$segment == "history"], na.rm = TRUE) else min(quant_df$date, na.rm = TRUE)
  forecast_end <- max(quant_df$date, na.rm = TRUE)
  forecast_start <- if (has_forecast) min(quant_df$date[quant_df$segment == "forecast"], na.rm = TRUE) else cutoff_date
  cutoff_line_date <- cutoff_date

  p <- ggplot2::ggplot(quant_df, ggplot2::aes(x = date)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = .data[[outer_low]], ymax = .data[[outer_high]], fill = "90% interval"),
      alpha = 0.45,
      color = NA
    )

  if (isTRUE(style$posterior$show_inner_interval) && inner_low %in% names(quant_df) && inner_high %in% names(quant_df)) {
    p <- p + ggplot2::geom_ribbon(
      ggplot2::aes(ymin = .data[[inner_low]], ymax = .data[[inner_high]], fill = "60% interval"),
      alpha = 0.62,
      color = NA
    )
  }

  if (isTRUE(style$posterior$render_sample_paths) && nrow(sample_df) > 0L) {
    p <- p + ggplot2::geom_line(
      data = sample_df,
      mapping = ggplot2::aes(y = value, group = interaction(segment, sample_index), color = "Posterior draws"),
      linewidth = style$posterior$sample_line_width,
      alpha = style$posterior$sample_line_alpha,
      lineend = "round"
    )
  }

  p <- p +
    ggplot2::geom_line(
      ggplot2::aes(y = .data[[center_col]], color = "Model median"),
      linewidth = 1.05,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed, color = "Observed"),
      linewidth = 0.9,
      lineend = "round"
    ) +
    ggplot2::geom_segment(
      data = data.frame(date = cutoff_line_date),
      mapping = ggplot2::aes(x = date, xend = date, y = -Inf, yend = Inf),
      inherit.aes = FALSE,
      color = style$colors$cutoff,
      linewidth = 0.55,
      linetype = "22"
    ) +
    ggplot2::scale_color_manual(
      values = c(
        "Observed" = style$colors$observed,
        "Model median" = style$colors$median,
        "Posterior draws" = style$colors$sample_paths
      ),
      breaks = c("Observed", "Model median", if (isTRUE(style$posterior$render_sample_paths) && nrow(sample_df) > 0L) "Posterior draws")
    ) +
    ggplot2::scale_fill_manual(
      values = c(
        "90% interval" = style$colors$interval_outer,
        "60% interval" = style$colors$interval_inner
      ),
      breaks = c("90% interval", if (isTRUE(style$posterior$show_inner_interval) && inner_low %in% names(quant_df) && inner_high %in% names(quant_df)) "60% interval")
    ) +
    ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
    ggplot2::labs(
      title = post_publication_pretty_model_id(model_id),
      subtitle = post_publication_subtitle(cutoff_date, "posterior samples"),
      x = NULL,
      y = post_publication_y_label(style),
      caption = post_publication_caption(cutoff_date, source_run, has_draws = nrow(sample_df) > 0L)
    ) +
    post_publication_base_theme(style)

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
  invisible(list(cutoff_date = cutoff_date))
}

post_publication_render_predictive_plot <- function(model_id, quant_df, png_path, pdf_path, style, source_run) {
  quant_df <- post_publication_common_data(quant_df)
  outer_low <- post_publication_quantile_col(style$intervals$outer[[1L]])
  outer_high <- post_publication_quantile_col(style$intervals$outer[[2L]])
  inner_low <- post_publication_quantile_col(style$intervals$inner[[1L]])
  inner_high <- post_publication_quantile_col(style$intervals$inner[[2L]])
  center_col <- if ("q50" %in% names(quant_df)) "q50" else names(quant_df)[grepl("^q", names(quant_df))][ceiling(sum(grepl("^q", names(quant_df))) / 2)]

  has_history <- any(quant_df$segment == "history", na.rm = TRUE)
  has_forecast <- any(quant_df$segment == "forecast", na.rm = TRUE)
  cutoff_date <- if (has_history) max(quant_df$date[quant_df$segment == "history"], na.rm = TRUE) else min(quant_df$date, na.rm = TRUE)
  forecast_end <- max(quant_df$date, na.rm = TRUE)
  forecast_start <- if (has_forecast) min(quant_df$date[quant_df$segment == "forecast"], na.rm = TRUE) else cutoff_date
  cutoff_line_date <- cutoff_date

  p <- ggplot2::ggplot(quant_df, ggplot2::aes(x = date)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = .data[[outer_low]], ymax = .data[[outer_high]], fill = "90% interval"),
      alpha = 0.45,
      color = NA
    )

  if (isTRUE(style$predictive$show_inner_interval) && inner_low %in% names(quant_df) && inner_high %in% names(quant_df)) {
    p <- p + ggplot2::geom_ribbon(
      ggplot2::aes(ymin = .data[[inner_low]], ymax = .data[[inner_high]], fill = "60% interval"),
      alpha = 0.62,
      color = NA
    )
  }

  p <- p +
    ggplot2::geom_line(
      ggplot2::aes(y = .data[[center_col]], color = "Model median"),
      linewidth = 1.05,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      ggplot2::aes(y = observed, color = "Observed"),
      linewidth = 0.9,
      lineend = "round"
    ) +
    ggplot2::geom_segment(
      data = data.frame(date = cutoff_line_date),
      mapping = ggplot2::aes(x = date, xend = date, y = -Inf, yend = Inf),
      inherit.aes = FALSE,
      color = style$colors$cutoff,
      linewidth = 0.55,
      linetype = "22"
    ) +
    ggplot2::scale_color_manual(
      values = c(
        "Observed" = style$colors$observed,
        "Model median" = style$colors$median
      ),
      breaks = c("Observed", "Model median")
    ) +
    ggplot2::scale_fill_manual(
      values = c(
        "90% interval" = style$colors$interval_outer,
        "60% interval" = style$colors$interval_inner
      ),
      breaks = c("90% interval", if (isTRUE(style$predictive$show_inner_interval) && inner_low %in% names(quant_df) && inner_high %in% names(quant_df)) "60% interval")
    ) +
    ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
    ggplot2::labs(
      title = post_publication_pretty_model_id(model_id),
      subtitle = post_publication_subtitle(cutoff_date, "predictive bands"),
      x = NULL,
      y = post_publication_y_label(style),
      caption = post_publication_caption(cutoff_date, source_run, has_draws = FALSE)
    ) +
    post_publication_base_theme(style)

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
  invisible(list(cutoff_date = cutoff_date))
}

post_publication_manifest_row <- function(model_id, plot_type, path, source_run, note = "") {
  data.frame(
    model_id = as.character(model_id),
    plot_type = as.character(plot_type),
    path = normalizePath(path, mustWork = FALSE),
    source_run = as.character(source_run %||% ""),
    note = as.character(note %||% ""),
    stringsAsFactors = FALSE
  )
}

post_publication_merge_manifest_rows <- function(existing, additional) {
  merged <- rbind(existing, additional)
  merged[] <- lapply(merged, function(col) if (is.factor(col)) as.character(col) else col)
  dedupe_cols <- if (all(c("model_id", "plot_type", "path") %in% names(merged))) {
    c("model_id", "plot_type", "path")
  } else if (all(c("model_id", "source_plot_type", "canonical_png") %in% names(merged))) {
    intersect(c("model_id", "source_plot_type", "canonical_png", "pdf_path"), names(merged))
  } else {
    names(merged)
  }
  key <- do.call(
    paste,
    c(lapply(dedupe_cols, function(col) ifelse(is.na(merged[[col]]), "<NA>", as.character(merged[[col]]))), sep = "\r")
  )
  merged <- merged[!duplicated(key, fromLast = TRUE), , drop = FALSE]
  sort_cols <- intersect(
    c("model_id", "plot_type", "source_plot_type", "path", "canonical_png", "pdf_path", "source_run"),
    names(merged)
  )
  if (length(sort_cols) > 0L) {
    ord_args <- lapply(sort_cols, function(col) merged[[col]])
    ord_args$method <- "radix"
    ord_args$na.last <- TRUE
    ord <- do.call(order, ord_args)
    merged <- merged[ord, , drop = FALSE]
  }
  rownames(merged) <- NULL
  merged
}

post_publication_update_main_manifest <- function(manifest_path, rows_to_add, png_note_updates) {
  current <- utils::read.csv(manifest_path, stringsAsFactors = FALSE, check.names = FALSE)
  if (nrow(png_note_updates) > 0L) {
    for (i in seq_len(nrow(png_note_updates))) {
      hit <- current$model_id == png_note_updates$model_id[[i]] &
        current$plot_type == png_note_updates$plot_type[[i]] &
        current$path == png_note_updates$path[[i]]
      current$note[hit] <- png_note_updates$note[[i]]
    }
  }
  merged <- post_publication_merge_manifest_rows(current, rows_to_add)
  post_publication_write_csv(merged, manifest_path)
  merged
}

unified_render_publication_figures <- function(
  outputs_dir,
  run_id,
  project_root,
  enabled = TRUE,
  rewrite_canonical_png = TRUE,
  export_pdf = TRUE,
  fail_fast = TRUE,
  style_config_path = NULL
) {
  outputs_dir <- normalizePath(outputs_dir, mustWork = FALSE)
  if (!isTRUE(enabled)) {
    return(list(status = TRUE, rendered = 0L, skipped = 0L, outputs_dir = outputs_dir))
  }
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ggplot2 is required for publication post figures.", call. = FALSE)
  }

  manifest_path <- file.path(outputs_dir, "figure_manifest.csv")
  if (!file.exists(manifest_path)) {
    return(list(status = TRUE, rendered = 0L, skipped = 0L, outputs_dir = outputs_dir, note = "figure_manifest_missing"))
  }

  style <- post_publication_load_style(project_root = project_root, config_path = style_config_path)
  style_snapshot_path <- post_publication_write_style_snapshot(outputs_dir, style)
  manifest <- utils::read.csv(manifest_path, stringsAsFactors = FALSE, check.names = FALSE)
  target_types <- c("cutoff_window_posterior_samples", "cutoff_window_predictive_bands")
  target_rows <- manifest[manifest$plot_type %in% target_types, , drop = FALSE]
  if (nrow(target_rows) == 0L) {
    return(list(status = TRUE, rendered = 0L, skipped = 0L, outputs_dir = outputs_dir, style_snapshot = style_snapshot_path))
  }

  rendered_rows <- list()
  manifest_rows_to_add <- list()
  png_note_updates <- list()
  failures <- character(0)
  successful_targets <- 0L

  for (i in seq_len(nrow(target_rows))) {
    row <- target_rows[i, , drop = FALSE]
    model_id <- row$model_id[[1L]]
    plot_type <- row$plot_type[[1L]]
    png_path <- normalizePath(row$path[[1L]], mustWork = FALSE)
    if (!isTRUE(rewrite_canonical_png)) {
      png_path <- sub("\\.png$", "_publication.png", png_path, ignore.case = TRUE)
    }
    pdf_path <- if (isTRUE(export_pdf)) sub("\\.png$", ".pdf", png_path, ignore.case = TRUE) else ""
    quant_row <- manifest[manifest$model_id == model_id & manifest$plot_type == "cutoff_window_quantiles", , drop = FALSE]
    sample_row <- manifest[manifest$model_id == model_id & manifest$plot_type == "cutoff_window_sample_subset", , drop = FALSE]

    tryCatch({
      quant_df <- post_publication_read_contract_csv(
        quant_row$path[[1L]],
        required_cols = c("model_id", "date", "segment", "observed"),
        context = sprintf("quantiles contract for %s", model_id)
      )
      sample_df <- if (nrow(sample_row) > 0L) {
        post_publication_read_contract_csv(
          sample_row$path[[1L]],
          required_cols = c("model_id", "draw_id", "sample_index", "date", "segment", "value"),
          context = sprintf("sample subset contract for %s", model_id)
        )
      } else {
        NULL
      }

      if (identical(plot_type, "cutoff_window_posterior_samples")) {
        post_root <- post_publication_find_post_root(outputs_dir)
        cache_paths <- post_publication_resolve_posterior_cache_paths(post_root, model_id)
        quant_focus <- post_publication_apply_exact_cache_interval(
          quant_df = quant_df,
          hist_cache_path = cache_paths$hist_cache_path,
          forecast_cache_path = cache_paths$forecast_cache_path,
          probs = c(0.025, 0.975),
          low_col = "interval_low",
          high_col = "interval_high"
        )
        quant_focus <- post_publication_apply_exact_cache_mean(
          quant_df = quant_focus,
          hist_cache_path = cache_paths$hist_cache_path,
          forecast_cache_path = cache_paths$forecast_cache_path,
          mean_col = "model_mean"
        )

        post_publication_render_focus_posterior_plot(
          model_id = model_id,
          quant_df = quant_focus,
          sample_df = sample_df,
          png_path = png_path,
          pdf_path = pdf_path,
          style = style,
          source_run = row$source_run[[1L]],
          interval_low_col = "interval_low",
          interval_high_col = "interval_high",
          interval_label = "Pointwise central 95% predictive interval",
          ensemble_df = NULL
        )

        png_note_updates[[length(png_note_updates) + 1L]] <- post_publication_manifest_row(
          model_id = model_id,
          plot_type = plot_type,
          path = row$path[[1L]],
          source_run = row$source_run[[1L]],
          note = sprintf("style=%s; exact_interval=95_from_cache; observed_split=fit_vs_heldout", style$version)
        )

        if (nzchar(pdf_path)) {
          manifest_rows_to_add[[length(manifest_rows_to_add) + 1L]] <- post_publication_manifest_row(
            model_id = model_id,
            plot_type = "cutoff_window_posterior_samples_pdf",
            path = pdf_path,
            source_run = row$source_run[[1L]],
            note = sprintf("paired_with=cutoff_window_posterior_samples; style=%s", style$version)
          )
        }

        rendered_rows[[length(rendered_rows) + 1L]] <- data.frame(
          model_id = as.character(model_id),
          source_plot_type = "cutoff_window_posterior_samples_focus",
          canonical_png = normalizePath(png_path, mustWork = FALSE),
          pdf_path = if (nzchar(pdf_path)) normalizePath(pdf_path, mustWork = FALSE) else "",
          quantiles_path = normalizePath(quant_row$path[[1L]], mustWork = FALSE),
          sample_subset_path = if (nrow(sample_row) > 0L) normalizePath(sample_row$path[[1L]], mustWork = FALSE) else "",
          style_version = style$version,
          style_source_path = as.character(style$style_source_path %||% ""),
          style_snapshot_path = as.character(style_snapshot_path %||% ""),
          rewritten_canonical_png = isTRUE(rewrite_canonical_png),
          rendered_at_utc = post_publication_iso_utc(),
          source_run = as.character(row$source_run[[1L]]),
          stringsAsFactors = FALSE
        )

        context_paths <- post_publication_resolve_context_input_paths(post_root)
        if (length(context_paths) > 0L) {
          ensemble_frames <- list()
          if (!is.null(context_paths$glofas_path) && file.exists(context_paths$glofas_path)) {
            ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(context_paths$glofas_path, "GloFAS")
          }
          if (!is.null(context_paths$nws_path) && file.exists(context_paths$nws_path)) {
            ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(context_paths$nws_path, "NWS")
          }
          retrospective_df <- if (!is.null(context_paths$retros_path) && file.exists(context_paths$retros_path)) {
            post_publication_read_retrospectives(context_paths$retros_path)
          } else {
            NULL
          }
          if (length(ensemble_frames) > 0L || (!is.null(retrospective_df) && nrow(retrospective_df) > 0L)) {
            ensemble_df <- if (length(ensemble_frames) > 0L) do.call(rbind, ensemble_frames) else NULL
            with_ens_png <- sub("\\.png$", "_with_raw_ensembles.png", png_path, ignore.case = TRUE)
            with_ens_pdf <- if (nzchar(pdf_path)) sub("\\.png$", "_with_raw_ensembles.pdf", png_path, ignore.case = TRUE) else ""

            post_publication_render_focus_posterior_plot(
              model_id = model_id,
              quant_df = quant_focus,
              sample_df = sample_df,
              png_path = with_ens_png,
              pdf_path = with_ens_pdf,
              style = style,
              source_run = row$source_run[[1L]],
              interval_low_col = "interval_low",
              interval_high_col = "interval_high",
              interval_label = "Pointwise central 95% predictive interval",
              ensemble_df = ensemble_df,
              retrospective_df = retrospective_df
            )

            manifest_rows_to_add[[length(manifest_rows_to_add) + 1L]] <- post_publication_manifest_row(
              model_id = model_id,
              plot_type = "cutoff_window_posterior_samples_with_raw_ensembles",
              path = with_ens_png,
              source_run = row$source_run[[1L]],
              note = sprintf("style=%s; exact_interval=95_from_cache; includes_adapter_scale_retrospectives_and_ensemble_references", style$version)
            )
            if (nzchar(with_ens_pdf)) {
              manifest_rows_to_add[[length(manifest_rows_to_add) + 1L]] <- post_publication_manifest_row(
                model_id = model_id,
                plot_type = "cutoff_window_posterior_samples_with_raw_ensembles_pdf",
                path = with_ens_pdf,
                source_run = row$source_run[[1L]],
                note = sprintf("paired_with=cutoff_window_posterior_samples_with_raw_ensembles; style=%s", style$version)
              )
            }

            rendered_rows[[length(rendered_rows) + 1L]] <- data.frame(
              model_id = as.character(model_id),
              source_plot_type = "cutoff_window_posterior_samples_with_raw_ensembles",
              canonical_png = normalizePath(with_ens_png, mustWork = FALSE),
              pdf_path = if (nzchar(with_ens_pdf)) normalizePath(with_ens_pdf, mustWork = FALSE) else "",
              quantiles_path = normalizePath(quant_row$path[[1L]], mustWork = FALSE),
              sample_subset_path = if (nrow(sample_row) > 0L) normalizePath(sample_row$path[[1L]], mustWork = FALSE) else "",
              style_version = style$version,
              style_source_path = as.character(style$style_source_path %||% ""),
              style_snapshot_path = as.character(style_snapshot_path %||% ""),
              rewritten_canonical_png = FALSE,
              rendered_at_utc = post_publication_iso_utc(),
              source_run = as.character(row$source_run[[1L]]),
              stringsAsFactors = FALSE
            )
          }
        }
      } else if (identical(plot_type, "cutoff_window_predictive_bands")) {
        post_publication_render_focus_predictive_plot(
          model_id = model_id,
          quant_df = quant_df,
          png_path = png_path,
          pdf_path = pdf_path,
          style = style,
          source_run = row$source_run[[1L]],
          interval_low_col = "q05",
          interval_high_col = "q95",
          interval_label = "90% interval",
          ensemble_df = NULL
        )
        png_note_updates[[length(png_note_updates) + 1L]] <- post_publication_manifest_row(
          model_id = model_id,
          plot_type = plot_type,
          path = row$path[[1L]],
          source_run = row$source_run[[1L]],
          note = sprintf("style=%s; interval=90_from_quantiles; observed_split=fit_vs_heldout", style$version)
        )

        if (nzchar(pdf_path)) {
          manifest_rows_to_add[[length(manifest_rows_to_add) + 1L]] <- post_publication_manifest_row(
            model_id = model_id,
            plot_type = paste0(plot_type, "_pdf"),
            path = pdf_path,
            source_run = row$source_run[[1L]],
            note = sprintf("paired_with=%s; style=%s", plot_type, style$version)
          )
        }

        rendered_rows[[length(rendered_rows) + 1L]] <- data.frame(
          model_id = as.character(model_id),
          source_plot_type = "cutoff_window_predictive_bands_focus",
          canonical_png = normalizePath(png_path, mustWork = FALSE),
          pdf_path = if (nzchar(pdf_path)) normalizePath(pdf_path, mustWork = FALSE) else "",
          quantiles_path = normalizePath(quant_row$path[[1L]], mustWork = FALSE),
          sample_subset_path = if (nrow(sample_row) > 0L) normalizePath(sample_row$path[[1L]], mustWork = FALSE) else "",
          style_version = style$version,
          style_source_path = as.character(style$style_source_path %||% ""),
          style_snapshot_path = as.character(style_snapshot_path %||% ""),
          rewritten_canonical_png = isTRUE(rewrite_canonical_png),
          rendered_at_utc = post_publication_iso_utc(),
          source_run = as.character(row$source_run[[1L]]),
          stringsAsFactors = FALSE
        )

        post_root <- post_publication_find_post_root(outputs_dir)
        context_paths <- post_publication_resolve_context_input_paths(post_root)
        if (length(context_paths) > 0L) {
          ensemble_frames <- list()
          if (!is.null(context_paths$glofas_path) && file.exists(context_paths$glofas_path)) {
            ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(context_paths$glofas_path, "GloFAS")
          }
          if (!is.null(context_paths$nws_path) && file.exists(context_paths$nws_path)) {
            ensemble_frames[[length(ensemble_frames) + 1L]] <- post_publication_read_member_forecasts(context_paths$nws_path, "NWS")
          }
          retrospective_df <- if (!is.null(context_paths$retros_path) && file.exists(context_paths$retros_path)) {
            post_publication_read_retrospectives(context_paths$retros_path)
          } else {
            NULL
          }
          if (length(ensemble_frames) > 0L || (!is.null(retrospective_df) && nrow(retrospective_df) > 0L)) {
            ensemble_df <- if (length(ensemble_frames) > 0L) do.call(rbind, ensemble_frames) else NULL
            with_ens_png <- sub("\\.png$", "_with_raw_ensembles.png", png_path, ignore.case = TRUE)
            with_ens_pdf <- if (nzchar(pdf_path)) sub("\\.png$", "_with_raw_ensembles.pdf", png_path, ignore.case = TRUE) else ""
            post_publication_render_focus_predictive_plot(
              model_id = model_id,
              quant_df = quant_df,
              png_path = with_ens_png,
              pdf_path = with_ens_pdf,
              style = style,
              source_run = row$source_run[[1L]],
              interval_low_col = "q05",
              interval_high_col = "q95",
              interval_label = "90% interval",
              ensemble_df = ensemble_df,
              retrospective_df = retrospective_df
            )

            manifest_rows_to_add[[length(manifest_rows_to_add) + 1L]] <- post_publication_manifest_row(
              model_id = model_id,
              plot_type = "cutoff_window_predictive_bands_with_raw_ensembles",
              path = with_ens_png,
              source_run = row$source_run[[1L]],
              note = sprintf("style=%s; interval=90_from_quantiles; includes_adapter_scale_retrospectives_and_ensemble_references", style$version)
            )
            if (nzchar(with_ens_pdf)) {
              manifest_rows_to_add[[length(manifest_rows_to_add) + 1L]] <- post_publication_manifest_row(
                model_id = model_id,
                plot_type = "cutoff_window_predictive_bands_with_raw_ensembles_pdf",
                path = with_ens_pdf,
                source_run = row$source_run[[1L]],
                note = sprintf("paired_with=cutoff_window_predictive_bands_with_raw_ensembles; style=%s", style$version)
              )
            }

            rendered_rows[[length(rendered_rows) + 1L]] <- data.frame(
              model_id = as.character(model_id),
              source_plot_type = "cutoff_window_predictive_bands_with_raw_ensembles",
              canonical_png = normalizePath(with_ens_png, mustWork = FALSE),
              pdf_path = if (nzchar(with_ens_pdf)) normalizePath(with_ens_pdf, mustWork = FALSE) else "",
              quantiles_path = normalizePath(quant_row$path[[1L]], mustWork = FALSE),
              sample_subset_path = "",
              style_version = style$version,
              style_source_path = as.character(style$style_source_path %||% ""),
              style_snapshot_path = as.character(style_snapshot_path %||% ""),
              rewritten_canonical_png = FALSE,
              rendered_at_utc = post_publication_iso_utc(),
              source_run = as.character(row$source_run[[1L]]),
              stringsAsFactors = FALSE
            )
          }
        }
      }
      successful_targets <- successful_targets + 1L
    }, error = function(e) {
      failures <<- c(failures, sprintf("%s [%s]: %s", model_id, plot_type, conditionMessage(e)))
    })
  }

  if (length(failures) > 0L && isTRUE(fail_fast)) {
    stop(paste(failures, collapse = " | "), call. = FALSE)
  }

  rendered_df <- if (length(rendered_rows) > 0L) do.call(rbind, rendered_rows) else data.frame()
  pub_manifest_path <- file.path(outputs_dir, "publication_figure_manifest.csv")
  if (nrow(rendered_df) > 0L) {
    rendered_df <- rendered_df[order(rendered_df$model_id, rendered_df$source_plot_type, method = "radix", na.last = TRUE), , drop = FALSE]
    rownames(rendered_df) <- NULL
    post_publication_write_csv(rendered_df, pub_manifest_path)
  }

  add_df <- if (length(manifest_rows_to_add) > 0L) do.call(rbind, manifest_rows_to_add) else manifest[FALSE, , drop = FALSE]
  update_df <- if (length(png_note_updates) > 0L) do.call(rbind, png_note_updates) else manifest[FALSE, , drop = FALSE]
  post_publication_update_main_manifest(manifest_path, rows_to_add = add_df, png_note_updates = update_df)

  list(
    status = length(failures) == 0L,
    rendered = successful_targets,
    rendered_outputs = nrow(rendered_df),
    skipped = nrow(target_rows) - successful_targets,
    failures = failures,
    outputs_dir = outputs_dir,
    publication_manifest_path = pub_manifest_path,
    style_snapshot_path = style_snapshot_path
  )
}

post_publication_matrix_interval <- function(path, probs = c(0.025, 0.975), context = "matrix_interval") {
  if (!file.exists(path)) {
    stop(sprintf("%s missing: %s", context, path), call. = FALSE)
  }
  mat <- readRDS(path)
  mat <- as.matrix(mat)
  if (!is.matrix(mat) || nrow(mat) <= 0L || ncol(mat) <= 0L) {
    stop(sprintf("%s invalid matrix at %s", context, path), call. = FALSE)
  }
  qs <- apply(mat, 2, stats::quantile, probs = probs, na.rm = TRUE, type = 8, names = FALSE)
  matrix(qs, nrow = length(probs), byrow = FALSE)
}

post_publication_apply_exact_cache_interval <- function(
  quant_df,
  hist_cache_path,
  forecast_cache_path,
  probs = c(0.025, 0.975),
  low_col = "interval_low",
  high_col = "interval_high"
) {
  out <- post_publication_common_data(quant_df)
  hist_idx <- which(out$segment == "history")
  fc_idx <- which(out$segment == "forecast")
  out[[low_col]] <- NA_real_
  out[[high_col]] <- NA_real_

  if (length(hist_idx) > 0L) {
    hist_q <- post_publication_matrix_interval(hist_cache_path, probs = probs, context = "history cache interval")
    if (ncol(hist_q) != length(hist_idx)) {
      stop(sprintf("history cache columns (%d) do not match history rows (%d)", ncol(hist_q), length(hist_idx)), call. = FALSE)
    }
    out[[low_col]][hist_idx] <- as.numeric(hist_q[1L, ])
    out[[high_col]][hist_idx] <- as.numeric(hist_q[2L, ])
  }

  if (length(fc_idx) > 0L) {
    fc_q <- post_publication_matrix_interval(forecast_cache_path, probs = probs, context = "forecast cache interval")
    if (ncol(fc_q) != length(fc_idx)) {
      stop(sprintf("forecast cache columns (%d) do not match forecast rows (%d)", ncol(fc_q), length(fc_idx)), call. = FALSE)
    }
    out[[low_col]][fc_idx] <- as.numeric(fc_q[1L, ])
    out[[high_col]][fc_idx] <- as.numeric(fc_q[2L, ])
  }

  out
}

post_publication_apply_exact_cache_mean <- function(
  quant_df,
  hist_cache_path,
  forecast_cache_path,
  mean_col = "model_mean"
) {
  out <- post_publication_common_data(quant_df)
  hist_idx <- which(out$segment == "history")
  fc_idx <- which(out$segment == "forecast")
  out[[mean_col]] <- NA_real_

  if (length(hist_idx) > 0L) {
    hist_mat <- as.matrix(readRDS(hist_cache_path))
    if (ncol(hist_mat) != length(hist_idx)) {
      stop(sprintf("history cache columns (%d) do not match history rows (%d)", ncol(hist_mat), length(hist_idx)), call. = FALSE)
    }
    out[[mean_col]][hist_idx] <- colMeans(hist_mat, na.rm = TRUE)
  }

  if (length(fc_idx) > 0L) {
    fc_mat <- as.matrix(readRDS(forecast_cache_path))
    if (ncol(fc_mat) != length(fc_idx)) {
      stop(sprintf("forecast cache columns (%d) do not match forecast rows (%d)", ncol(fc_mat), length(fc_idx)), call. = FALSE)
    }
    out[[mean_col]][fc_idx] <- colMeans(fc_mat, na.rm = TRUE)
  }

  out
}

post_publication_read_member_forecasts <- function(path, provider_label) {
  if (!file.exists(path)) {
    stop(sprintf("forecast member file missing: %s", path), call. = FALSE)
  }
  df <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  if (!("target_date" %in% names(df))) {
    stop(sprintf("forecast member file missing target_date: %s", path), call. = FALSE)
  }
  member_cols <- grep("^member_", names(df), value = TRUE)
  if (length(member_cols) == 0L) {
    stop(sprintf("forecast member file missing member_* columns: %s", path), call. = FALSE)
  }
  dates <- as.Date(df$target_date)
  long <- data.frame(
    date = rep(dates, times = length(member_cols)),
    member = rep(member_cols, each = nrow(df)),
    value = as.numeric(unlist(df[member_cols], use.names = FALSE)),
    provider = as.character(provider_label),
    stringsAsFactors = FALSE
  )
  long <- long[is.finite(long$value) & !is.na(long$date), , drop = FALSE]
  rownames(long) <- NULL
  long
}

post_publication_read_retrospectives <- function(path) {
  if (!file.exists(path)) {
    stop(sprintf("retrospective adapter file missing: %s", path), call. = FALSE)
  }
  df <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  date_col <- intersect(c("Date", "date"), names(df))
  if (length(date_col) == 0L) {
    stop(sprintf("retrospective adapter file missing Date/date column: %s", path), call. = FALSE)
  }
  date_col <- date_col[[1L]]
  source_cols <- setdiff(names(df), c(date_col, "target_date", "USGS", "usgs", "observed", "observed_usgs"))
  source_cols <- source_cols[grepl("glofas|nws", source_cols, ignore.case = TRUE)]
  if (length(source_cols) == 0L) {
    return(data.frame(date = as.Date(character()), source = character(), provider = character(), value = numeric()))
  }
  dates <- as.Date(df[[date_col]])
  rows <- lapply(source_cols, function(col) {
    provider <- if (grepl("glofas", col, ignore.case = TRUE)) {
      "GloFAS"
    } else if (grepl("nws", col, ignore.case = TRUE)) {
      "NWS"
    } else {
      col
    }
    data.frame(
      date = dates,
      source = as.character(col),
      provider = provider,
      value = suppressWarnings(as.numeric(df[[col]])),
      stringsAsFactors = FALSE
    )
  })
  long <- do.call(rbind, rows)
  long <- long[is.finite(long$value) & !is.na(long$date), , drop = FALSE]
  rownames(long) <- NULL
  long
}

post_publication_resolve_context_input_paths <- function(post_root) {
  inputs_dir <- file.path(post_root, "inputs")
  out <- list(
    nws_path = file.path(inputs_dir, "nws_post_adapter.csv"),
    glofas_path = file.path(inputs_dir, "glofas_post_adapter.csv"),
    retros_path = file.path(inputs_dir, "retros_post_adapter.csv")
  )
  out[vapply(out, file.exists, logical(1))]
}

# Explicit interior breaks prevent the automatic calendar grid from drawing an
# extra date beyond the observed/cache window and clipping its label at the edge.
post_publication_focus_date_breaks <- function(dates) {
  limits <- range(as.Date(dates), na.rm = TRUE)
  if (as.integer(diff(limits)) < 2L) return(unique(limits))
  seq(limits[[1L]] + 1L, limits[[2L]] - 1L, by = "2 weeks")
}

post_publication_focus_caption <- function(cutoff_date, forecast_start = as.Date(cutoff_date) + 1L) {
  sprintf(
    "Dashed line: forecast origin (%s); first forecast: %s.",
    as.character(as.Date(cutoff_date)),
    as.character(as.Date(forecast_start))
  )
}

post_publication_focus_subtitle <- function(cutoff_date, forecast_start = as.Date(cutoff_date) + 1L) {
  sprintf(
    "Forecast origin: %s | first forecast: %s",
    as.character(as.Date(cutoff_date)),
    as.character(as.Date(forecast_start))
  )
}

post_publication_parse_y_limits <- function(raw, context) {
  if (is.null(raw)) {
    return(NULL)
  }
  vals <- as.numeric(unlist(raw, use.names = FALSE))
  if (length(vals) != 2L || any(!is.finite(vals)) || vals[[1L]] >= vals[[2L]]) {
    stop(sprintf("invalid y limits configured for %s", context), call. = FALSE)
  }
  vals
}

post_publication_y_limits_for_cutoff <- function(cutoff_date, style) {
  shared <- post_publication_parse_y_limits(style$y_limits %||% NULL, "shared publication style")
  if (!is.null(shared)) {
    return(shared)
  }
  cutoff_key <- format(as.Date(cutoff_date), "%Y%m%d")
  raw <- style$y_limits_by_cutoff[[cutoff_key]] %||% NULL
  post_publication_parse_y_limits(raw, sprintf("cutoff %s", cutoff_key))
}

post_publication_render_focus_predictive_plot <- function(
  model_id,
  quant_df,
  png_path,
  pdf_path,
  style,
  source_run = "",
  interval_low_col = "q05",
  interval_high_col = "q95",
  interval_label = "90% interval",
  ensemble_df = NULL,
  retrospective_df = NULL
) {
  quant_df <- post_publication_common_data(quant_df)
  if (!(interval_low_col %in% names(quant_df)) || !(interval_high_col %in% names(quant_df))) {
    stop(sprintf("focus predictive plot requires interval columns %s and %s", interval_low_col, interval_high_col), call. = FALSE)
  }

  if (!is.null(ensemble_df) && nrow(ensemble_df) > 0L) {
    ensemble_df$date <- as.Date(ensemble_df$date)
    ensemble_df <- ensemble_df[order(ensemble_df$provider, ensemble_df$member, ensemble_df$date, method = "radix"), , drop = FALSE]
  }

  center_col <- if ("model_mean" %in% names(quant_df)) {
    "model_mean"
  } else if ("q50" %in% names(quant_df)) {
    "q50"
  } else {
    names(quant_df)[grepl("^q", names(quant_df))][ceiling(sum(grepl("^q", names(quant_df))) / 2)]
  }

  has_history <- any(quant_df$segment == "history", na.rm = TRUE)
  has_forecast <- any(quant_df$segment == "forecast", na.rm = TRUE)
  cutoff_date <- if (has_history) max(quant_df$date[quant_df$segment == "history"], na.rm = TRUE) else min(quant_df$date, na.rm = TRUE)
  forecast_end <- max(quant_df$date, na.rm = TRUE)
  forecast_start <- if (has_forecast) min(quant_df$date[quant_df$segment == "forecast"], na.rm = TRUE) else cutoff_date
  cutoff_line_date <- cutoff_date
  y_limits <- post_publication_y_limits_for_cutoff(cutoff_date, style)

  if (!is.null(retrospective_df) && nrow(retrospective_df) > 0L) {
    retrospective_df$date <- as.Date(retrospective_df$date)
    retrospective_df <- retrospective_df[
      !is.na(retrospective_df$date) &
        retrospective_df$date >= min(quant_df$date, na.rm = TRUE) &
        retrospective_df$date <= cutoff_date &
        is.finite(retrospective_df$value),
      ,
      drop = FALSE
    ]
    retrospective_df$legend_label <- ifelse(
      retrospective_df$provider == "GloFAS",
      "GloFAS retrospective",
      "NWS retrospective"
    )
    retrospective_df <- retrospective_df[order(retrospective_df$provider, retrospective_df$source, retrospective_df$date, method = "radix"), , drop = FALSE]
  }
  retrospective_labels <- if (!is.null(retrospective_df) && nrow(retrospective_df) > 0L) {
    unique(retrospective_df$legend_label)
  } else {
    character(0)
  }

  hist_obs <- quant_df[quant_df$segment == "history", c("date", "observed"), drop = FALSE]
  fc_obs <- quant_df[quant_df$segment == "forecast", c("date", "observed"), drop = FALSE]
  palette <- post_publication_product_palette()
  observed_fit_label <- "USGS observations"
  observed_future_label <- "Held-out USGS"
  model_center_label <- "exDQLM - Synthesis"
  color_breaks <- c(
    observed_fit_label,
    observed_future_label,
    model_center_label,
    retrospective_labels,
    if (!is.null(ensemble_df) && any(ensemble_df$provider == "GloFAS")) {
      sprintf("GloFAS forecast ensemble (%d members)", length(unique(ensemble_df$member[ensemble_df$provider == "GloFAS"])))
    },
    if (!is.null(ensemble_df) && any(ensemble_df$provider != "GloFAS")) {
      sprintf("NWS forecast ensemble (%d members)", length(unique(ensemble_df$member[ensemble_df$provider != "GloFAS"])))
    }
  )
  linetype_values <- c(
    setNames("solid", observed_fit_label),
    setNames("22", observed_future_label),
    setNames("solid", model_center_label)
  )
  if (length(retrospective_labels) > 0L) {
    linetype_values[retrospective_labels] <- "dotdash"
  }
  if (!is.null(ensemble_df) && any(ensemble_df$provider == "GloFAS")) {
    glofas_label <- sprintf("GloFAS forecast ensemble (%d members)", length(unique(ensemble_df$member[ensemble_df$provider == "GloFAS"])))
    linetype_values[[glofas_label]] <- "solid"
  }
  if (!is.null(ensemble_df) && any(ensemble_df$provider != "GloFAS")) {
    nws_label <- sprintf("NWS forecast ensemble (%d members)", length(unique(ensemble_df$member[ensemble_df$provider != "GloFAS"])))
    linetype_values[[nws_label]] <- "solid"
  }

  flood_labels <- post_publication_flood_label_df(forecast_end)

  p <- ggplot2::ggplot(quant_df, ggplot2::aes(x = date)) +
    ggplot2::geom_hline(
      data = post_publication_flood_stage_df(),
      mapping = ggplot2::aes(yintercept = y),
      inherit.aes = FALSE,
      color = "#5B677A",
      linewidth = 0.55,
      linetype = "22",
      alpha = 0.95
    ) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = .data[[interval_low_col]], ymax = .data[[interval_high_col]], fill = interval_label),
      alpha = 0.42,
      color = NA
    )

  if (!is.null(retrospective_df) && nrow(retrospective_df) > 0L) {
    p <- p + ggplot2::geom_line(
      data = retrospective_df,
      mapping = ggplot2::aes(y = value, group = interaction(provider, source), color = legend_label, linetype = legend_label),
      linewidth = 0.82,
      alpha = 0.78,
      lineend = "round"
    )
  }

  if (!is.null(ensemble_df) && nrow(ensemble_df) > 0L) {
    ensemble_df$legend_label <- ifelse(
      ensemble_df$provider == "GloFAS",
      sprintf("GloFAS forecast ensemble (%d members)", length(unique(ensemble_df$member[ensemble_df$provider == "GloFAS"]))),
      sprintf("NWS forecast ensemble (%d members)", length(unique(ensemble_df$member[ensemble_df$provider != "GloFAS"])))
    )
    p <- p + ggplot2::geom_line(
      data = ensemble_df,
      mapping = ggplot2::aes(y = value, group = interaction(provider, member), color = legend_label, linetype = legend_label),
      linewidth = 0.62,
      alpha = 0.24,
      lineend = "round"
    )
  }

  p <- p +
    ggplot2::geom_line(
      ggplot2::aes(y = .data[[center_col]], color = model_center_label, linetype = model_center_label),
      linewidth = 1.10,
      lineend = "round"
    ) +
    ggplot2::geom_line(
      data = hist_obs,
      mapping = ggplot2::aes(y = observed, color = observed_fit_label, linetype = observed_fit_label),
      linewidth = 0.95,
      lineend = "round"
    ) +
    ggplot2::geom_point(
      data = hist_obs,
      mapping = ggplot2::aes(x = date, y = observed),
      inherit.aes = FALSE,
      color = palette[["usgs"]],
      fill = palette[["usgs"]],
      shape = 16,
      size = 1.5,
      alpha = 0.95,
      show.legend = FALSE
    ) +
    ggplot2::geom_line(
      data = fc_obs,
      mapping = ggplot2::aes(y = observed, color = observed_future_label, linetype = observed_future_label),
      linewidth = 0.95,
      lineend = "round"
    ) +
    ggplot2::geom_point(
      data = fc_obs,
      mapping = ggplot2::aes(x = date, y = observed),
      inherit.aes = FALSE,
      color = palette[["usgs_future"]],
      fill = "white",
      shape = 21,
      stroke = 0.55,
      size = 1.7,
      show.legend = FALSE
    ) +
    ggplot2::geom_segment(
      data = data.frame(date = cutoff_line_date),
      mapping = ggplot2::aes(x = date, xend = date, y = -Inf, yend = Inf),
      inherit.aes = FALSE,
      color = style$colors$cutoff,
      linewidth = 0.55,
      linetype = "22"
    ) +
    ggplot2::geom_text(
      data = flood_labels,
      mapping = ggplot2::aes(x = x, y = y, label = label),
      inherit.aes = FALSE,
      hjust = 1.02,
      vjust = -0.15,
      size = 4.2,
      color = "#4A5568",
      fontface = "italic"
    ) +
    ggplot2::scale_color_manual(
      values = c(
        setNames(palette[["usgs"]], observed_fit_label),
        setNames(palette[["usgs_future"]], observed_future_label),
        setNames(style$colors$median, model_center_label),
        setNames(palette[["glofas"]], retrospective_labels[grepl("^GloFAS retrospective$", retrospective_labels)]),
        setNames(palette[["nws"]], retrospective_labels[grepl("^NWS retrospective$", retrospective_labels)]),
        setNames(palette[["glofas"]], names(linetype_values)[grepl("^GloFAS forecast ensemble \\(", names(linetype_values))]),
        setNames(palette[["nws"]], names(linetype_values)[grepl("^NWS forecast ensemble \\(", names(linetype_values))])
      ),
      breaks = color_breaks
    ) +
    ggplot2::scale_linetype_manual(
      values = linetype_values,
      breaks = intersect(color_breaks, names(linetype_values))
    ) +
    ggplot2::scale_fill_manual(
      values = setNames(style$colors$interval_outer, interval_label),
      breaks = interval_label
    ) +
    ggplot2::scale_x_date(date_breaks = "1 week", date_labels = "%b %d") +
    ggplot2::labs(
      title = post_publication_model_title(model_id),
      subtitle = post_publication_focus_subtitle(cutoff_date, forecast_start),
      x = "Date",
      y = post_publication_y_label(style),
      caption = post_publication_focus_caption(cutoff_date, forecast_start)
    ) +
    ggplot2::guides(
      color = ggplot2::guide_legend(order = 1, nrow = 2, byrow = TRUE),
      linetype = "none",
      fill = ggplot2::guide_legend(order = 2, nrow = 1)
    ) +
    post_publication_base_theme(style) +
    ggplot2::theme(
      legend.position = "bottom",
      legend.direction = "horizontal",
      legend.box = "vertical",
      legend.justification = "center",
      legend.text = ggplot2::element_text(size = 10.8, color = "#243B53"),
      legend.margin = ggplot2::margin(t = 2, r = 0, b = 0, l = 0),
      legend.spacing.x = grid::unit(8, "pt"),
      legend.key.width = grid::unit(20, "pt"),
      legend.key.height = grid::unit(10, "pt"),
      plot.margin = ggplot2::margin(10, 10, 8, 10)
    )

  if (!is.null(y_limits)) {
    p <- p + ggplot2::coord_cartesian(ylim = y_limits)
  }

  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
  invisible(list(cutoff_date = cutoff_date))
}

post_publication_find_post_root <- function(outputs_dir) {
  outputs_dir <- normalizePath(outputs_dir, mustWork = FALSE)
  candidates <- unique(c(
    dirname(dirname(outputs_dir)),
    dirname(outputs_dir),
    outputs_dir
  ))
  hits <- candidates[
    dir.exists(candidates) &
      file.exists(file.path(candidates, "cache")) &
      file.exists(file.path(candidates, "inputs"))
  ]
  if (length(hits) == 0L) {
    stop(sprintf("could not infer post root from outputs_dir: %s", outputs_dir), call. = FALSE)
  }
  hits[[1L]]
}

post_publication_resolve_posterior_cache_paths <- function(post_root, model_id) {
  cache_dir <- file.path(post_root, "cache")
  if (!dir.exists(cache_dir)) {
    stop(sprintf("post cache directory missing: %s", cache_dir), call. = FALSE)
  }

  if (grepl("multivar", model_id, fixed = TRUE)) {
    mode <- if (grepl("_keep$", model_id)) {
      "keep"
    } else if (grepl("_drop$", model_id)) {
      "drop"
    } else {
      stop(sprintf("could not infer multivariate mode from model_id: %s", model_id), call. = FALSE)
    }
    hist_cache_path <- file.path(cache_dir, sprintf("%s__mode-%s__synth_multivar_hist_log1p.rds", model_id, mode))
    forecast_cache_path <- file.path(cache_dir, sprintf("%s__mode-%s__synth_multivar_forecast_log1p.rds", model_id, mode))
  } else if (grepl("univar", model_id, fixed = TRUE)) {
    hist_cache_path <- file.path(cache_dir, "synth_univar_hist_log1p.rds")
    forecast_cache_path <- file.path(cache_dir, "synth_univar_forecast_log1p.rds")
  } else {
    stop(sprintf("no posterior cache contract defined for model_id: %s", model_id), call. = FALSE)
  }

  if (!file.exists(hist_cache_path) || !file.exists(forecast_cache_path)) {
    stop(
      sprintf(
        "posterior cache missing for %s: hist=%s forecast=%s",
        model_id,
        hist_cache_path,
        forecast_cache_path
      ),
      call. = FALSE
    )
  }

  list(
    hist_cache_path = hist_cache_path,
    forecast_cache_path = forecast_cache_path
  )
}

post_publication_resolve_ensemble_input_paths <- function(post_root) {
  out <- post_publication_resolve_context_input_paths(post_root)
  out[intersect(names(out), c("nws_path", "glofas_path"))]
}

post_publication_render_focus_posterior_plot <- function(
  model_id, quant_df, sample_df, png_path, pdf_path, style, source_run = "",
  interval_low_col = "interval_low", interval_high_col = "interval_high",
  interval_label = "Pointwise central 95% predictive interval",
  ensemble_df = NULL, retrospective_df = NULL
) {
  quant_df <- post_publication_common_data(quant_df)
  if (!(interval_low_col %in% names(quant_df)) || !(interval_high_col %in% names(quant_df))) {
    stop(sprintf("focus plot requires interval columns %s and %s", interval_low_col, interval_high_col), call. = FALSE)
  }
  # These columns are calculated from the complete saved predictive matrices by
  # post_publication_apply_exact_cache_interval/mean; display paths never enter
  # their calculation. The mean is E[log(1 + Q)], not log(1 + E[Q]).
  if (!("model_mean" %in% names(quant_df))) {
    stop("focus posterior plot requires exact cache-derived model_mean; a median cannot be labeled as a predictive mean.", call. = FALSE)
  }
  center_col <- "model_mean"
  has_history <- any(quant_df$segment == "history", na.rm = TRUE)
  has_forecast <- any(quant_df$segment == "forecast", na.rm = TRUE)
  cutoff_date <- if (has_history) max(quant_df$date[quant_df$segment == "history"], na.rm = TRUE) else min(quant_df$date, na.rm = TRUE)
  forecast_start <- if (has_forecast) min(quant_df$date[quant_df$segment == "forecast"], na.rm = TRUE) else cutoff_date + 1L
  forecast_end <- max(quant_df$date, na.rm = TRUE)
  y_limits <- post_publication_y_limits_for_cutoff(cutoff_date, style)
  sample_df <- if (!is.null(sample_df)) sample_df else data.frame()
  if (isTRUE(style$posterior$render_sample_paths) && nrow(sample_df) > 0L) {
    sample_df$date <- as.Date(sample_df$date)
    sample_df <- sample_df[order(sample_df$segment, sample_df$sample_index, sample_df$date, method = "radix"), , drop = FALSE]
    sample_df <- post_publication_sample_subset(sample_df, cap = as.integer(style$posterior$sample_path_cap %||% 10L))
  } else {
    sample_df <- data.frame()
  }
  if (!is.null(ensemble_df) && nrow(ensemble_df) > 0L) {
    ensemble_df$date <- as.Date(ensemble_df$date)
    ensemble_df$legend_label <- ifelse(ensemble_df$provider == "GloFAS", "GloFAS ensemble", "NWM ensemble")
    ensemble_df <- ensemble_df[order(ensemble_df$provider, ensemble_df$member, ensemble_df$date, method = "radix"), , drop = FALSE]
  }
  if (!is.null(retrospective_df) && nrow(retrospective_df) > 0L) {
    retrospective_df$date <- as.Date(retrospective_df$date)
    retrospective_df <- retrospective_df[
      !is.na(retrospective_df$date) & retrospective_df$date >= min(quant_df$date, na.rm = TRUE) &
        retrospective_df$date <= cutoff_date & is.finite(retrospective_df$value), , drop = FALSE]
    retrospective_df$legend_label <- ifelse(retrospective_df$provider == "GloFAS", "GloFAS retrospective", "NWM retrospective")
    retrospective_df <- retrospective_df[order(retrospective_df$provider, retrospective_df$source, retrospective_df$date, method = "radix"), , drop = FALSE]
  }
  hist_obs <- quant_df[quant_df$segment == "history", c("date", "observed"), drop = FALSE]
  fc_obs <- quant_df[quant_df$segment == "forecast", c("date", "observed"), drop = FALSE]
  observed_fit_label <- "USGS history"
  observed_future_label <- "USGS verification"
  model_center_label <- "Predictive mean (log scale)"
  sample_label <- "Predictive sample paths"
  palette <- post_publication_product_palette()
  color_values <- c(
    setNames(palette[["usgs"]], observed_fit_label), setNames(palette[["usgs_future"]], observed_future_label),
    setNames(style$colors$median, model_center_label),
    "GloFAS retrospective" = palette[["glofas"]], "NWM retrospective" = palette[["nws"]],
    "GloFAS ensemble" = palette[["glofas"]], "NWM ensemble" = palette[["nws"]],
    setNames("#87929E", sample_label))
  # Provider and role both remain identifiable when printed without color.
  linetype_values <- c("solid", "22", "solid", "dotdash", "longdash", "solid", "dotted", "solid")
  names(linetype_values) <- names(color_values)
  shape_values <- setNames(c(16, 21, NA, 15, 17, NA, NA, NA), names(color_values))
  retrospective_labels <- if (!is.null(retrospective_df) && nrow(retrospective_df)) unique(retrospective_df$legend_label) else character()
  ensemble_labels <- if (!is.null(ensemble_df) && nrow(ensemble_df)) unique(ensemble_df$legend_label) else character()
  color_breaks <- c(observed_fit_label, observed_future_label, model_center_label,
                    retrospective_labels, ensemble_labels, if (nrow(sample_df)) sample_label)
  color_breaks <- unique(color_breaks)
  p <- ggplot2::ggplot(quant_df, ggplot2::aes(x = date)) +
    ggplot2::geom_hline(data = post_publication_flood_stage_df(), ggplot2::aes(yintercept = y),
      inherit.aes = FALSE, color = "#5B677A", linewidth = 0.35, linetype = "22") +
    ggplot2::geom_ribbon(ggplot2::aes(ymin = .data[[interval_low_col]], ymax = .data[[interval_high_col]], fill = interval_label),
      alpha = 0.42, color = NA)
  if (nrow(sample_df)) {
    p <- p + ggplot2::geom_line(data = sample_df,
      ggplot2::aes(y = value, group = interaction(segment, sample_index), color = sample_label),
      linewidth = style$posterior$sample_line_width %||% 0.25,
      alpha = style$posterior$sample_line_alpha %||% 0.10, lineend = "round")
  }
  if (!is.null(retrospective_df) && nrow(retrospective_df)) {
    p <- p + ggplot2::geom_line(data = retrospective_df,
      ggplot2::aes(y = value, group = interaction(provider, source), color = legend_label, linetype = legend_label),
      linewidth = 0.50, alpha = 0.85, lineend = "round")
    # Sparse markers supplement the different dash patterns, without obscuring
    # daily values. Lines still use every original date and value.
    marker_df <- retrospective_df[as.integer(retrospective_df$date - min(quant_df$date)) %% 7L == 0L, , drop = FALSE]
    p <- p + ggplot2::geom_point(data = marker_df,
      ggplot2::aes(y = value, color = legend_label, shape = legend_label), size = 1.5, show.legend = TRUE)
  }
  if (!is.null(ensemble_df) && nrow(ensemble_df)) {
    p <- p + ggplot2::geom_line(data = ensemble_df,
      ggplot2::aes(y = value, group = interaction(provider, member), color = legend_label, linetype = legend_label),
      linewidth = 0.35, alpha = 0.28, lineend = "round")
  }
  p <- p +
    ggplot2::geom_line(ggplot2::aes(y = .data[[center_col]], color = model_center_label, linetype = model_center_label), linewidth = 0.90) +
    ggplot2::geom_line(data = hist_obs, ggplot2::aes(y = observed, color = observed_fit_label, linetype = observed_fit_label), linewidth = 0.6) +
    ggplot2::geom_point(data = hist_obs, ggplot2::aes(y = observed, color = observed_fit_label, shape = observed_fit_label), size = 1.3, show.legend = TRUE) +
    ggplot2::geom_line(data = fc_obs, ggplot2::aes(y = observed, color = observed_future_label, linetype = observed_future_label), linewidth = 0.6) +
    ggplot2::geom_point(data = fc_obs, ggplot2::aes(y = observed, color = observed_future_label, shape = observed_future_label), fill = "white", stroke = 0.4, size = 1.5, show.legend = TRUE) +
    ggplot2::geom_vline(xintercept = cutoff_date, color = style$colors$cutoff, linewidth = 0.4, linetype = "22") +
    ggplot2::geom_text(data = post_publication_flood_label_df(forecast_end),
      ggplot2::aes(x = x, y = y, label = label), inherit.aes = FALSE,
      hjust = 1.02, vjust = -0.3, size = 2.9, color = "#4A5568", fontface = "italic") +
    ggplot2::scale_color_manual(name = NULL, values = color_values, breaks = color_breaks) +
    ggplot2::scale_linetype_manual(name = NULL, values = linetype_values, breaks = color_breaks) +
    ggplot2::scale_shape_manual(name = NULL, values = shape_values, breaks = color_breaks) +
    ggplot2::scale_fill_manual(name = NULL, values = setNames(style$colors$interval_outer, interval_label), breaks = interval_label) +
    ggplot2::scale_x_date(breaks = post_publication_focus_date_breaks(quant_df$date), date_labels = "%b %d") +
    ggplot2::labs(title = post_publication_model_title(model_id),
      subtitle = post_publication_focus_subtitle(cutoff_date, forecast_start), x = "Date", y = post_publication_y_label(style),
      caption = post_publication_focus_caption(cutoff_date, forecast_start)) +
    ggplot2::guides(color = ggplot2::guide_legend(order = 1, ncol = 2, byrow = TRUE,
      override.aes = list(alpha = 1, linetype = unname(linetype_values[color_breaks]),
        shape = unname(shape_values[color_breaks]),
        linewidth = ifelse(color_breaks == model_center_label, 0.9, 0.5), size = 1.6)),
      linetype = "none", shape = "none", fill = ggplot2::guide_legend(order = 2, nrow = 1, override.aes = list(shape = NA, color = NA, linetype = 0))) +
    post_publication_base_theme(style) +
    ggplot2::theme(legend.position = "bottom", legend.direction = "horizontal", legend.box = "vertical",
      legend.justification = "center", legend.text = ggplot2::element_text(size = 8.5, color = "#243B53"),
      axis.text = ggplot2::element_text(size = 8.5),
      legend.margin = ggplot2::margin(t = 1, r = 0, b = 0, l = 0),
      legend.spacing.x = grid::unit(6, "pt"), legend.key.width = grid::unit(25, "pt"),
      legend.key.height = grid::unit(9, "pt"), plot.margin = ggplot2::margin(6, 7, 4, 5))
  if (!is.null(y_limits)) p <- p + ggplot2::coord_cartesian(ylim = y_limits)
  post_publication_save_plot(p, png_path = png_path, pdf_path = pdf_path, style = style)
  invisible(list(cutoff_date = cutoff_date, forecast_start = forecast_start,
    sample_path_count = if (nrow(sample_df)) length(unique(sample_df$sample_index)) else 0L,
    plot = p))
}
