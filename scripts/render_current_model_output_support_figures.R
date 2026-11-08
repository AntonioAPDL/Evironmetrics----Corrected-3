#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(values) {
  out <- list()
  i <- 1L
  while (i <= length(values)) {
    key <- values[[i]]
    if (!startsWith(key, "--")) {
      stop(sprintf("Unexpected argument: %s", key), call. = FALSE)
    }
    if (i == length(values)) {
      stop(sprintf("Missing value for argument: %s", key), call. = FALSE)
    }
    out[[substring(key, 3L)]] <- values[[i + 1L]]
    i <- i + 2L
  }
  out
}

opt <- parse_args(args)

required <- c("workflow-root", "run-root", "output-dir", "cutoff-date", "forecast-start-date")
missing <- required[!vapply(required, function(k) !is.null(opt[[k]]) && nzchar(opt[[k]]), logical(1))]
if (length(missing) > 0L) {
  stop(sprintf("Missing required args: %s", paste(missing, collapse = ", ")), call. = FALSE)
}

project_root <- normalizePath(opt[["workflow-root"]], mustWork = TRUE)
run_root <- normalizePath(opt[["run-root"]], mustWork = TRUE)
out_dir <- normalizePath(opt[["output-dir"]], mustWork = FALSE)
state_summary_path_opt <- opt[["state-summary-path"]]
state_summary_path <- if (!is.null(state_summary_path_opt) && nzchar(state_summary_path_opt)) {
  normalizePath(state_summary_path_opt, mustWork = TRUE)
} else {
  NULL
}
setwd(project_root)
cutoff_date <- opt[["cutoff-date"]]
forecast_start_date <- opt[["forecast-start-date"]]

source(file.path(project_root, "scripts", "figure_style_contract.R"))

DISPLAY_FLOW_SCALE <- if (!is.null(opt[["display-flow-scale"]]) && nzchar(opt[["display-flow-scale"]])) {
  opt[["display-flow-scale"]]
} else {
  "log1p_cms"
}
INTERNAL_FLOW_SCALE <- if (!is.null(opt[["internal-flow-scale"]]) && nzchar(opt[["internal-flow-scale"]])) {
  opt[["internal-flow-scale"]]
} else {
  DISPLAY_FLOW_SCALE
}
STATE_INTERNAL_FLOW_SCALE <- INTERNAL_FLOW_SCALE
COMPONENT_SUMMARY_PROBS <- c(0.975, 0.5, 0.025)

convert_internal_flow_to_display <- function(x, internal_scale = STATE_INTERNAL_FLOW_SCALE, display_scale = DISPLAY_FLOW_SCALE) {
  vals <- suppressWarnings(as.numeric(x))
  if (identical(internal_scale, display_scale)) {
    return(vals)
  }
  if (identical(internal_scale, "log_log1p_cms") && identical(display_scale, "log1p_cms")) {
    return(exp(vals))
  }
  stop(sprintf("Unsupported flow-scale conversion: %s -> %s", internal_scale, display_scale), call. = FALSE)
}

convert_internal_bounds_to_display <- function(bounds, internal_scale = STATE_INTERNAL_FLOW_SCALE, display_scale = DISPLAY_FLOW_SCALE) {
  convert_internal_flow_to_display(bounds, internal_scale = internal_scale, display_scale = display_scale)
}

compute_display_ylim <- function(values, include_zero = TRUE, pad_frac = 0.08) {
  vals <- suppressWarnings(as.numeric(values))
  vals <- vals[is.finite(vals)]
  if (length(vals) == 0L) {
    return(c(0, 1))
  }
  lo <- min(vals, na.rm = TRUE)
  hi <- max(vals, na.rm = TRUE)
  if (include_zero) {
    lo <- min(lo, 0)
  }
  span <- hi - lo
  if (!is.finite(span) || span <= 0) {
    span <- max(abs(hi), 1)
  }
  pad <- max(span * pad_frac, 0.05)
  c(lo, hi + pad)
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
cache_dir <- file.path(out_dir, "cache")
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

q_paths <- c(
  file.path(run_root, "fit/exdqlm_multivar/keep/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData"),
  file.path(run_root, "fit/exdqlm_multivar/keep/q=20/outputs/DISC_variables_20_exAL_synth_DISC.RData"),
  file.path(run_root, "fit/exdqlm_multivar/keep/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData"),
  file.path(run_root, "fit/exdqlm_multivar/keep/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData"),
  file.path(run_root, "fit/exdqlm_multivar/keep/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData"),
  file.path(run_root, "fit/exdqlm_multivar/keep/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData"),
  file.path(run_root, "fit/exdqlm_multivar/keep/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData")
)

have_q_paths <- all(file.exists(q_paths))
missing_q <- q_paths[!file.exists(q_paths)]
if (!have_q_paths && is.null(state_summary_path)) {
  stop(sprintf(
    paste(
      "Missing required multivariate fit artifacts and no retained state summary was provided:",
      "%s"
    ),
    paste(missing_q, collapse = ", ")
  ), call. = FALSE)
}

env_vars <- list(
  ENV_PROJECT_ROOT = project_root,
  UNIFIED_REQUIRE_RUNSCOPED_POST = "TRUE",
  UNIFIED_ALLOW_LEGACY_POST_FALLBACK = "FALSE",
  UNIFIED_MODEL_RUN_EXDQLM_MULTIVAR = if (have_q_paths) "TRUE" else "FALSE",
  UNIFIED_MODEL_RUN_EXDQLM_UNIVAR = "FALSE",
  UNIFIED_MODEL_RUN_NDLM_MAIN = "FALSE",
  UNIFIED_MODEL_RUN_NDLM_UNIVAR = "FALSE",
  UNIFIED_CUTOFF_DATE = cutoff_date,
  UNIFIED_FORECAST_START_DATE = forecast_start_date,
  ENV_USGS_DAILY_PATH = file.path(run_root, "inputs/shared/usgs/usgs_daily.csv"),
  ENV_NWS_FORECAST_PATH = file.path(run_root, "inputs/shared/forecasts/nws_forecast.csv"),
  ENV_GLOFAS_FORECAST_PATH = file.path(run_root, "inputs/shared/forecasts/glofas_forecast.csv"),
  ENV_RETROS_PATH = file.path(run_root, "inputs/shared/retros/retros.csv"),
  ENV_PPT_PATH = file.path(run_root, "inputs/shared/covariates/cov_01_PPT.csv"),
  ENV_SOIL_PATH = file.path(run_root, "inputs/shared/covariates/cov_02_SOIL.csv"),
  ENV_PCA_PATH = file.path(run_root, "inputs/shared/covariates/cov_03_PCA.csv"),
  ENV_COVARIATE_FEATURES_PATH = file.path(run_root, "inputs/shared/covariates/covariate_features.csv"),
  UNIFIED_POST_CACHE_DIR = cache_dir
)
if (have_q_paths) {
  env_vars$UNIFIED_DISC_W_RDATA_PATHS <- paste(q_paths, collapse = ",")
}
do.call(Sys.setenv, env_vars)

source(file.path(project_root, "R/environmetrics/00_setup.R"))
source(file.path(project_root, "R/environmetrics/00_paths.R"))
DATA_CBIND_RDS <- file.path(cache_dir, "data_cbind_tY_X.rds")
DATA_CBIND_CSV <- file.path(cache_dir, "data_cbind_tY_X.csv")
TIMESTAMPS_CSV <- file.path(cache_dir, "timestamps.csv")
source(file.path(project_root, "R/environmetrics/00_constants.R"))
source(file.path(project_root, "R/environmetrics/01_config.R"))
source(file.path(project_root, "R/environmetrics/02_helpers_core.R"))
source(file.path(project_root, "R/environmetrics/utils_data.R"))
source(file.path(project_root, "R/environmetrics/utils_plot.R"))
source(file.path(project_root, "R/environmetrics/10_data_inputs.R"))
source(file.path(project_root, "R/environmetrics/20_model_setup.R"))
if (!exists("dates_ts_usgs", inherits = FALSE)) {
  dates_ts_usgs <- timestamps
}
if (!exists("flood_stage_labels", inherits = FALSE)) {
  flood_stage_labels <- c("Major reference", "Minor reference")
}

state_cache_path <- file.path(cache_dir, "historical_support_state_summaries.rds")

load_selected_objects <- function(path, object_names) {
  env <- new.env(parent = emptyenv())
  loaded <- load(path, envir = env)
  missing <- setdiff(object_names, loaded)
  if (length(missing) > 0L) {
    stop(sprintf("Missing objects in %s: %s", path, paste(missing, collapse = ", ")), call. = FALSE)
  }
  list2env(mget(object_names, envir = env, inherits = FALSE), envir = .GlobalEnv)
  rm(env)
  invisible(gc())
}

resolve_proj <- function(Ft, Mu, Sigma) {
  p_use <- min(length(Ft), length(Mu), nrow(Sigma), ncol(Sigma))
  Ft_use <- matrix(as.numeric(Ft)[seq_len(p_use)], ncol = 1L)
  Mu_use <- as.numeric(Mu)[seq_len(p_use)]
  Sigma_use <- as.matrix(Sigma)[seq_len(p_use), seq_len(p_use), drop = FALSE]
  c(
    mean = as.numeric(crossprod(Ft_use, Mu_use)),
    sd = sqrt(max(as.numeric(t(Ft_use) %*% Sigma_use %*% Ft_use), 0))
  )
}

build_xbs_retro <- function() {
  objs <- list(
    `5` = new.theta.out_5_exAL_synth_DISC,
    `20` = new.theta.out_20_exAL_synth_DISC,
    `35` = new.theta.out_35_exAL_synth_DISC,
    `50` = new.theta.out_50_exAL_synth_DISC,
    `65` = new.theta.out_65_exAL_synth_DISC,
    `80` = new.theta.out_80_exAL_synth_DISC,
    `95` = new.theta.out_95_exAL_synth_DISC
  )
  qnames <- c("5", "20", "35", "50", "65", "80", "95")

  set.seed(777)
  arr <- array(NA_real_, c(7, TT, n.samp))
  for (t in seq_len(TT)) {
    Ft <- FF[, 1, t]
    stats <- lapply(qnames, function(q) resolve_proj(Ft, objs[[q]]$sm[, t], objs[[q]]$sC[, , t]))
    means <- vapply(stats, `[[`, numeric(1), "mean")
    sds <- vapply(stats, `[[`, numeric(1), "sd")
    draws <- rnorm(
      n = n.samp * length(means),
      mean = rep(means, each = n.samp),
      sd = rep(sds, each = n.samp)
    )
    draws_mat <- matrix(draws, nrow = n.samp, ncol = length(means))
    for (i in seq_along(qnames)) {
      arr[i, t, ] <- sort_keep_na(draws_mat[, i])
    }
  }
  arr
}

build_quant_df <- function(arr, idx, dates) {
  percentiles <- c(0.025, 0.5, 0.975)

  get_quantile_trajectory <- function(qidx, quantile_name) {
    mat <- arr[qidx, idx, , drop = FALSE]
    mat <- matrix(mat, nrow = length(idx), ncol = dim(arr)[3])
    qt_res <- t(fast_row_quantiles_t(mat, probs = percentiles))
    colnames(qt_res) <- c("Lower", "Median", "Upper")
    data.frame(
      Date = dates,
      Quantile = quantile_name,
      Lower = qt_res[, "Lower"],
      Median = qt_res[, "Median"],
      Upper = qt_res[, "Upper"]
    )
  }

  quantiles_map <- list(
    "5th" = 1,
    "20th" = 2,
    "35th" = 3,
    "50th" = 4,
    "65th" = 5,
    "80th" = 6,
    "95th" = 7
  )

  bind_rows(lapply(names(quantiles_map), function(qname) {
    get_quantile_trajectory(quantiles_map[[qname]], qname)
  }))
}

render_quantile_window <- function(xbs_retro, idx, title_text, out_file, ylim_override = NULL) {
  dates <- as.Date(dates_ts_usgs[idx])
  quant_df <- build_quant_df(xbs_retro, idx, dates)
  quant_df <- quant_df %>%
    mutate(
      Lower = convert_internal_flow_to_display(Lower),
      Median = convert_internal_flow_to_display(Median),
      Upper = convert_internal_flow_to_display(Upper)
    )
  obs_df <- data.frame(Date = dates, Value = convert_internal_flow_to_display(Y[1, idx]))
  flood_df <- figure_flood_label_df(
    plot_scale = DISPLAY_FLOW_SCALE,
    values = c(quant_df$Lower, quant_df$Upper, obs_df$Value)
  )
  flood_style <- figure_flood_stage_style()
  ylim <- if (is.null(ylim_override)) {
    compute_display_ylim(c(quant_df$Lower, quant_df$Upper, obs_df$Value, flood_df$y), include_zero = TRUE)
  } else {
    as.numeric(ylim_override)
  }

  alpha_val <- 0.11
  col_95 <- "#2171b5"
  col_50 <- "#238b45"
  col_05 <- "#b2182b"
  p <- ggplot() +
    annotate(
      "text",
      x = max(as.Date(dates_ts_usgs[idx])),
      y = flood_df$label_y,
      label = flood_df$label,
      hjust = 1.02,
      vjust = 0.2,
      color = flood_style$label_color,
      fontface = flood_style$label_face,
      size = flood_style$label_size
    ) +
    geom_hline(
      data = flood_df,
      aes(yintercept = y),
      linetype = flood_style$line_type,
      color = flood_style$line_color,
      linewidth = flood_style$line_width
    ) +
    geom_ribbon(
      data = quant_df %>% filter(Quantile == "95th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = col_95,
      alpha = alpha_val
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Median),
      color = col_95,
      linewidth = 0.45
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Lower),
      color = col_95,
      linewidth = 0.14
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Upper),
      color = col_95,
      linewidth = 0.14
    ) +
    geom_ribbon(
      data = quant_df %>% filter(Quantile == "5th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = col_05,
      alpha = alpha_val
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Median),
      color = col_05,
      linewidth = 0.45
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Lower),
      color = col_05,
      linewidth = 0.14
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Upper),
      color = col_05,
      linewidth = 0.14
    ) +
    geom_ribbon(
      data = quant_df %>% filter(Quantile == "50th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = col_50,
      alpha = alpha_val
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Median),
      color = col_50,
      linewidth = 0.45
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Lower),
      color = col_50,
      linewidth = 0.14
    ) +
    geom_line(
      data = quant_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Upper),
      color = col_50,
      linewidth = 0.14
    ) +
    geom_point(
      data = obs_df,
      aes(x = Date, y = Value),
      color = "black",
      size = 0.35
    ) +
    geom_line(
      data = obs_df,
      aes(x = Date, y = Value),
      color = "black",
      linewidth = 0.22
    ) +
    labs(
      title = title_text,
      x = NULL,
      y = figure_flow_axis_label(DISPLAY_FLOW_SCALE)
    ) +
    scale_x_date(date_breaks = "1 year", date_labels = "%Y-%m") +
    coord_cartesian(ylim = ylim) +
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

  ggsave(out_file, plot = p, width = 12, height = 6, units = "in", dpi = 900)
}

component_summary_indices <- function(summary_probs) {
  probs <- suppressWarnings(as.numeric(summary_probs))
  if (length(probs) < 3L || any(!is.finite(probs))) {
    stop("Component summary probabilities must contain finite 2.5%, 50%, and 97.5% entries.", call. = FALSE)
  }
  targets <- c(Lower = 0.025, Median = 0.5, Upper = 0.975)
  idx <- vapply(targets, function(target) which.min(abs(probs - target)), integer(1))
  if (any(abs(probs[idx] - targets) > 1e-8)) {
    stop(
      sprintf(
        "Component summary probabilities do not match the 95%% band contract: %s",
        paste(probs, collapse = ", ")
      ),
      call. = FALSE
    )
  }
  idx
}

build_component_df <- function(
    component,
    idx,
    q_d_50,
    q_d_05,
    q_d_95,
    shift_map = NULL,
    summary_probs = COMPONENT_SUMMARY_PROBS) {
  summary_idx <- component_summary_indices(summary_probs)
  build_quantile_df <- function(arr, component, idx, date_vec, quantile_name) {
    vals <- matrix(arr[component, idx, , drop = FALSE], nrow = length(idx), ncol = dim(arr)[3])
    shift_vec <- shift_map[[quantile_name]] %||% rep(0, length(idx))
    tibble(
      Date = as.Date(date_vec[idx]),
      Quantile = quantile_name,
      Lower = vals[, summary_idx[["Lower"]]] + shift_vec,
      Median = vals[, summary_idx[["Median"]]] + shift_vec,
      Upper = vals[, summary_idx[["Upper"]]] + shift_vec
    )
  }

  bind_rows(
    build_quantile_df(q_d_50, component, idx, dates_ts_usgs, "50th"),
    build_quantile_df(q_d_05, component, idx, dates_ts_usgs, "5th"),
    build_quantile_df(q_d_95, component, idx, dates_ts_usgs, "95th")
  )
}

build_trend_mean_shift_map <- function(theta_50, theta_05, theta_95, idx, trend_component = 1L) {
  shift_for <- function(theta_arr) {
    mat <- theta_arr[trend_component, idx, , drop = TRUE]
    if (is.null(dim(mat))) {
      return(rep(as.numeric(mat), length(idx)))
    }
    rowMeans(mat, na.rm = TRUE)
  }
  list(
    "50th" = shift_for(theta_50),
    "5th" = shift_for(theta_05),
    "95th" = shift_for(theta_95)
  )
}

render_component_quantiles <- function(comp_df, obs_df, time_cuts, ylab, title_text, ylim, out_file) {
  shade_periods <- tibble(
    xmin = as.Date(dates_ts_usgs[time_cuts[c(1, 3)]]),
    xmax = as.Date(dates_ts_usgs[time_cuts[c(2, 4)]]),
    period = c("Dry", "Rainy"),
    fill = c("#ffeead", "#c9e4f6")
  )

  col_50 <- "#238b45"
  band_50 <- "#b2df8a"
  col_05 <- "#b2182b"
  band_05 <- "#fdbba1"
  col_95 <- "#2171b5"
  band_95 <- "#a6bddb"
  obs_line <- "#222222"
  obs_point <- "#222222"
  ribbon_alpha <- 0.11
  lnn <- 0.4

  p <- ggplot() +
    geom_rect(
      data = shade_periods,
      aes(xmin = xmin, xmax = xmax, ymin = -Inf, ymax = Inf, fill = period),
      alpha = 0.6,
      inherit.aes = FALSE,
      show.legend = FALSE
    ) +
    scale_fill_manual(values = setNames(shade_periods$fill, shade_periods$period)) +
    geom_ribbon(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_50,
      alpha = ribbon_alpha
    ) +
    geom_ribbon(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_05,
      alpha = ribbon_alpha
    ) +
    geom_ribbon(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, ymin = Lower, ymax = Upper),
      fill = band_95,
      alpha = ribbon_alpha
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Median),
      color = col_50,
      linewidth = lnn
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Median),
      color = col_05,
      linewidth = lnn
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Median),
      color = col_95,
      linewidth = lnn
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Lower),
      color = "green",
      linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "50th"),
      aes(x = Date, y = Upper),
      color = "green",
      linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Lower),
      color = "red",
      linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "5th"),
      aes(x = Date, y = Upper),
      color = "red",
      linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Lower),
      color = "blue",
      linewidth = 0.1
    ) +
    geom_line(
      data = comp_df %>% filter(Quantile == "95th"),
      aes(x = Date, y = Upper),
      color = "blue",
      linewidth = 0.1
    ) +
    geom_line(data = obs_df, aes(x = Date, y = Value), color = obs_line, linewidth = 0.1) +
    geom_point(data = obs_df, aes(x = Date, y = Value), color = obs_point, size = 0.1, alpha = 0.95) +
    annotate(
      "text",
      x = shade_periods$xmin + (shade_periods$xmax - shade_periods$xmin) / 2,
      y = ylim[1] + 0.01 * diff(ylim),
      label = shade_periods$period,
      size = 3.4,
      color = "#565656",
      fontface = "italic"
    ) +
    labs(title = title_text, x = NULL, y = ylab) +
    coord_cartesian(ylim = ylim, expand = TRUE) +
    scale_x_date(date_breaks = "24 months", date_labels = "%Y-%m") +
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

if (!is.null(state_summary_path)) {
  message("Loading retained historical-support state summary...")
  cached <- readRDS(state_summary_path)
  xbs_retro <- cached$xbs_retro
  q_d_50 <- cached$q_d_50
  q_d_05 <- cached$q_d_05
  q_d_95 <- cached$q_d_95
  time_cuts <- cached$time_cuts
  trend_shift_map <- cached$trend_shift_map %||% NULL
  component_summary_probs <- cached$component_summary_probs %||% COMPONENT_SUMMARY_PROBS
  cached_internal_scale <- cached$internal_flow_scale %||% NULL
  if (is.null(trend_shift_map)) {
    stop(
      sprintf(
        "Retained historical-support state summary is missing trend_shift_map: %s",
        state_summary_path
      ),
      call. = FALSE
    )
  }
  if (!identical(normalizePath(state_summary_path, mustWork = TRUE), normalizePath(state_cache_path, mustWork = FALSE))) {
    saveRDS(cached, state_cache_path)
  }
  scale_mismatch <- !is.null(cached_internal_scale) && !identical(cached_internal_scale, INTERNAL_FLOW_SCALE)
  if (scale_mismatch && !have_q_paths) {
    stop(
      sprintf(
        paste(
          "Retained historical-support state summary uses internal scale '%s',",
          "but the requested render contract is '%s' and fit artifacts are unavailable to rebuild the cache."
        ),
        cached_internal_scale,
        INTERNAL_FLOW_SCALE
      ),
      call. = FALSE
    )
  }
  rebuild_state_cache <- (is.null(cached_internal_scale) || scale_mismatch) && have_q_paths
  if (!is.null(cached_internal_scale) && !scale_mismatch) {
    STATE_INTERNAL_FLOW_SCALE <- cached_internal_scale
  }
} else {
  rebuild_state_cache <- !file.exists(state_cache_path)
}

if (!rebuild_state_cache) {
  message("Loading cached historical-support state summaries...")
  cached <- readRDS(state_cache_path)
  xbs_retro <- cached$xbs_retro
  q_d_50 <- cached$q_d_50
  q_d_05 <- cached$q_d_05
  q_d_95 <- cached$q_d_95
  time_cuts <- cached$time_cuts
  trend_shift_map <- cached$trend_shift_map %||% NULL
  component_summary_probs <- cached$component_summary_probs %||% COMPONENT_SUMMARY_PROBS
  cached_internal_scale <- cached$internal_flow_scale %||% NULL
  scale_mismatch <- !is.null(cached_internal_scale) && !identical(cached_internal_scale, INTERNAL_FLOW_SCALE)
  if (is.null(trend_shift_map) || is.null(cached_internal_scale) || scale_mismatch) {
    message("Cached historical-support state summaries predate the current trend-shift/scale contract. Rebuilding cache...")
    rebuild_state_cache <- TRUE
  } else {
    STATE_INTERNAL_FLOW_SCALE <- cached_internal_scale
  }
}

if (rebuild_state_cache) {
  message("Loading only the state objects needed for the support figures...")
  load_selected_objects(
    q_paths[[1]],
    c("new.theta.out_5_exAL_synth_DISC", "samp.theta_5_exAL_synth_DISC")
  )
  load_selected_objects(q_paths[[2]], c("new.theta.out_20_exAL_synth_DISC"))
  load_selected_objects(q_paths[[3]], c("new.theta.out_35_exAL_synth_DISC"))
  load_selected_objects(
    q_paths[[4]],
    c("new.theta.out_50_exAL_synth_DISC", "samp.theta_50_exAL_synth_DISC")
  )
  load_selected_objects(q_paths[[5]], c("new.theta.out_65_exAL_synth_DISC"))
  load_selected_objects(q_paths[[6]], c("new.theta.out_80_exAL_synth_DISC"))
  load_selected_objects(
    q_paths[[7]],
    c("new.theta.out_95_exAL_synth_DISC", "samp.theta_95_exAL_synth_DISC")
  )
  message("Building historical-support state summaries from current run...")
  xbs_retro <- build_xbs_retro()
  rm(
    new.theta.out_5_exAL_synth_DISC,
    new.theta.out_20_exAL_synth_DISC,
    new.theta.out_35_exAL_synth_DISC,
    new.theta.out_50_exAL_synth_DISC,
    new.theta.out_65_exAL_synth_DISC,
    new.theta.out_80_exAL_synth_DISC,
    new.theta.out_95_exAL_synth_DISC
  )
  invisible(gc())
  q_d_50 <- fast_prepare_quantile_data(samp.theta_50_exAL_synth_DISC$samp_theta, probs = c(0.975, 0.5, 0.025), type = 7L)
  q_d_05 <- fast_prepare_quantile_data(samp.theta_5_exAL_synth_DISC$samp_theta, probs = c(0.975, 0.5, 0.025), type = 7L)
  q_d_95 <- fast_prepare_quantile_data(samp.theta_95_exAL_synth_DISC$samp_theta, probs = c(0.975, 0.5, 0.025), type = 7L)
  component_summary_probs <- COMPONENT_SUMMARY_PROBS
  idx_component <- ceiling(TT / 10):TT
  trend_shift_map <- build_trend_mean_shift_map(
    theta_50 = samp.theta_50_exAL_synth_DISC$samp_theta,
    theta_05 = samp.theta_5_exAL_synth_DISC$samp_theta,
    theta_95 = samp.theta_95_exAL_synth_DISC$samp_theta,
    idx = idx_component,
    trend_component = 1L
  )
  rm(
    samp.theta_5_exAL_synth_DISC,
    samp.theta_50_exAL_synth_DISC,
    samp.theta_95_exAL_synth_DISC
  )
  invisible(gc())
  time_cuts <- resolve_time_cuts(timestamps = timestamps, cutoff_date = as.Date(cutoff_date), context = "current_model_output_support")
  saveRDS(
    list(
      xbs_retro = xbs_retro,
      q_d_50 = q_d_50,
      q_d_05 = q_d_05,
      q_d_95 = q_d_95,
      time_cuts = time_cuts,
      trend_shift_map = trend_shift_map,
      component_summary_probs = component_summary_probs,
      internal_flow_scale = STATE_INTERNAL_FLOW_SCALE,
      display_flow_scale = DISPLAY_FLOW_SCALE
    ),
    state_cache_path
  )
}

render_quantile_window(
  xbs_retro = xbs_retro,
  idx = time_cuts[1]:time_cuts[2],
  title_text = "Quantile Dynamics: 2012–2016",
  out_file = file.path(out_dir, "All_exal_2012-2016_DISC.png"),
  ylim_override = c(0, 7)
)
render_quantile_window(
  xbs_retro = xbs_retro,
  idx = time_cuts[3]:time_cuts[4],
  title_text = "Quantile Dynamics: 2017–2019",
  out_file = file.path(out_dir, "All_exal_2017-2019_DISC.png"),
  ylim_override = c(0, 7)
)
render_quantile_window(
  xbs_retro = xbs_retro,
  idx = time_cuts[3]:time_cuts[4],
  title_text = "Quantile Dynamics: 2017–2019",
  out_file = file.path(out_dir, "All_exal_2017-2019_DISC_fullrange.png"),
  ylim_override = c(0, 20)
)

idx_component <- ceiling(TT / 10):TT
obs_df <- tibble(Date = as.Date(dates_ts_usgs[idx_component]), Value = Y[1, idx_component])
comp_df <- build_component_df(
  component = 6,
  idx = idx_component,
  q_d_50 = q_d_50,
  q_d_05 = q_d_05,
  q_d_95 = q_d_95,
  shift_map = trend_shift_map,
  summary_probs = component_summary_probs
)
obs_df <- obs_df %>% mutate(Value = convert_internal_flow_to_display(Value))
comp_df <- comp_df %>%
  mutate(
    Lower = convert_internal_flow_to_display(Lower),
    Median = convert_internal_flow_to_display(Median),
    Upper = convert_internal_flow_to_display(Upper)
  )
render_component_quantiles(
  comp_df = comp_df,
  obs_df = obs_df,
  time_cuts = time_cuts,
  ylab = figure_flow_axis_label(DISPLAY_FLOW_SCALE),
  title_text = "Long-cycle Component Evolution: 1991–2022",
  ylim = compute_display_ylim(c(comp_df$Lower, comp_df$Upper, obs_df$Value), include_zero = TRUE),
  out_file = file.path(out_dir, "80_component_1991_2022.png")
)

meta <- list(
  workflow_root = project_root,
  multivar_run_root = run_root,
  cutoff_date = cutoff_date,
  forecast_start_date = forecast_start_date,
  rendered_files = c(
    "All_exal_2012-2016_DISC.png",
    "All_exal_2017-2019_DISC.png",
    "All_exal_2017-2019_DISC_fullrange.png",
    "80_component_1991_2022.png"
  ),
  display_flow_scale = DISPLAY_FLOW_SCALE,
  internal_flow_scale = STATE_INTERNAL_FLOW_SCALE,
  component_display_contract = "long-cycle component shifted by posterior mean trend level",
  component_summary_probs = as.numeric(component_summary_probs),
  time_cuts = as.integer(time_cuts),
  time_cut_dates = as.character(as.Date(timestamps[time_cuts])),
  rendered_at_utc = format(Sys.time(), tz = "UTC", usetz = TRUE)
)
writeLines(jsonlite::toJSON(meta, auto_unbox = TRUE, pretty = TRUE), file.path(out_dir, "render_metadata.json"))
stale_helper_files <- file.path(out_dir, c("data_cbind_tY_X.rds", "data_cbind_tY_X.csv", "timestamps.csv"))
unlink(stale_helper_files[file.exists(stale_helper_files)])
message("Rendered current-model historical support figures successfully.")
