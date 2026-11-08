###############################################################################
# Helper functions (core)
# Inputs:
#   - Data/matrix objects passed from later modules
# Outputs:
#   - Utility functions for model computations and checks
# Dependencies:
#   - Base R + Matrix + dlm-related functions
###############################################################################

if (!exists("%||%", mode = "function", inherits = TRUE)) {
  `%||%` <- function(x, y) {
    if (is.null(x)) y else x
  }
}

# Function to check if a matrix is positive definite
is_positive_definite <- function(x) {
  eigenvalues <- eigen(x)$values
  return(all(eigenvalues > 0))
}

# Function to compute inverse or square root of inverse using Cholesky Decomposition
compute_cholesky <- function(q, compute_sqrt_inverse = FALSE) {
  if (!is_positive_definite(q)) {
    stop("The matrix is not positive definite.")
  }
  
  # Compute Cholesky decomposition
  chol_decomp <- chol(as.matrix(q))
  
  # Convert to Matrix class to use with chol2inv
  U <- Matrix(chol_decomp, sparse = TRUE)
  
  # Compute inverse using Cholesky decomposition
  inv_q <- chol2inv(U)
  
  if (!compute_sqrt_inverse) {
    return(list(inverse = inv_q))
  } else {
    # Compute square root of the inverse
    # The square root of the inverse in this context is the inverse of the upper triangular matrix U
    sqrt_inv_q <- solve(U)
    
    # Check if the square root of the inverse times itself results in the inverse
    sqrt_inv_q_product <- sqrt_inv_q %*% t(sqrt_inv_q)
    is_correct <- all.equal(sqrt_inv_q_product, inv_q, tolerance = 1e-12)
    
    return(list(inverse = inv_q, sqrt_inverse = sqrt_inv_q, check = is_correct))
  }
}

# Stable sort policy for forecast sample slices.
# Default keeps NA values to preserve vector length during array-slice assignment.
sort_keep_na <- function(x, keep_na = NULL) {
  if (is.null(keep_na)) {
    keep_na_env <- Sys.getenv("ENV_SORT_KEEP_NA", "TRUE")
    keep_na <- isTRUE(as.logical(keep_na_env))
  }
  if (isTRUE(keep_na)) {
    return(sort(x, na.last = TRUE))
  }
  sort(x)
}

# Sort a vector while guaranteeing exact output length for safe array-slice writes.
sort_to_len <- function(x, target_len, keep_na = NULL, fill = NA_real_, context = NULL) {
  if (length(target_len) != 1L || is.na(target_len) || target_len < 0) {
    stop(sprintf("sort_to_len target_len must be a single non-negative integer; got: %s", paste(target_len, collapse = ",")))
  }

  target_len <- as.integer(target_len)
  sorted <- sort_keep_na(as.vector(x), keep_na = keep_na)
  cur_len <- length(sorted)

  if (cur_len == target_len) {
    return(sorted)
  }

  if (cur_len == 0L && target_len > 0L) {
    if (!is.null(context) && nzchar(context)) {
      warning(sprintf("sort_to_len received empty input for %s; padding to target length %d", context, target_len), call. = FALSE)
    }
    return(rep(fill, target_len))
  }

  if (cur_len < target_len) {
    return(c(sorted, rep(fill, target_len - cur_len)))
  }

  sorted[seq_len(target_len)]
}

# Shared date helpers used by both full and smoke-fast post modules.
daily_dates_for_n <- function(start_date, n_days, context = "dates") {
  start_date <- as.Date(start_date)
  if (length(start_date) != 1L || !is.finite(start_date)) {
    stop(sprintf("[%s] start_date must be a valid scalar Date.", context), call. = FALSE)
  }
  n_use <- as.integer(n_days[[1]])
  if (!is.finite(n_use) || n_use <= 0L) {
    stop(
      sprintf("[%s] n_days must be a positive finite integer, got '%s'.", context, as.character(n_days[[1]])),
      call. = FALSE
    )
  }
  seq(start_date, by = "1 day", length.out = n_use)
}

daily_dates_for_matrix_rows <- function(mat, start_date, context = "dates.rows") {
  if (is.null(dim(mat)) || length(dim(mat)) != 2L) {
    stop(sprintf("[%s] expected a 2D object for row-based date construction.", context), call. = FALSE)
  }
  daily_dates_for_n(start_date = start_date, n_days = nrow(mat), context = context)
}

daily_dates_for_matrix_cols <- function(mat, start_date, context = "dates.cols") {
  if (is.null(dim(mat)) || length(dim(mat)) != 2L) {
    stop(sprintf("[%s] expected a 2D object for column-based date construction.", context), call. = FALSE)
  }
  daily_dates_for_n(start_date = start_date, n_days = ncol(mat), context = context)
}

post_default_quantile_labels <- function() {
  c("05", "20", "35", "50", "65", "80", "95")
}

post_requested_quantile_labels <- function(
  default = post_default_quantile_labels(),
  env_key = "UNIFIED_FIT_QUANTILE_LABELS"
) {
  raw <- trimws(unlist(strsplit(Sys.getenv(env_key, ""), ",", fixed = TRUE), use.names = FALSE))
  raw <- raw[nzchar(raw)]
  if (length(raw) == 0L) {
    return(as.character(default))
  }

  numeric_labels <- suppressWarnings(as.integer(round(as.numeric(raw))))
  numeric_labels <- numeric_labels[is.finite(numeric_labels)]
  if (length(numeric_labels) == 0L) {
    return(as.character(default))
  }

  sprintf("%02d", sort(unique(as.integer(numeric_labels))))
}

post_requested_quantile_spec <- function(
  default = post_default_quantile_labels(),
  env_key = "UNIFIED_FIT_QUANTILE_LABELS"
) {
  labels <- post_requested_quantile_labels(default = default, env_key = env_key)
  ints <- as.integer(labels)
  list(
    labels = labels,
    tags = as.character(ints),
    probs = as.numeric(ints) / 100
  )
}

safe_exp_limit <- function(margin = 5) {
  margin <- suppressWarnings(as.numeric(margin[[1L]]))
  if (!is.finite(margin) || margin < 0) margin <- 5
  log(.Machine$double.xmax) - margin
}

post_write_exp_guard_report <- function(summary, report_path) {
  if (is.null(report_path) || !nzchar(report_path)) {
    return(invisible(FALSE))
  }
  dir.create(dirname(report_path), recursive = TRUE, showWarnings = FALSE)
  lines <- c(
    sprintf("context=%s", as.character(summary$context)),
    sprintf("overflow_policy=%s", as.character(summary$overflow_policy)),
    sprintf("safe_exp_limit=%0.6f", as.numeric(summary$safe_exp_limit)),
    sprintf("max_input=%0.6f", as.numeric(summary$max_input)),
    sprintf("n_input_nonfinite=%d", as.integer(summary$n_input_nonfinite)),
    sprintf("n_overflow_risk=%d", as.integer(summary$n_overflow_risk)),
    sprintf("n_capped=%d", as.integer(summary$n_capped))
  )
  writeLines(lines, con = report_path, useBytes = TRUE)
  invisible(TRUE)
}

post_transform_loglog1p_array <- function(
  arr,
  context = "latent_array",
  margin = 5,
  overflow_policy = c("error", "cap"),
  report_path = NULL
) {
  overflow_policy <- match.arg(overflow_policy)
  if (!is.numeric(arr) || is.null(dim(arr)) || length(dim(arr)) < 2L) {
    stop(sprintf("[EXP_INPUT_SHAPE] %s must be a numeric array with at least 2 dimensions.", context), call. = FALSE)
  }

  finite_mask <- is.finite(arr)
  n_input_nonfinite <- sum(!finite_mask)
  if (n_input_nonfinite > 0L) {
    stop(sprintf("[EXP_INPUT_NONFINITE] %s contains %d non-finite latent values.", context, as.integer(n_input_nonfinite)), call. = FALSE)
  }

  finite_vals <- as.numeric(arr[finite_mask])
  if (length(finite_vals) == 0L) {
    stop(sprintf("[EXP_INPUT_EMPTY] %s has no finite values to exponentiate.", context), call. = FALSE)
  }

  limit <- safe_exp_limit(margin = margin)
  max_val <- max(finite_vals, na.rm = TRUE)
  if (!is.finite(max_val)) {
    stop(sprintf("[EXP_INPUT_NONFINITE] %s max latent value is non-finite.", context), call. = FALSE)
  }

  overflow_mask <- finite_mask & (arr > limit)
  n_overflow_risk <- sum(overflow_mask)
  n_capped <- 0L
  arr_use <- arr
  if (n_overflow_risk > 0L) {
    if (identical(overflow_policy, "error")) {
      stop(
        sprintf(
          "[EXP_OVERFLOW_RISK] %s contains %d latent values above the safe exp limit %.6f (max_input=%.6f).",
          context,
          as.integer(n_overflow_risk),
          limit,
          max_val
        ),
        call. = FALSE
      )
    }
    arr_use[overflow_mask] <- limit
    n_capped <- as.integer(n_overflow_risk)
    warning(
      sprintf(
        "[EXP_OVERFLOW_CAP] %s capped %d latent values above the safe exp limit %.6f (max_input=%.6f).",
        context,
        n_capped,
        limit,
        max_val
      ),
      call. = FALSE
    )
  }

  summary <- list(
    context = as.character(context),
    overflow_policy = as.character(overflow_policy),
    safe_exp_limit = as.numeric(limit),
    max_input = as.numeric(max_val),
    n_input_nonfinite = as.integer(n_input_nonfinite),
    n_overflow_risk = as.integer(n_overflow_risk),
    n_capped = as.integer(n_capped)
  )
  post_write_exp_guard_report(summary, report_path)

  list(
    values = exp(arr_use),
    summary = summary
  )
}

assert_exp_safe_matrix <- function(mat, context = "latent_matrix", margin = 5) {
  if (!is.numeric(mat) || is.null(dim(mat)) || length(dim(mat)) != 2L) {
    stop(sprintf("[EXP_INPUT_SHAPE] %s must be a numeric 2D matrix.", context), call. = FALSE)
  }

  finite_vals <- as.numeric(mat[is.finite(mat)])
  if (length(finite_vals) == 0L) {
    stop(sprintf("[EXP_INPUT_EMPTY] %s has no finite values to exponentiate.", context), call. = FALSE)
  }

  limit <- safe_exp_limit(margin = margin)
  max_val <- max(finite_vals, na.rm = TRUE)
  if (!is.finite(max_val)) {
    stop(sprintf("[EXP_INPUT_NONFINITE] %s max latent value is non-finite.", context), call. = FALSE)
  }
  if (max_val > limit) {
    stop(
      sprintf(
        "[EXP_OVERFLOW_RISK] %s max latent value %.6f exceeds safe exp limit %.6f.",
        context,
        max_val,
        limit
      ),
      call. = FALSE
    )
  }

  invisible(list(max = max_val, limit = limit))
}

post_transform_loglog1p_to_log1p_mat <- function(sample_mat, context = "sample_mat") {
  if (!is.matrix(sample_mat)) {
    sample_mat <- as.matrix(sample_mat)
  }
  if (!is.numeric(sample_mat) || length(dim(sample_mat)) != 2L) {
    stop(sprintf("[%s_SHAPE] sample_mat must be a numeric 2D matrix.", context), call. = FALSE)
  }
  post_transform_loglog1p_array(
    sample_mat,
    context = paste0(context, ".loglog1p"),
    overflow_policy = "error"
  )$values
}

post_resolve_analysis_scale_post_internal <- local({
  cached <- NULL

  function(default = "log1p_cms") {
    if (!is.null(cached)) {
      return(cached)
    }

    env_scale <- Sys.getenv("UNIFIED_ANALYSIS_SCALE_POST_INTERNAL", "")
    if (nzchar(env_scale)) {
      cached <<- env_scale
      return(cached)
    }

    opt_scale <- getOption("unified.analysis_scale_post_internal", NULL)
    if (!is.null(opt_scale) && nzchar(as.character(opt_scale))) {
      cached <<- as.character(opt_scale)
      return(cached)
    }

    run_root <- Sys.getenv("UNIFIED_RUN_ROOT", "")
    resolved_config_path <- if (nzchar(run_root)) file.path(run_root, "resolved_config.yaml") else ""
    if (nzchar(resolved_config_path) && file.exists(resolved_config_path) && requireNamespace("yaml", quietly = TRUE)) {
      cfg <- tryCatch(yaml::read_yaml(resolved_config_path), error = function(e) NULL)
      if (is.list(cfg) && is.list(cfg$scale_contract)) {
        cfg_scale <- as.character(cfg$scale_contract$analysis_scale_post_internal %||% "")
        if (nzchar(cfg_scale)) {
          cached <<- cfg_scale
          return(cached)
        }
      }
    }

    cached <<- as.character(default)
    cached
  }
})

post_flow_scale_label <- function(scale = NULL) {
  scale <- as.character(scale %||% post_resolve_analysis_scale_post_internal())
  if (identical(scale, "raw_cms")) return("raw cms")
  if (identical(scale, "log_cms")) return("log(cms)")
  if (identical(scale, "log1p_cms")) return("log1p cms")
  if (identical(scale, "log_log_cms")) return("log(log(cms))")
  if (identical(scale, "log_log1p_cms")) return("log(log1p(cms))")
  scale
}

post_transform_usgs_log1p_truth_to_analysis_scale <- function(
  log1p_values,
  target_scale = NULL,
  context = "usgs_truth"
) {
  x <- suppressWarnings(as.numeric(log1p_values))
  target_scale <- as.character(target_scale %||% post_resolve_analysis_scale_post_internal())
  if (exists("unified_assert_known_scale", inherits = TRUE)) {
    unified_assert_known_scale(target_scale, "target_scale")
  }

  out <- rep(NA_real_, length(x))
  finite <- is.finite(x)
  if (!any(finite)) {
    return(out)
  }

  if (identical(target_scale, "log1p_cms")) {
    out[finite] <- x[finite]
    return(out)
  }

  if (identical(target_scale, "log_log1p_cms")) {
    positive <- finite & x > 0
    out[positive] <- log(x[positive])
    return(out)
  }

  if (!exists("unified_convert_scale", inherits = TRUE)) {
    stop(sprintf("[%s_SCALE_HELPER] unified_convert_scale is required for target_scale=%s.", context, target_scale), call. = FALSE)
  }
  converted <- tryCatch(
    unified_convert_scale(x[finite], from_scale = "log1p_cms", to_scale = target_scale),
    error = function(e) e
  )
  if (inherits(converted, "error")) {
    stop(sprintf("[%s_SCALE_CONVERT] %s", context, conditionMessage(converted)), call. = FALSE)
  }
  out[finite] <- converted
  out
}

post_write_scale_transform_report <- function(summary, report_path = NULL) {
  if (is.null(report_path) || !nzchar(report_path)) {
    return(invisible(FALSE))
  }
  dir.create(dirname(report_path), recursive = TRUE, showWarnings = FALSE)
  lines <- c(
    sprintf("context=%s", as.character(summary$context %||% "")),
    sprintf("from_scale=%s", as.character(summary$from_scale %||% "")),
    sprintf("to_scale=%s", as.character(summary$to_scale %||% "")),
    sprintf("transform=%s", as.character(summary$transform %||% "")),
    sprintf("n_input_nonfinite=%d", as.integer(summary$n_input_nonfinite %||% 0L)),
    sprintf("n_output_nonfinite=%d", as.integer(summary$n_output_nonfinite %||% 0L)),
    sprintf("min_input=%s", format(as.numeric(summary$min_input %||% NA_real_), digits = 15)),
    sprintf("max_input=%s", format(as.numeric(summary$max_input %||% NA_real_), digits = 15)),
    sprintf("min_output=%s", format(as.numeric(summary$min_output %||% NA_real_), digits = 15)),
    sprintf("max_output=%s", format(as.numeric(summary$max_output %||% NA_real_), digits = 15))
  )
  writeLines(lines, con = report_path, useBytes = TRUE)
  invisible(TRUE)
}

post_transform_internal_array_to_log1p <- function(
  arr,
  from_scale = NULL,
  context = "internal_array",
  report_path = NULL
) {
  if (!is.numeric(arr) || is.null(dim(arr)) || length(dim(arr)) < 2L) {
    stop(sprintf("[%s_SHAPE] expected a numeric array with at least 2 dimensions.", context), call. = FALSE)
  }

  from_scale <- as.character(from_scale %||% post_resolve_analysis_scale_post_internal())
  if (exists("unified_assert_known_scale", inherits = TRUE)) {
    unified_assert_known_scale(from_scale, "from_scale")
  }

  finite_mask <- is.finite(arr)
  n_input_nonfinite <- sum(!finite_mask)
  if (n_input_nonfinite > 0L) {
    stop(sprintf("[%s_NONFINITE] input contains %d non-finite values.", context, as.integer(n_input_nonfinite)), call. = FALSE)
  }

  min_input <- min(arr[finite_mask], na.rm = TRUE)
  max_input <- max(arr[finite_mask], na.rm = TRUE)

  if (identical(from_scale, "log1p_cms")) {
    out <- arr
    summary <- list(
      context = as.character(context),
      from_scale = from_scale,
      to_scale = "log1p_cms",
      transform = "identity",
      n_input_nonfinite = as.integer(n_input_nonfinite),
      n_output_nonfinite = 0L,
      min_input = as.numeric(min_input),
      max_input = as.numeric(max_input),
      min_output = as.numeric(min_input),
      max_output = as.numeric(max_input)
    )
    post_write_scale_transform_report(summary, report_path)
    return(list(values = out, summary = summary))
  }

  if (identical(from_scale, "log_log1p_cms")) {
    out <- post_transform_loglog1p_array(
      arr,
      context = paste0(context, ".loglog1p"),
      overflow_policy = "cap",
      report_path = report_path
    )
    out$summary$from_scale <- from_scale
    out$summary$to_scale <- "log1p_cms"
    out$summary$transform <- "exp"
    return(out)
  }

  if (!exists("unified_convert_scale", inherits = TRUE)) {
    stop(sprintf("[%s_SCALE_HELPER] unified_convert_scale is required for from_scale=%s.", context, from_scale), call. = FALSE)
  }

  out <- array(
    unified_convert_scale(as.numeric(arr), from_scale = from_scale, to_scale = "log1p_cms"),
    dim = dim(arr),
    dimnames = dimnames(arr)
  )
  n_output_nonfinite <- sum(!is.finite(out))
  if (n_output_nonfinite > 0L) {
    stop(sprintf("[%s_OUTPUT_NONFINITE] converted output contains %d non-finite values.", context, as.integer(n_output_nonfinite)), call. = FALSE)
  }
  summary <- list(
    context = as.character(context),
    from_scale = from_scale,
    to_scale = "log1p_cms",
    transform = sprintf("unified_convert_scale(%s->log1p_cms)", from_scale),
    n_input_nonfinite = as.integer(n_input_nonfinite),
    n_output_nonfinite = as.integer(n_output_nonfinite),
    min_input = as.numeric(min_input),
    max_input = as.numeric(max_input),
    min_output = as.numeric(min(out[is.finite(out)], na.rm = TRUE)),
    max_output = as.numeric(max(out[is.finite(out)], na.rm = TRUE))
  )
  post_write_scale_transform_report(summary, report_path)
  list(values = out, summary = summary)
}

post_transform_internal_to_log1p_mat <- function(sample_mat, from_scale = NULL, context = "sample_mat", report_path = NULL) {
  if (!is.matrix(sample_mat)) {
    sample_mat <- as.matrix(sample_mat)
  }
  if (!is.numeric(sample_mat) || length(dim(sample_mat)) != 2L) {
    stop(sprintf("[%s_SHAPE] sample_mat must be a numeric 2D matrix.", context), call. = FALSE)
  }
  post_transform_internal_array_to_log1p(
    sample_mat,
    from_scale = from_scale,
    context = context,
    report_path = report_path
  )$values
}

post_extract_ndlm_mean_sample_mat <- function(ndlm_raw, context = "ndlm.mean_sample_mat") {
  sample_mat <- NULL
  if (is.numeric(ndlm_raw) && !is.null(dim(ndlm_raw)) && length(dim(ndlm_raw)) == 3L &&
      dim(ndlm_raw)[1] >= 1L && dim(ndlm_raw)[2] > 0L && dim(ndlm_raw)[3] > 1L) {
    sample_mat <- t(ndlm_raw[1, , , drop = FALSE][1, , ])
  } else if (is.matrix(ndlm_raw) && is.numeric(ndlm_raw) && nrow(ndlm_raw) > 1L && ncol(ndlm_raw) > 0L) {
    sample_mat <- ndlm_raw
  }

  if (is.null(sample_mat)) {
    stop(sprintf("[%s_SHAPE] unable to extract NDLM mean sample matrix.", context), call. = FALSE)
  }
  if (!is.matrix(sample_mat)) {
    sample_mat <- as.matrix(sample_mat)
  }
  if (!is.numeric(sample_mat) || length(dim(sample_mat)) != 2L || nrow(sample_mat) <= 1L || ncol(sample_mat) <= 0L) {
    stop(sprintf("[%s_SHAPE] NDLM mean sample matrix must be numeric [sample x horizon] with n_sample > 1.", context), call. = FALSE)
  }
  if (!all(is.finite(sample_mat))) {
    stop(sprintf("[%s_FINITE] NDLM mean sample matrix contains non-finite values.", context), call. = FALSE)
  }
  sample_mat
}

post_ndlm_predictive_draws <- function(
  ndlm_raw,
  sigma_draws,
  context = "ndlm.predictive",
  seed = 777L
) {
  mean_loglog1p <- post_extract_ndlm_mean_sample_mat(
    ndlm_raw,
    context = paste0(context, ".mean")
  )

  sigma_source_used <- "vector"
  if (is.matrix(sigma_draws) ||
      (!is.null(dim(sigma_draws)) && length(dim(sigma_draws)) == 2L)) {
    sigma_mat <- as.matrix(sigma_draws)
    if (!is.numeric(sigma_mat) || ncol(sigma_mat) < 1L) {
      stop(sprintf("[%s_SIGMA_SHAPE] sigma draw matrix must be numeric with ncol >= 1.", context), call. = FALSE)
    }
    sigma_row_idx <- 1L
    sigma_row_names <- rownames(sigma_mat)
    if (!is.null(sigma_row_names) && "usgs" %in% sigma_row_names) {
      sigma_row_idx <- match("usgs", sigma_row_names)
      sigma_source_used <- "matrix_row_usgs"
    } else {
      sigma_source_used <- "matrix_row_1"
    }
    sigma_vec <- suppressWarnings(as.numeric(sigma_mat[sigma_row_idx, , drop = TRUE]))
  } else {
    sigma_vec <- suppressWarnings(as.numeric(sigma_draws))
  }
  sigma_vec <- sigma_vec[is.finite(sigma_vec)]
  if (length(sigma_vec) < 1L) {
    stop(sprintf("[%s_SIGMA] sigma draws are missing or non-finite.", context), call. = FALSE)
  }
  if (any(sigma_vec < 0)) {
    stop(sprintf("[%s_SIGMA_NEG] sigma draws must be non-negative.", context), call. = FALSE)
  }

  n_eff <- min(nrow(mean_loglog1p), length(sigma_vec))
  if (!is.finite(n_eff) || n_eff <= 1L) {
    stop(sprintf("[%s_N_EFF] effective predictive sample size must exceed 1.", context), call. = FALSE)
  }
  mean_loglog1p <- mean_loglog1p[seq_len(n_eff), , drop = FALSE]
  sd_vec <- sqrt(sigma_vec[seq_len(n_eff)])

  had_seed <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
  if (had_seed) {
    old_seed <- get(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
  }
  on.exit({
    if (had_seed) {
      assign(".Random.seed", old_seed, envir = .GlobalEnv)
    } else if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
      rm(".Random.seed", envir = .GlobalEnv)
    }
  }, add = TRUE)

  set.seed(as.integer(seed))
  z <- matrix(stats::rnorm(length(mean_loglog1p)), nrow = n_eff, ncol = ncol(mean_loglog1p))
  predictive_loglog1p <- mean_loglog1p + sweep(z, 1L, sd_vec, `*`)
  predictive_log1p <- post_transform_loglog1p_to_log1p_mat(
    predictive_loglog1p,
    context = paste0(context, ".predictive")
  )

  list(
    mean_loglog1p = mean_loglog1p,
    predictive_loglog1p = predictive_loglog1p,
    predictive_log1p = predictive_log1p,
    sigma_sd = sd_vec,
    sigma_source_used = sigma_source_used
  )
}

post_build_ndlm_state_draw_array <- function(
  ndlm_obj,
  ranges,
  FF_list,
  n_samp,
  p_state = 7L,
  eps_reg = 0,
  seed = 777L,
  context = "ndlm.state_draws"
) {
  if (!is.list(ndlm_obj)) {
    stop(sprintf("[%s_OBJ] ndlm_obj must be a list.", context), call. = FALSE)
  }
  if (!is.list(ndlm_obj$sm_ens) || !is.list(ndlm_obj$sC_ens)) {
    stop(sprintf("[%s_FIELDS] ndlm_obj must contain sm_ens and sC_ens lists.", context), call. = FALSE)
  }
  ranges <- suppressWarnings(as.integer(ranges))
  if (length(ranges) < 1L || any(!is.finite(ranges)) || any(ranges < 1L)) {
    stop(sprintf("[%s_RANGES] ranges must be positive integers.", context), call. = FALSE)
  }
  if (!is.list(FF_list) || length(FF_list) < 1L) {
    stop(sprintf("[%s_FF] FF_list must be a non-empty list.", context), call. = FALSE)
  }
  n_samp <- suppressWarnings(as.integer(n_samp[[1L]]))
  if (!is.finite(n_samp) || n_samp <= 1L) {
    stop(sprintf("[%s_N_SAMP] n_samp must exceed 1.", context), call. = FALSE)
  }
  p_state <- suppressWarnings(as.integer(p_state[[1L]]))
  if (!is.finite(p_state) || p_state < 1L) {
    stop(sprintf("[%s_P_STATE] p_state must be >= 1.", context), call. = FALSE)
  }

  next_idx_block <- function(prev_idx, block_len) {
    block_len <- suppressWarnings(as.integer(block_len[[1L]]))
    start <- if (length(prev_idx) == 0L) 0L else as.integer(prev_idx[[length(prev_idx)]])
    if (!is.finite(block_len) || block_len <= 0L) return(integer(0))
    seq_len(block_len) + start
  }

  ks <- -diff(c(ranges, 0L))
  J <- min(length(ks), length(FF_list), length(ndlm_obj$sm_ens), length(ndlm_obj$sC_ens))
  if (J < 1L) {
    stop(sprintf("[%s_J] unable to resolve forecast segments.", context), call. = FALSE)
  }

  had_seed <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
  if (had_seed) {
    old_seed <- get(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
  }
  on.exit({
    if (had_seed) {
      assign(".Random.seed", old_seed, envir = .GlobalEnv)
    } else if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
      rm(".Random.seed", envir = .GlobalEnv)
    }
  }, add = TRUE)

  set.seed(as.integer(seed))
  xbs_ndlm <- array(NA_real_, c(1L, as.integer(ranges[[1L]]), n_samp))
  idx <- c(0L)

  for (j in seq_len(J)) {
    idx <- next_idx_block(idx, ks[J - j + 1L])
    if (length(idx) == 0L) next

    sm_j <- ndlm_obj$sm_ens[[j]]
    sC_j <- ndlm_obj$sC_ens[[j]]
    if (!is.numeric(sm_j) || is.null(dim(sm_j)) || length(dim(sm_j)) != 2L ||
        !is.numeric(sC_j) || is.null(dim(sC_j)) || length(dim(sC_j)) != 3L) {
      next
    }

    n_avail <- min(length(idx), ncol(sm_j), dim(sC_j)[3])
    if (!is.finite(n_avail) || n_avail <= 0L) next

    Ft <- FF_list[[j]][seq_len(min(p_state, nrow(FF_list[[j]]))), 1]
    for (tt in seq_len(n_avail)) {
      t_idx <- idx[[tt]]
      Mu <- sm_j[, tt]
      Sigma <- sC_j[, , tt]
      p_use <- min(length(Ft), length(Mu), nrow(Sigma), ncol(Sigma))
      if (!is.finite(p_use) || p_use <= 0L) next
      Ft_use <- matrix(Ft[seq_len(p_use)], ncol = 1L)
      S <- Sigma[seq_len(p_use), seq_len(p_use), drop = FALSE] + diag(p_use) * eps_reg
      mean_use <- as.numeric(crossprod(Ft_use, Mu[seq_len(p_use)]))
      var_use <- as.numeric(t(Ft_use) %*% S %*% Ft_use)
      sd_use <- sqrt(max(var_use, 0))
      xbs_ndlm[1L, t_idx, ] <- stats::rnorm(n = n_samp, mean = mean_use, sd = sd_use)
    }
  }

  xbs_ndlm
}

post_quantile_crossing_summary <- function(sample_cube, q_probs, context = "quantile.crossing") {
  if (!is.numeric(sample_cube) || is.null(dim(sample_cube)) || length(dim(sample_cube)) != 3L) {
    stop(sprintf("[%s_SHAPE] sample_cube must be numeric 3D [quantile x sample x horizon].", context), call. = FALSE)
  }
  q_probs <- as.numeric(q_probs)
  if (length(q_probs) != dim(sample_cube)[1]) {
    stop(sprintf("[%s_Q_LEN] q_probs length must match sample_cube quantile dimension.", context), call. = FALSE)
  }
  if (is.unsorted(q_probs)) {
    stop(sprintf("[%s_Q_ORDER] q_probs must be sorted ascending.", context), call. = FALSE)
  }

  horizon <- as.integer(dim(sample_cube)[3])
  per_time <- vector("list", horizon)
  for (h in seq_len(horizon)) {
    qmat <- sample_cube[, , h, drop = FALSE][, , 1L]
    finite_cols <- apply(qmat, 2L, function(x) all(is.finite(x)))
    qmat <- qmat[, finite_cols, drop = FALSE]
    if (ncol(qmat) < 1L) {
      per_time[[h]] <- data.frame(
        lead_day = as.integer(h),
        n_sample_paths = 0L,
        n_crossing_paths = 0L,
        crossing_rate = NA_real_,
        stringsAsFactors = FALSE
      )
      next
    }
    crossing <- apply(qmat, 2L, function(x) any(diff(as.numeric(x)) < 0))
    per_time[[h]] <- data.frame(
      lead_day = as.integer(h),
      n_sample_paths = as.integer(length(crossing)),
      n_crossing_paths = as.integer(sum(crossing, na.rm = TRUE)),
      crossing_rate = mean(crossing, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  }

  per_time_df <- do.call(rbind, per_time)
  list(
    per_time = per_time_df,
    summary = data.frame(
      n_horizon = as.integer(horizon),
      n_sample_paths_total = as.integer(sum(per_time_df$n_sample_paths, na.rm = TRUE)),
      n_crossing_paths_total = as.integer(sum(per_time_df$n_crossing_paths, na.rm = TRUE)),
      max_crossing_rate = if (nrow(per_time_df) > 0L) max(per_time_df$crossing_rate, na.rm = TRUE) else NA_real_,
      mean_crossing_rate = if (nrow(per_time_df) > 0L) mean(per_time_df$crossing_rate, na.rm = TRUE) else NA_real_,
      stringsAsFactors = FALSE
    )
  )
}

post_quantile_curve_from_sample_cube <- function(sample_cube, q_probs, context = "quantile.curve") {
  if (!is.numeric(sample_cube) || is.null(dim(sample_cube)) || length(dim(sample_cube)) != 3L) {
    stop(sprintf("[%s_SHAPE] sample_cube must be numeric 3D [quantile x sample x horizon].", context), call. = FALSE)
  }
  q_probs <- as.numeric(q_probs)
  if (length(q_probs) != dim(sample_cube)[1]) {
    stop(sprintf("[%s_Q_LEN] q_probs length must match sample_cube quantile dimension.", context), call. = FALSE)
  }
  if (is.unsorted(q_probs)) {
    stop(sprintf("[%s_Q_ORDER] q_probs must be sorted ascending.", context), call. = FALSE)
  }

  n_q <- dim(sample_cube)[1]
  horizon <- dim(sample_cube)[3]
  out <- matrix(NA_real_, nrow = n_q, ncol = horizon)
  rownames(out) <- sprintf("q_%0.2f", q_probs)

  for (i in seq_len(n_q)) {
    mat <- sample_cube[i, , , drop = TRUE]
    if (!is.matrix(mat)) {
      mat <- matrix(mat, nrow = dim(sample_cube)[2], ncol = dim(sample_cube)[3])
    }
    out[i, ] <- as.numeric(fast_col_quantiles_t(mat, probs = q_probs[i], na.rm = TRUE)[1, ])
  }

  out
}

post_quantile_curve_crossing_summary <- function(q_curve, q_probs, context = "quantile.curve.crossing") {
  if (!is.numeric(q_curve) || is.null(dim(q_curve)) || length(dim(q_curve)) != 2L) {
    stop(sprintf("[%s_SHAPE] q_curve must be numeric 2D [quantile x horizon].", context), call. = FALSE)
  }
  q_probs <- as.numeric(q_probs)
  if (length(q_probs) != nrow(q_curve)) {
    stop(sprintf("[%s_Q_LEN] q_probs length must match q_curve quantile dimension.", context), call. = FALSE)
  }
  if (is.unsorted(q_probs)) {
    stop(sprintf("[%s_Q_ORDER] q_probs must be sorted ascending.", context), call. = FALSE)
  }

  horizon <- ncol(q_curve)
  per_time <- vector("list", horizon)
  for (h in seq_len(horizon)) {
    vals <- as.numeric(q_curve[, h])
    neg_diffs <- diff(vals)
    bad <- neg_diffs[is.finite(neg_diffs) & neg_diffs < 0]
    per_time[[h]] <- data.frame(
      lead_day = as.integer(h),
      n_quantiles = as.integer(length(vals)),
      has_crossing = as.integer(length(bad) > 0L),
      n_crossings = as.integer(length(bad)),
      max_negative_gap = if (length(bad) > 0L) min(bad) else 0,
      stringsAsFactors = FALSE
    )
  }

  per_time_df <- do.call(rbind, per_time)
  list(
    per_time = per_time_df,
    summary = data.frame(
      n_horizon = as.integer(horizon),
      n_times_with_crossing = as.integer(sum(per_time_df$has_crossing, na.rm = TRUE)),
      crossing_share = mean(per_time_df$has_crossing, na.rm = TRUE),
      max_negative_gap = if (nrow(per_time_df) > 0L) min(per_time_df$max_negative_gap, na.rm = TRUE) else NA_real_,
      stringsAsFactors = FALSE
    )
  )
}

post_quantile_curve_long_values <- function(q_curve, q_probs, horizon = ncol(q_curve), context = "quantile.curve.long_values") {
  if (!is.numeric(q_curve) || is.null(dim(q_curve)) || length(dim(q_curve)) != 2L) {
    stop(sprintf("[%s_SHAPE] q_curve must be numeric 2D [quantile x horizon].", context), call. = FALSE)
  }
  q_probs <- as.numeric(q_probs)
  if (length(q_probs) != nrow(q_curve)) {
    stop(sprintf("[%s_Q_LEN] q_probs length must match q_curve quantile dimension.", context), call. = FALSE)
  }
  horizon <- as.integer(horizon[[1L]])
  if (!is.finite(horizon) || horizon < 1L || ncol(q_curve) != horizon) {
    stop(sprintf("[%s_HORIZON] q_curve horizon mismatch.", context), call. = FALSE)
  }
  # R stores matrices column-major, so this preserves the desired
  # lead-major/quantile-minor ordering:
  # lead1: q1,q2,... ; lead2: q1,q2,... ; ...
  as.numeric(q_curve)
}

post_exdqlm_synthesize_from_sample_cube <- function(
  sample_cube,
  q_probs,
  n_samp = 1000L,
  seed = NULL,
  enforce_isotonic = TRUE,
  rearrange = TRUE,
  grid_M = 1001L,
  context = "exdqlm.synthesize"
) {
  if (!requireNamespace("exdqlm", quietly = TRUE)) {
    stop(sprintf("[%s_PACKAGE] package 'exdqlm' is required for univariate synthesis repair.", context), call. = FALSE)
  }
  if (!is.numeric(sample_cube) || is.null(dim(sample_cube)) || length(dim(sample_cube)) != 3L) {
    stop(sprintf("[%s_SHAPE] sample_cube must be numeric 3D [quantile x sample x horizon].", context), call. = FALSE)
  }
  q_probs <- as.numeric(q_probs)
  if (length(q_probs) != dim(sample_cube)[1]) {
    stop(sprintf("[%s_Q_LEN] q_probs length must match sample_cube quantile dimension.", context), call. = FALSE)
  }
  if (length(q_probs) < 2L) {
    stop(sprintf("[%s_Q_MIN] at least two quantile fits are required for synthesis.", context), call. = FALSE)
  }
  if (is.unsorted(q_probs)) {
    stop(sprintf("[%s_Q_ORDER] q_probs must be sorted ascending.", context), call. = FALSE)
  }

  horizon <- as.integer(dim(sample_cube)[3])
  draws_list <- lapply(seq_along(q_probs), function(i) {
    mat <- sample_cube[i, , , drop = TRUE]
    if (!is.matrix(mat)) {
      mat <- matrix(mat, nrow = dim(sample_cube)[2], ncol = dim(sample_cube)[3])
    }
    t(mat)
  })

  synth_fun <- NULL
  exdqlm_exports <- getNamespaceExports("exdqlm")
  if ("exdqlm_synthesize_from_draws" %in% exdqlm_exports) {
    synth_fun <- getExportedValue("exdqlm", "exdqlm_synthesize_from_draws")
  } else if ("quantileSynthesis" %in% exdqlm_exports) {
    synth_fun <- getExportedValue("exdqlm", "quantileSynthesis")
  } else {
    stop(
      sprintf("[%s_PACKAGE_API] package 'exdqlm' does not export a quantile synthesis entrypoint.", context),
      call. = FALSE
    )
  }

  out <- synth_fun(
    draws_list = draws_list,
    p = q_probs,
    enforce_isotonic = isTRUE(enforce_isotonic),
    rearrange = isTRUE(rearrange),
    grid_M = as.integer(grid_M),
    n_samp = as.integer(n_samp),
    seed = seed,
    T_expected = horizon
  )

  synth_draws <- t(as.matrix(out$draws))
  anchor_q <- t(as.matrix(out$quantiles))
  empirical_q <- fast_col_quantiles_t(synth_draws, probs = out$levels, na.rm = TRUE)

  list(
    draws = synth_draws,
    levels = as.numeric(out$levels),
    anchor_quantiles = anchor_q,
    empirical_quantiles = empirical_q,
    summary = out$summary,
    method = out$method
  )
}

post_quantile_synthesis_method_tag <- function(
  enforce_isotonic = TRUE,
  rearrange = TRUE,
  grid_M = 1001L,
  method = "exdqlm"
) {
  method <- gsub("[^A-Za-z0-9._-]+", "_", as.character(method %||% "exdqlm"))
  method <- gsub("^_+|_+$", "", method)
  if (!nzchar(method)) method <- "exdqlm"
  sprintf(
    "%s_iso%s_rearr%s_grid%d_v1",
    method,
    if (isTRUE(enforce_isotonic)) "1" else "0",
    if (isTRUE(rearrange)) "1" else "0",
    as.integer(grid_M[[1L]])
  )
}

post_quantile_synthesis_cache_file_name <- function(
  base_name,
  method_tag,
  model_id = "",
  transfer_mode = NA_character_
) {
  base_name <- as.character(base_name %||% "")
  method_tag <- gsub("[^A-Za-z0-9._-]+", "_", as.character(method_tag %||% ""))
  method_tag <- gsub("^_+|_+$", "", method_tag)
  if (!nzchar(base_name)) {
    stop("post_quantile_synthesis_cache_file_name requires a non-empty base_name.", call. = FALSE)
  }
  if (!nzchar(method_tag)) {
    stop("post_quantile_synthesis_cache_file_name requires a non-empty method_tag.", call. = FALSE)
  }

  ext <- if (grepl("\\.[^.]+$", base_name)) sub("^.*(\\.[^.]+)$", "\\1", base_name) else ""
  stem <- if (nzchar(ext)) substr(base_name, 1L, nchar(base_name) - nchar(ext)) else base_name
  post_cache_file_name(
    paste0(stem, "__", method_tag, ext),
    model_id = model_id,
    transfer_mode = transfer_mode
  )
}

post_synthesize_rearranged_sample_cube <- function(
  sample_cube,
  q_probs,
  n_samp = dim(sample_cube)[2],
  seed = NULL,
  enforce_isotonic = TRUE,
  rearrange = TRUE,
  grid_M = 1001L,
  sort_draws_by_time = TRUE,
  context = "quantile.synthesis"
) {
  if (!is.numeric(sample_cube) || is.null(dim(sample_cube)) || length(dim(sample_cube)) != 3L) {
    stop(sprintf("[%s_SHAPE] sample_cube must be numeric 3D [quantile x sample x horizon].", context), call. = FALSE)
  }
  q_probs <- as.numeric(q_probs)
  if (length(q_probs) != dim(sample_cube)[1]) {
    stop(sprintf("[%s_Q_LEN] q_probs length must match sample_cube quantile dimension.", context), call. = FALSE)
  }
  if (length(q_probs) < 2L || is.unsorted(q_probs) || any(!is.finite(q_probs)) ||
      any(q_probs <= 0 | q_probs >= 1)) {
    stop(sprintf("[%s_Q_PROBS] q_probs must be sorted finite probabilities in (0, 1).", context), call. = FALSE)
  }
  n_samp <- suppressWarnings(as.integer(n_samp[[1L]]))
  if (!is.finite(n_samp) || n_samp <= 1L) {
    stop(sprintf("[%s_N_SAMP] n_samp must exceed 1.", context), call. = FALSE)
  }
  grid_M <- suppressWarnings(as.integer(grid_M[[1L]]))
  if (!is.finite(grid_M) || grid_M < 11L) {
    stop(sprintf("[%s_GRID_M] grid_M must be an integer >= 11.", context), call. = FALSE)
  }

  finite_slices <- vapply(
    seq_len(dim(sample_cube)[3]),
    function(t_idx) all(is.finite(sample_cube[, , t_idx])),
    logical(1)
  )
  if (!all(finite_slices)) {
    bad_t <- which(!finite_slices)
    stop(
      sprintf(
        "[%s_NONFINITE] sample_cube contains non-finite values at t=%s.",
        context,
        paste(utils::head(bad_t, 10L), collapse = ",")
      ),
      call. = FALSE
    )
  }

  raw_sample_crossing <- post_quantile_crossing_summary(
    sample_cube = sample_cube,
    q_probs = q_probs,
    context = paste0(context, ".raw_sample")
  )
  raw_quantile_curve <- post_quantile_curve_from_sample_cube(
    sample_cube = sample_cube,
    q_probs = q_probs,
    context = paste0(context, ".raw_curve")
  )
  raw_curve_crossing <- post_quantile_curve_crossing_summary(
    q_curve = raw_quantile_curve,
    q_probs = q_probs,
    context = paste0(context, ".raw_curve")
  )

  synth <- post_exdqlm_synthesize_from_sample_cube(
    sample_cube = sample_cube,
    q_probs = q_probs,
    n_samp = n_samp,
    seed = seed,
    enforce_isotonic = enforce_isotonic,
    rearrange = rearrange,
    grid_M = grid_M,
    context = context
  )

  sample_mat <- as.matrix(synth$draws)
  if (!is.numeric(sample_mat) || nrow(sample_mat) != n_samp || ncol(sample_mat) != dim(sample_cube)[3]) {
    stop(
      sprintf(
        "[%s_OUTPUT_SHAPE] synthesized draws must have shape [n_samp x horizon]=[%d x %d].",
        context,
        as.integer(n_samp),
        as.integer(dim(sample_cube)[3])
      ),
      call. = FALSE
    )
  }

  if (isTRUE(sort_draws_by_time)) {
    for (t_idx in seq_len(ncol(sample_mat))) {
      sample_mat[, t_idx] <- sort_keep_na(sample_mat[, t_idx])
    }
  }

  levels <- as.numeric(synth$levels %||% q_probs)
  empirical_quantiles <- fast_col_quantiles_t(sample_mat, probs = levels, na.rm = TRUE)
  anchor_quantiles <- as.matrix(synth$anchor_quantiles)
  if (!is.numeric(anchor_quantiles) || nrow(anchor_quantiles) != length(levels) ||
      ncol(anchor_quantiles) != ncol(sample_mat)) {
    anchor_quantiles <- empirical_quantiles
  }

  anchor_curve_crossing <- post_quantile_curve_crossing_summary(
    q_curve = anchor_quantiles,
    q_probs = levels,
    context = paste0(context, ".anchor_curve")
  )
  empirical_curve_crossing <- post_quantile_curve_crossing_summary(
    q_curve = empirical_quantiles,
    q_probs = levels,
    context = paste0(context, ".empirical_curve")
  )

  scalar <- function(df, name, default = NA_real_) {
    if (!is.data.frame(df) || !(name %in% names(df)) || nrow(df) < 1L) return(default)
    val <- suppressWarnings(as.numeric(df[[name]][[1L]]))
    if (is.finite(val)) val else default
  }

  method_tag <- post_quantile_synthesis_method_tag(
    enforce_isotonic = enforce_isotonic,
    rearrange = rearrange,
    grid_M = grid_M,
    method = "exdqlm"
  )
  method_name <- as.character((synth$method %||% list())$name %||% "exdqlm_quantile_synthesis")

  summary <- data.frame(
    context = as.character(context),
    method_tag = method_tag,
    method_name = method_name,
    n_quantiles = as.integer(dim(sample_cube)[1]),
    n_samples_input = as.integer(dim(sample_cube)[2]),
    n_samples_output = as.integer(nrow(sample_mat)),
    horizon = as.integer(ncol(sample_mat)),
    enforce_isotonic = isTRUE(enforce_isotonic),
    rearrange = isTRUE(rearrange),
    grid_M = as.integer(grid_M),
    sort_draws_by_time = isTRUE(sort_draws_by_time),
    raw_sample_mean_crossing_rate = scalar(raw_sample_crossing$summary, "mean_crossing_rate"),
    raw_sample_max_crossing_rate = scalar(raw_sample_crossing$summary, "max_crossing_rate"),
    raw_curve_crossing_share = scalar(raw_curve_crossing$summary, "crossing_share"),
    raw_curve_max_negative_gap = scalar(raw_curve_crossing$summary, "max_negative_gap"),
    anchor_curve_crossing_share = scalar(anchor_curve_crossing$summary, "crossing_share"),
    anchor_curve_max_negative_gap = scalar(anchor_curve_crossing$summary, "max_negative_gap"),
    empirical_curve_crossing_share = scalar(empirical_curve_crossing$summary, "crossing_share"),
    empirical_curve_max_negative_gap = scalar(empirical_curve_crossing$summary, "max_negative_gap"),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      sample_mat = sample_mat,
      quantiles = empirical_quantiles,
      anchor_quantiles = anchor_quantiles,
      raw_quantile_curve = raw_quantile_curve,
      levels = levels,
      method_tag = method_tag,
      diagnostics = list(
        summary = summary,
        raw_sample_crossing = raw_sample_crossing,
        raw_curve_crossing = raw_curve_crossing,
        anchor_curve_crossing = anchor_curve_crossing,
        empirical_curve_crossing = empirical_curve_crossing,
        exdqlm_summary = synth$summary,
        method = synth$method
      )
    ),
    class = "post_quantile_synthesis"
  )
}

build_agg_discrep_quantile_df <- function(
  q_array,
  idx,
  dates,
  quantile_rows = c(1L, 4L, 7L),
  quantile_labels = c("5th", "50th", "95th"),
  context = "agg_discrep"
) {
  if (!is.numeric(q_array) || is.null(dim(q_array)) || length(dim(q_array)) != 3L) {
    stop(sprintf("[%s_SHAPE] q_array must be numeric 3D [quantile_row x time x summary].", context))
  }
  if (dim(q_array)[3] < 3L) {
    stop(sprintf("[%s_SUMMARY_DIM] q_array third dimension must contain at least 3 summary slots.", context))
  }

  idx <- as.integer(idx)
  if (length(idx) == 0L || any(!is.finite(idx)) || any(idx < 1L)) {
    stop(sprintf("[%s_INDEX] idx must contain positive finite indices.", context))
  }
  if (max(idx) > dim(q_array)[2]) {
    stop(
      sprintf(
        "[%s_INDEX_OOB] idx max=%d exceeds q_array time dimension=%d.",
        context,
        as.integer(max(idx)),
        as.integer(dim(q_array)[2])
      )
    )
  }

  quantile_rows <- as.integer(quantile_rows)
  if (length(quantile_rows) != length(quantile_labels)) {
    stop(sprintf("[%s_LABEL_MAP] quantile_rows and quantile_labels must have the same length.", context))
  }
  if (any(!is.finite(quantile_rows)) || any(quantile_rows < 1L) || any(quantile_rows > dim(q_array)[1])) {
    stop(
      sprintf(
        "[%s_ROW_OOB] quantile_rows must be within [1, %d].",
        context,
        as.integer(dim(q_array)[1])
      )
    )
  }

  dates <- as.Date(dates)
  if (length(dates) != length(idx)) {
    stop(
      sprintf(
        "[%s_DATE_LEN] dates length=%d must equal idx length=%d.",
        context,
        as.integer(length(dates)),
        as.integer(length(idx))
      )
    )
  }

  rows <- lapply(seq_along(quantile_rows), function(i) {
    row_id <- quantile_rows[[i]]
    lower_raw <- q_array[row_id, idx, 1]
    upper_raw <- q_array[row_id, idx, 3]
    data.frame(
      Date = dates,
      Quantile = as.character(quantile_labels[[i]]),
      Lower = pmin(lower_raw, upper_raw),
      Median = q_array[row_id, idx, 2],
      Upper = pmax(lower_raw, upper_raw),
      stringsAsFactors = FALSE
    )
  })
  dplyr::bind_rows(rows)
}

resolve_agg_discrep_ylim <- function(
  obs,
  fitted_df,
  preferred_ylim = NULL,
  min_inrange_share = 0.15,
  pad_frac = 0.05,
  min_span = 0.1,
  context = "agg_discrep"
) {
  obs <- as.numeric(obs)
  if (!is.data.frame(fitted_df) ||
      !all(c("Lower", "Median", "Upper") %in% names(fitted_df))) {
    stop(sprintf("[%s_FITTED_SCHEMA] fitted_df must contain Lower/Median/Upper columns.", context))
  }

  fitted_vals <- c(
    as.numeric(fitted_df$Lower),
    as.numeric(fitted_df$Median),
    as.numeric(fitted_df$Upper)
  )
  obs_finite <- obs[is.finite(obs)]
  fitted_finite <- fitted_vals[is.finite(fitted_vals)]
  combined <- c(obs_finite, fitted_finite)
  if (length(combined) == 0L) {
    stop(sprintf("[%s_EMPTY_SERIES] no finite observed/fitted values available to resolve ylim.", context))
  }

  pref_valid <- FALSE
  pref <- c(NA_real_, NA_real_)
  if (!is.null(preferred_ylim)) {
    pref <- as.numeric(preferred_ylim)
    pref_valid <- length(pref) == 2L && all(is.finite(pref)) && pref[1] < pref[2]
  }

  inrange_share <- NA_real_
  use_preferred <- FALSE
  if (pref_valid && length(fitted_finite) > 0L) {
    inrange_share <- mean(fitted_finite >= pref[1] & fitted_finite <= pref[2])
    use_preferred <- is.finite(inrange_share) && inrange_share >= as.numeric(min_inrange_share)
  } else if (pref_valid && length(fitted_finite) == 0L) {
    use_preferred <- TRUE
  }

  if (use_preferred) {
    return(list(
      ylim = pref,
      mode = "preferred",
      preferred_inrange_share = inrange_share,
      fitted_finite_n = as.integer(length(fitted_finite)),
      obs_finite_n = as.integer(length(obs_finite)),
      combined_min = min(combined),
      combined_max = max(combined),
      preferred_min = pref[1],
      preferred_max = pref[2]
    ))
  }

  y_min <- min(combined)
  y_max <- max(combined)
  span <- y_max - y_min
  if (!is.finite(span) || span < as.numeric(min_span)) {
    mid <- mean(c(y_min, y_max))
    span <- as.numeric(min_span)
    y_min <- mid - 0.5 * span
    y_max <- mid + 0.5 * span
  }
  pad <- max(as.numeric(pad_frac) * span, 1e-6)
  dyn <- c(y_min - pad, y_max + pad)

  list(
    ylim = dyn,
    mode = if (pref_valid) "expanded" else "expanded_no_preferred",
    preferred_inrange_share = inrange_share,
    fitted_finite_n = as.integer(length(fitted_finite)),
    obs_finite_n = as.integer(length(obs_finite)),
    combined_min = min(combined),
    combined_max = max(combined),
    preferred_min = if (pref_valid) pref[1] else NA_real_,
    preferred_max = if (pref_valid) pref[2] else NA_real_
  )
}

forecast_cube_effective_horizon <- function(cube, context = "forecast_cube") {
  if (!is.numeric(cube)) {
    stop(sprintf("[FORECAST_CUBE_TYPE] %s must be a numeric 3D array.", context))
  }
  d <- dim(cube)
  if (is.null(d) || length(d) != 3L) {
    stop(sprintf("[FORECAST_CUBE_DIM] %s must be a 3D array [quantile x sample x time].", context))
  }
  n_t <- as.integer(d[[3L]])
  if (!is.finite(n_t) || n_t <= 0L) {
    stop(sprintf("[FORECAST_CUBE_EMPTY] %s has no forecast time dimension.", context))
  }

  finite_by_t <- vapply(
    seq_len(n_t),
    function(t) all(is.finite(cube[, , t])),
    logical(1)
  )

  if (!any(finite_by_t)) {
    stop(sprintf("[FORECAST_CUBE_EMPTY] %s has no fully finite forecast slices.", context))
  }

  last_finite <- max(which(finite_by_t))
  interior_missing <- which(!finite_by_t[seq_len(last_finite)])
  if (length(interior_missing) > 0L) {
    stop(
      sprintf(
        "[FORECAST_CUBE_GAP] %s has non-finite interior forecast slices before horizon end at t=%d (first bad t=%d).",
        context,
        as.integer(last_finite),
        as.integer(interior_missing[[1L]])
      )
    )
  }

  trailing_missing <- which(!finite_by_t & seq_len(n_t) > last_finite)
  if (length(trailing_missing) > 0L) {
    warning(
      sprintf(
        "[FORECAST_CUBE_TRUNCATE] %s contains trailing non-finite slices; effective horizon reduced from %d to %d.",
        context,
        as.integer(n_t),
        as.integer(last_finite)
      ),
      call. = FALSE
    )
  }

  list(
    horizon = as.integer(last_finite),
    finite_mask = finite_by_t,
    trailing_missing = as.integer(length(trailing_missing))
  )
}

trim_forecast_cube_to_effective_horizon <- function(cube, context = "forecast_cube") {
  info <- forecast_cube_effective_horizon(cube, context = context)
  n_t <- dim(cube)[3]
  if (info$horizon >= n_t) {
    return(list(cube = cube, info = info))
  }
  list(
    cube = cube[, , seq_len(info$horizon), drop = FALSE],
    info = info
  )
}

post_export_tables_enabled <- function(default = TRUE) {
  if (exists("EXPORT_TABLES", inherits = TRUE)) {
    return(isTRUE(get("EXPORT_TABLES", inherits = TRUE)))
  }
  isTRUE(as.logical(Sys.getenv("EXPORT_TABLES", if (isTRUE(default)) "TRUE" else "FALSE")))
}

post_quantile_label_to_int <- function(x) {
  x <- as.character(x)
  x <- gsub("[^0-9]", "", x)
  out <- suppressWarnings(as.integer(x))
  out
}

post_ci_string <- function(lower, upper, digits = 5L) {
  lower <- as.numeric(lower)
  upper <- as.numeric(upper)
  fmt <- paste0("%.", as.integer(digits), "f")
  out <- rep(NA_character_, length(lower))
  ok <- is.finite(lower) & is.finite(upper)
  out[ok] <- sprintf(paste0(fmt, ", ", fmt), lower[ok], upper[ok])
  out
}

post_write_csv <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write.csv(df, file = path, row.names = FALSE)
  invisible(path)
}

post_table_formats <- function(default = c("csv")) {
  raw <- Sys.getenv("EXPORT_TABLE_FORMATS", "")
  if (!nzchar(raw)) {
    return(unique(tolower(as.character(default))))
  }
  vals <- trimws(unlist(strsplit(raw, ",", fixed = TRUE), use.names = FALSE))
  vals <- vals[nzchar(vals)]
  if (length(vals) == 0L) {
    return(unique(tolower(as.character(default))))
  }
  unique(tolower(vals))
}

post_table_row_order <- function(df, sort_keys = NULL) {
  n <- nrow(df)
  if (n <= 1L) return(seq_len(n))

  if (!is.null(sort_keys) && length(sort_keys) > 0L) {
    keys <- intersect(as.character(sort_keys), names(df))
  } else {
    keys <- character(0)
  }
  # Preserve caller-provided row order unless explicit valid sort keys are provided.
  if (length(keys) == 0L) {
    return(seq_len(n))
  }

  key_cols <- lapply(keys, function(k) {
    v <- df[[k]]
    if (inherits(v, "factor")) {
      as.character(v)
    } else {
      v
    }
  })
  do.call(order, c(key_cols, list(na.last = TRUE, method = "radix")))
}

post_drop_na_rows <- function(df, keep_na = TRUE) {
  if (isTRUE(keep_na) || nrow(df) == 0L) return(df)
  df[stats::complete.cases(df), , drop = FALSE]
}

post_format_numeric_columns <- function(df, digits = 10L) {
  out <- df
  for (nm in names(out)) {
    col <- out[[nm]]
    if (is.numeric(col) && !is.integer(col)) {
      vals <- as.numeric(col)
      out[[nm]] <- ifelse(
        is.na(vals),
        NA_character_,
        formatC(vals, digits = as.integer(digits), format = "fg", flag = "#")
      )
    } else if (inherits(col, "factor")) {
      out[[nm]] <- as.character(col)
    }
  }
  out
}

post_write_csv_deterministic <- function(df, path, numeric_digits = 10L) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  out <- post_format_numeric_columns(df, digits = numeric_digits)
  utils::write.table(
    out,
    file = path,
    sep = ",",
    row.names = FALSE,
    col.names = TRUE,
    quote = TRUE,
    na = "NA",
    qmethod = "double",
    eol = "\n"
  )
  invisible(path)
}

post_path_relative_to_dir <- function(path, output_dir) {
  dir_abs <- normalizePath(output_dir, mustWork = TRUE)
  path_abs <- normalizePath(path, mustWork = FALSE)
  prefix <- paste0(dir_abs, .Platform$file.sep)
  if (startsWith(path_abs, prefix)) {
    return(substr(path_abs, nchar(prefix) + 1L, nchar(path_abs)))
  }
  basename(path_abs)
}

post_sha256_file <- function(path) {
  stopifnot(file.exists(path))

  if (requireNamespace("digest", quietly = TRUE)) {
    return(digest::digest(file = path, algo = "sha256"))
  }

  cmd <- Sys.which("sha256sum")
  if (nzchar(cmd)) {
    out <- tryCatch(system2(cmd, shQuote(path), stdout = TRUE, stderr = FALSE), error = function(e) character(0))
    if (length(out) >= 1L) {
      token <- strsplit(out[[1L]], "[[:space:]]+")[[1L]][1L]
      if (nzchar(token)) return(token)
    }
  }

  stop("Unable to compute sha256 (digest package or sha256sum command required).", call. = FALSE)
}

post_export_tables <- function(
  tables,
  output_dir,
  file_stems = NULL,
  formats = c("csv"),
  keep_na = TRUE,
  sort_keys = NULL,
  numeric_digits = 10L
) {
  if (is.null(tables) || length(tables) == 0L) {
    return(data.frame(
      table_name = character(0),
      file_path = character(0),
      nrow = integer(0),
      ncol = integer(0),
      sha256 = character(0),
      stringsAsFactors = FALSE
    ))
  }
  if (is.null(names(tables)) || any(!nzchar(names(tables)))) {
    stop("post_export_tables requires a named list of tables.", call. = FALSE)
  }

  formats <- unique(tolower(as.character(formats)))
  formats <- formats[formats %in% c("csv", "rds")]
  if (length(formats) == 0L) formats <- "csv"

  manifest_rows <- list()

  for (nm in names(tables)) {
    df <- as.data.frame(tables[[nm]], stringsAsFactors = FALSE)
    df <- post_drop_na_rows(df, keep_na = keep_na)

    keys <- NULL
    if (!is.null(sort_keys) && !is.null(sort_keys[[nm]])) {
      keys <- sort_keys[[nm]]
    }
    ord <- post_table_row_order(df, sort_keys = keys)
    if (length(ord) > 0L) {
      df <- df[ord, , drop = FALSE]
    }
    rownames(df) <- NULL

    stem <- nm
    if (!is.null(file_stems) && !is.null(file_stems[[nm]]) && nzchar(file_stems[[nm]])) {
      stem <- as.character(file_stems[[nm]])
    }

    for (fmt in formats) {
      path <- file.path(output_dir, sprintf("%s.%s", stem, fmt))
      if (identical(fmt, "csv")) {
        post_write_csv_deterministic(df, path, numeric_digits = numeric_digits)
      } else if (identical(fmt, "rds")) {
        dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
        saveRDS(df, path)
      }

      manifest_rows[[length(manifest_rows) + 1L]] <- data.frame(
        table_name = nm,
        file_path = post_path_relative_to_dir(path, output_dir),
        nrow = nrow(df),
        ncol = ncol(df),
        sha256 = post_sha256_file(path),
        stringsAsFactors = FALSE
      )
    }
  }

  do.call(rbind, manifest_rows)
}

post_write_lines <- function(lines, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(lines, con = path, useBytes = TRUE)
  invisible(path)
}

post_source_levels <- c("USGS", "GLOFAS", "NWS")
post_quantile_levels <- c(5L, 20L, 35L, 50L, 65L, 80L, 95L)
post_covariate_levels <- c("Precipitation", "Soil Moisture", "PC1", "Intercept", "Lag1", "Lag2", "Lag3", "Lag4", "Lag5")

post_component_to_covariate <- function(component) {
  component <- as.integer(component)
  mapping <- c(
    "23" = "Precipitation",
    "24" = "Soil Moisture",
    "25" = "PC1",
    "26" = "Intercept",
    "27" = "Lag1",
    "28" = "Lag2",
    "29" = "Lag3",
    "30" = "Lag4",
    "31" = "Lag5"
  )
  out <- unname(mapping[as.character(component)])
  fallback <- paste0("Component_", component)
  out[is.na(out)] <- fallback[is.na(out)]
  out
}

post_export_gamma_sigma_tables <- function(
  all_quantiles,
  output_dir,
  ci_digits = 5L,
  write_tex = TRUE,
  table_formats = c("csv"),
  keep_na = TRUE,
  numeric_digits = 10L
) {
  req_cols <- c("variable", "source", "quantile", "quantile_025", "median", "quantile_975")
  missing_cols <- setdiff(req_cols, names(all_quantiles))
  if (length(missing_cols) > 0L) {
    stop(sprintf("post_export_gamma_sigma_tables missing columns: %s", paste(missing_cols, collapse = ", ")))
  }

  vars <- tolower(as.character(all_quantiles$variable))
  keep <- vars %in% c("gamma", "sigma")
  work <- all_quantiles[keep, req_cols, drop = FALSE]
  if (nrow(work) == 0L) {
    empty <- data.frame(
      quantile = integer(0),
      source = character(0),
      stat = character(0),
      center = numeric(0),
      q2_5 = numeric(0),
      q97_5 = numeric(0),
      ci_str = character(0),
      stringsAsFactors = FALSE
    )
    manifest <- post_export_tables(
      tables = list(gamma = empty, sigma = empty),
      output_dir = output_dir,
      file_stems = list(gamma = "gamma_summary", sigma = "sigma_summary"),
      formats = table_formats,
      keep_na = keep_na,
      sort_keys = list(gamma = c("quantile", "source", "stat"), sigma = c("quantile", "source", "stat")),
      numeric_digits = numeric_digits
    )
    return(list(gamma = empty, sigma = empty, manifest = manifest))
  }

  out <- data.frame(
    quantile = post_quantile_label_to_int(work$quantile),
    source = toupper(as.character(work$source)),
    stat = tolower(as.character(work$variable)),
    center = as.numeric(work$median),
    q2_5 = as.numeric(work$quantile_025),
    q97_5 = as.numeric(work$quantile_975),
    stringsAsFactors = FALSE
  )
  out$ci_str <- post_ci_string(out$q2_5, out$q97_5, digits = ci_digits)

  out$source <- factor(out$source, levels = post_source_levels, ordered = TRUE)
  out$quantile <- as.integer(out$quantile)
  out <- out[order(out$quantile, out$source, out$stat), c("quantile", "source", "stat", "center", "q2_5", "q97_5", "ci_str")]
  rownames(out) <- NULL
  out$source <- as.character(out$source)

  gamma_df <- out[out$stat == "gamma", , drop = FALSE]
  sigma_df <- out[out$stat == "sigma", , drop = FALSE]
  manifest <- post_export_tables(
    tables = list(gamma = gamma_df, sigma = sigma_df),
    output_dir = output_dir,
    file_stems = list(gamma = "gamma_summary", sigma = "sigma_summary"),
    formats = table_formats,
    keep_na = keep_na,
    sort_keys = list(gamma = c("quantile", "source", "stat"), sigma = c("quantile", "source", "stat")),
    numeric_digits = numeric_digits
  )

  if (isTRUE(write_tex)) {
    gamma_lines <- c(
      "% quantile & source & center & [q2.5, q97.5] \\\\",
      if (nrow(gamma_df) == 0L) "% <empty>" else sprintf(
        "%d & %s & %.5f & [%.5f, %.5f] \\\\",
        gamma_df$quantile, gamma_df$source, gamma_df$center, gamma_df$q2_5, gamma_df$q97_5
      )
    )
    sigma_lines <- c(
      "% quantile & source & center & [q2.5, q97.5] \\\\",
      if (nrow(sigma_df) == 0L) "% <empty>" else sprintf(
        "%d & %s & %.5f & [%.5f, %.5f] \\\\",
        sigma_df$quantile, sigma_df$source, sigma_df$center, sigma_df$q2_5, sigma_df$q97_5
      )
    )
    post_write_lines(gamma_lines, file.path(output_dir, "gamma_summary.tex"))
    post_write_lines(sigma_lines, file.path(output_dir, "sigma_summary.tex"))
  }

  list(gamma = gamma_df, sigma = sigma_df, manifest = manifest)
}

post_export_covariate_effects_table <- function(
  summary_df,
  output_dir,
  time_index = NA_integer_,
  ci_digits = 5L,
  write_tex = TRUE,
  table_formats = c("csv"),
  keep_na = TRUE,
  numeric_digits = 10L
) {
  req_cols <- c("Component", "Quantile", "Lower", "Mean", "Upper")
  missing_cols <- setdiff(req_cols, names(summary_df))
  if (length(missing_cols) > 0L) {
    stop(sprintf("post_export_covariate_effects_table missing columns: %s", paste(missing_cols, collapse = ", ")))
  }

  out <- data.frame(
    covariate = post_component_to_covariate(summary_df$Component),
    quantile = post_quantile_label_to_int(summary_df$Quantile),
    center = as.numeric(summary_df$Mean),
    q2_5 = as.numeric(summary_df$Lower),
    q97_5 = as.numeric(summary_df$Upper),
    ci_str = NA_character_,
    time_index = as.integer(time_index),
    notes = "",
    stringsAsFactors = FALSE
  )
  out$ci_str <- post_ci_string(out$q2_5, out$q97_5, digits = ci_digits)

  out$covariate <- factor(out$covariate, levels = post_covariate_levels, ordered = TRUE)
  out$quantile <- as.integer(out$quantile)
  out <- out[order(out$covariate, out$quantile), c("covariate", "quantile", "center", "q2_5", "q97_5", "ci_str", "time_index", "notes")]
  rownames(out) <- NULL
  out$covariate <- as.character(out$covariate)

  manifest <- post_export_tables(
    tables = list(covariate_effects = out),
    output_dir = output_dir,
    file_stems = list(covariate_effects = "covariate_effects_summary"),
    formats = table_formats,
    keep_na = keep_na,
    sort_keys = list(covariate_effects = c("covariate", "quantile")),
    numeric_digits = numeric_digits
  )

  if (isTRUE(write_tex)) {
    lines <- c(
      "% covariate & quantile & center & [q2.5, q97.5] \\\\",
      if (nrow(out) == 0L) "% <empty>" else sprintf(
        "%s & %d & %.5f & [%.5f, %.5f] \\\\",
        out$covariate, out$quantile, out$center, out$q2_5, out$q97_5
      )
    )
    post_write_lines(lines, file.path(output_dir, "covariate_effects_summary.tex"))
  }

  list(table = out, manifest = manifest)
}

post_write_table_exports_manifest <- function(manifest_df, output_dir) {
  if (is.null(manifest_df) || nrow(manifest_df) == 0L) return(invisible(NULL))
  out_path <- file.path(output_dir, "posterior_table_exports_manifest.csv")
  post_write_csv_deterministic(manifest_df, out_path, numeric_digits = 15L)
  invisible(out_path)
}

post_write_table_exports_readme <- function(output_dir, ci_digits = 5L, table_formats = c("csv")) {
  lines <- c(
    "# Posterior Table Exports",
    "",
    "This folder contains machine-readable posterior summary tables generated during post-processing.",
    "",
    "Files:",
    "- gamma_summary.csv: gamma by source x quantile with center=posterior median and 95% CI",
    "- sigma_summary.csv: sigma by source x quantile with center=posterior median and 95% CI",
    "- covariate_effects_summary.csv: transfer-function covariate effects with center=posterior mean and 95% CI at final time index",
    "- crps_forecast_per_time*.csv: lead-wise forecast CRPS using quantile/check-loss approximation",
    "- crps_forecast_summary*.csv: mean and dispersion CRPS summaries by forecast model",
    "",
    "Optional LaTeX snippets:",
    "- gamma_summary.tex",
    "- sigma_summary.tex",
    "- covariate_effects_summary.tex",
    "",
    sprintf("CI string precision: %d decimal places.", as.integer(ci_digits)),
    sprintf("Table formats: %s", paste(unique(table_formats), collapse = ", ")),
    "The numeric columns are the source of truth for downstream table generation."
  )
  post_write_lines(lines, file.path(output_dir, "posterior_table_exports_README.md"))
}

log_g <- function(gam) {
  log(2) + stats::pnorm(-abs(gam), log = TRUE) + 0.5 * gam^2
}

L_fn <- function(p0) {
  stats::uniroot(function(gam) exp(log_g(gam)) - (1 - p0), c(-1000, 0))$root
}

U_fn <- function(p0) {
  stats::uniroot(function(gam) exp(log_g(gam)) - p0, c(0, 1000))$root
}

p_fn <- function(p0, gam) {
  (p0 - as.numeric(gam < 0)) / exp(log_g(gam)) + as.numeric(gam < 0)
}

A_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (1 - 2 * temp_p) / (temp_p * (1 - temp_p))
}

B_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  2 / (temp_p * (1 - temp_p))
}

C_fn <- function(p0, gam) {
  temp_p <- p_fn(p0, gam)
  (as.numeric(gam > 0) - temp_p)^(-1)
}

check_loss_fn <- function(p0, diff) {
  diff * p0 - diff * as.numeric(diff < 0)
}

post_sanitize_file_suffix <- function(file_suffix = "") {
  suffix_raw <- if (is.null(file_suffix)) "" else file_suffix
  suffix <- as.character(suffix_raw)
  if (!nzchar(suffix)) return("")
  suffix <- gsub("[^A-Za-z0-9._-]+", "_", suffix)
  suffix <- gsub("^_+|_+$", "", suffix)
  if (!nzchar(suffix)) return("")
  if (!startsWith(suffix, "_")) suffix <- paste0("_", suffix)
  suffix
}

post_cache_file_name <- function(base_name, model_id = "", transfer_mode = NA_character_) {
  base_name <- as.character(base_name %||% "")
  if (!nzchar(base_name)) {
    stop("post_cache_file_name requires a non-empty base_name.", call. = FALSE)
  }

  model_tag <- gsub("[^A-Za-z0-9._-]+", "_", as.character(model_id %||% ""))
  model_tag <- gsub("^_+|_+$", "", model_tag)

  mode_tag <- tolower(trimws(as.character(transfer_mode %||% "")))
  if (!nzchar(mode_tag) || is.na(mode_tag) || !(mode_tag %in% c("drop", "keep"))) {
    mode_tag <- ""
  }

  ext <- if (grepl("\\.[^.]+$", base_name)) sub("^.*(\\.[^.]+)$", "\\1", base_name) else ""
  stem <- if (nzchar(ext)) substr(base_name, 1L, nchar(base_name) - nchar(ext)) else base_name

  prefix_parts <- c(model_tag, if (nzchar(mode_tag)) paste0("mode-", mode_tag) else "")
  prefix_parts <- prefix_parts[nzchar(prefix_parts)]
  if (length(prefix_parts) == 0L) {
    return(base_name)
  }
  paste0(paste(prefix_parts, collapse = "__"), "__", stem, ext)
}

post_plot_sample_indices <- function(n_available, cap = 128L) {
  n_use <- suppressWarnings(as.integer(n_available[[1L]]))
  cap_use <- suppressWarnings(as.integer(cap[[1L]]))
  if (!is.finite(n_use) || n_use <= 0L) return(integer(0))
  if (!is.finite(cap_use) || cap_use <= 0L) cap_use <- min(n_use, 128L)
  if (n_use <= cap_use) return(seq_len(n_use))
  idx <- unique(as.integer(round(seq(1, n_use, length.out = cap_use))))
  idx[idx >= 1L & idx <= n_use]
}

post_crps_quantile_approx <- function(obs, sample_mat, context = "crps.quantile") {
  if (!is.matrix(sample_mat)) {
    sample_mat <- as.matrix(sample_mat)
  }
  if (!is.numeric(sample_mat) || length(dim(sample_mat)) != 2L) {
    stop(sprintf("[%s_SHAPE] sample_mat must be a numeric 2D matrix [sample x horizon].", context), call. = FALSE)
  }
  n_samp <- as.integer(nrow(sample_mat))
  horizon <- as.integer(ncol(sample_mat))
  if (!is.finite(n_samp) || !is.finite(horizon) || n_samp < 2L || horizon < 1L) {
    stop(
      sprintf("[%s_DIM] sample_mat must have at least 2 samples and 1 horizon point.", context),
      call. = FALSE
    )
  }

  obs_num <- as.numeric(obs)
  if (length(obs_num) < horizon) {
    warning(
      sprintf("[%s_OBS_SHORT] obs length (%d) is shorter than horizon (%d); padding with NA.", context, length(obs_num), horizon),
      call. = FALSE
    )
    obs_num <- c(obs_num, rep(NA_real_, horizon - length(obs_num)))
  }
  if (length(obs_num) > horizon) {
    obs_num <- obs_num[seq_len(horizon)]
  }

  out <- rep(NA_real_, horizon)
  n_eff <- integer(horizon)

  for (t_idx in seq_len(horizon)) {
    yy <- obs_num[[t_idx]]
    sample_vec <- sample_mat[, t_idx]
    sample_vec <- sample_vec[is.finite(sample_vec)]
    n_eff[[t_idx]] <- length(sample_vec)
    if (!is.finite(yy) || length(sample_vec) < 2L) {
      next
    }
    sample_vec <- sort(sample_vec)
    mm <- length(sample_vec)
    tau <- seq_len(mm) / (mm + 1)
    out[[t_idx]] <- 2 * mean(check_loss_fn(tau, yy - sample_vec))
  }

  list(
    crps = out,
    n_samples_eff = as.integer(n_eff),
    n_samples_nominal = n_samp,
    tau_rule = "k_over_m_plus_1",
    method = "quantile_check_loss_sum"
  )
}

post_truth_from_start_or_na <- function(
  usgs_dates,
  usgs_truth,
  forecast_start_date,
  horizon,
  context = "truth"
) {
  hz <- as.integer(horizon[[1L]])
  if (!is.finite(hz) || hz < 1L) {
    stop(sprintf("[%s_HORIZON] horizon must be a positive integer.", context), call. = FALSE)
  }

  start_date <- as.Date(forecast_start_date)
  dates <- as.Date(usgs_dates)
  truth_all <- as.numeric(usgs_truth)
  idx <- which(!is.na(dates) & dates >= start_date)

  status <- "available"
  message <- ""
  truth <- numeric(0)

  if (length(idx) == 0L) {
    status <- "missing"
    message <- sprintf("no USGS truth rows available at/after %s; CRPS obs padded with NA", as.character(start_date))
    warning(sprintf("[%s_TRUTH_MISSING] %s.", context, message), call. = FALSE)
    truth <- rep(NA_real_, hz)
  } else {
    truth <- truth_all[idx]
    if (length(truth) < hz) {
      status <- "short"
      message <- sprintf("truth length (%d) shorter than horizon (%d); padded with NA", length(truth), hz)
      warning(sprintf("[%s_TRUTH_SHORT] %s.", context, message), call. = FALSE)
      truth <- c(truth, rep(NA_real_, hz - length(truth)))
    } else {
      truth <- truth[seq_len(hz)]
    }
  }

  availability <- data.frame(
    context = as.character(context),
    forecast_start_date = as.character(start_date),
    horizon_days = as.integer(hz),
    truth_rows_available = as.integer(length(idx)),
    truth_rows_used = as.integer(sum(is.finite(as.numeric(truth)))),
    status = as.character(status),
    message = as.character(message),
    stringsAsFactors = FALSE
  )

  list(truth = as.numeric(truth), availability = availability)
}

post_crps_synth_model_meta <- function(
  family = c("univar", "multivar", "ndlm", "ndlm_main", "ndlm_univar"),
  likelihood_mode = "exal",
  transfer_mode = NA_character_
) {
  fam <- tolower(trimws(as.character(family)[[1L]]))
  if (!(fam %in% c("univar", "multivar", "ndlm", "ndlm_main", "ndlm_univar"))) {
    stop(sprintf("post_crps_synth_model_meta unsupported family: %s", fam), call. = FALSE)
  }

  lik <- tolower(trimws(as.character(likelihood_mode)[[1L]]))
  if (!(lik %in% c("exal", "al"))) {
    lik <- "exal"
  }
  mode <- as.character(transfer_mode)[[1L]]
  mode <- tolower(trimws(mode))
  if (!nzchar(mode) || is.na(mode) || !(mode %in% c("drop", "keep"))) {
    mode <- NA_character_
  }

  if (identical(fam, "univar")) {
    if (identical(lik, "al")) {
      return(list(model_id = "dqlm_univar_al_synth", model_variant = "dqlm_univar_al"))
    }
    return(list(model_id = "exdqlm_univar_synth", model_variant = "exdqlm_univar"))
  }

  if (identical(fam, "multivar")) {
    if (identical(lik, "al")) {
      prefix_id <- "dqlm_multivar_al_synth"
      prefix_variant <- "dqlm_multivar_al"
    } else {
      prefix_id <- "exdqlm_multivar_synth"
      prefix_variant <- "exdqlm_multivar"
    }
    if (is.na(mode)) {
      return(list(model_id = prefix_id, model_variant = prefix_variant))
    }
    return(list(
      model_id = paste0(prefix_id, "_", mode),
      model_variant = paste0(prefix_variant, "_", mode)
    ))
  }

  if (identical(fam, "ndlm_univar")) {
    if (is.na(mode)) {
      return(list(model_id = "ndlm_univar_synth", model_variant = "ndlm_univar"))
    }
    return(list(
      model_id = paste0("ndlm_univar_synth_", mode),
      model_variant = paste0("ndlm_univar_", mode)
    ))
  }

  if (is.na(mode)) {
    return(list(model_id = "ndlm_main_synth", model_variant = "ndlm_main"))
  }
  list(
    model_id = paste0("ndlm_main_synth_", mode),
    model_variant = paste0("ndlm_main_", mode)
  )
}

post_crps_model_tables <- function(
  model_id,
  model_family,
  model_variant,
  sample_mat,
  obs,
  forecast_dates,
  cutoff_date,
  forecast_start_date,
  transfer_mode = NA_character_,
  score_scale = "log_cms_plus1",
  context = "crps.model"
) {
  model_id <- as.character(if (is.null(model_id)) "" else model_id)
  model_family <- as.character(if (is.null(model_family)) "" else model_family)
  model_variant <- as.character(if (is.null(model_variant)) "" else model_variant)
  if (!nzchar(model_id)) stop(sprintf("[%s_MODEL_ID] model_id must be non-empty.", context), call. = FALSE)
  if (!nzchar(model_family)) stop(sprintf("[%s_MODEL_FAMILY] model_family must be non-empty.", context), call. = FALSE)
  if (!nzchar(model_variant)) stop(sprintf("[%s_MODEL_VARIANT] model_variant must be non-empty.", context), call. = FALSE)

  if (!is.matrix(sample_mat)) sample_mat <- as.matrix(sample_mat)
  horizon <- as.integer(ncol(sample_mat))

  dates <- as.Date(forecast_dates)
  if (length(dates) < horizon) {
    warning(
      sprintf("[%s_DATES_SHORT] forecast_dates length (%d) is shorter than horizon (%d); padding with NA.", context, length(dates), horizon),
      call. = FALSE
    )
    dates <- c(dates, rep(as.Date(NA), horizon - length(dates)))
  }
  if (length(dates) > horizon) {
    dates <- dates[seq_len(horizon)]
  }

  crps_out <- post_crps_quantile_approx(
    obs = obs,
    sample_mat = sample_mat,
    context = paste0(context, ".", model_id)
  )
  crps_vec <- as.numeric(crps_out$crps)
  finite <- is.finite(crps_vec)
  n_valid <- sum(finite)

  per_time <- data.frame(
    cutoff_date = as.character(as.Date(cutoff_date)),
    forecast_start_date = as.character(as.Date(forecast_start_date)),
    model_id = model_id,
    model_family = model_family,
    model_variant = model_variant,
    transfer_mode = as.character(ifelse(is.na(transfer_mode), NA_character_, transfer_mode)),
    lead_day = seq_len(horizon),
    forecast_date = as.character(dates),
    crps = crps_vec,
    n_samples_eff = as.integer(crps_out$n_samples_eff),
    n_samples_nominal = as.integer(crps_out$n_samples_nominal),
    score_method = as.character(crps_out$method),
    tau_rule = as.character(crps_out$tau_rule),
    score_scale = as.character(score_scale),
    stringsAsFactors = FALSE
  )

  summary <- data.frame(
    cutoff_date = as.character(as.Date(cutoff_date)),
    forecast_start_date = as.character(as.Date(forecast_start_date)),
    model_id = model_id,
    model_family = model_family,
    model_variant = model_variant,
    transfer_mode = as.character(ifelse(is.na(transfer_mode), NA_character_, transfer_mode)),
    horizon_days = as.integer(horizon),
    n_valid = as.integer(n_valid),
    mean_crps = if (n_valid > 0L) mean(crps_vec[finite]) else NA_real_,
    median_crps = if (n_valid > 0L) stats::median(crps_vec[finite]) else NA_real_,
    sd_crps = if (n_valid > 1L) stats::sd(crps_vec[finite]) else NA_real_,
    min_crps = if (n_valid > 0L) min(crps_vec[finite]) else NA_real_,
    max_crps = if (n_valid > 0L) max(crps_vec[finite]) else NA_real_,
    n_samples_nominal = as.integer(crps_out$n_samples_nominal),
    n_samples_eff_min = if (length(crps_out$n_samples_eff) > 0L) min(crps_out$n_samples_eff, na.rm = TRUE) else NA_integer_,
    n_samples_eff_max = if (length(crps_out$n_samples_eff) > 0L) max(crps_out$n_samples_eff, na.rm = TRUE) else NA_integer_,
    score_method = as.character(crps_out$method),
    tau_rule = as.character(crps_out$tau_rule),
    score_scale = as.character(score_scale),
    stringsAsFactors = FALSE
  )

  list(per_time = per_time, summary = summary)
}

post_safe_numeric_summary <- function(x) {
  vals <- as.numeric(x)
  finite <- vals[is.finite(vals)]
  if (length(finite) == 0L) {
    return(list(
      min = NA_real_,
      q01 = NA_real_,
      median = NA_real_,
      q99 = NA_real_,
      max = NA_real_,
      mean = NA_real_,
      sd = NA_real_,
      max_abs = NA_real_
    ))
  }
  qs <- stats::quantile(finite, probs = c(0.01, 0.5, 0.99), names = FALSE, na.rm = TRUE, type = 8)
  list(
    min = min(finite),
    q01 = as.numeric(qs[[1L]]),
    median = as.numeric(qs[[2L]]),
    q99 = as.numeric(qs[[3L]]),
    max = max(finite),
    mean = mean(finite),
    sd = if (length(finite) > 1L) stats::sd(finite) else 0,
    max_abs = max(abs(finite))
  )
}

post_crps_input_health_tables <- function(
  model_id,
  model_family,
  model_variant,
  sample_mat,
  forecast_dates,
  cutoff_date,
  forecast_start_date,
  transfer_mode = NA_character_,
  min_finite_share = 1,
  max_abs = NA_real_,
  context = "crps.input_health"
) {
  model_id <- as.character(if (is.null(model_id)) "" else model_id)
  model_family <- as.character(if (is.null(model_family)) "" else model_family)
  model_variant <- as.character(if (is.null(model_variant)) "" else model_variant)
  if (!nzchar(model_id)) stop(sprintf("[%s_MODEL_ID] model_id must be non-empty.", context), call. = FALSE)
  if (!nzchar(model_family)) stop(sprintf("[%s_MODEL_FAMILY] model_family must be non-empty.", context), call. = FALSE)
  if (!nzchar(model_variant)) stop(sprintf("[%s_MODEL_VARIANT] model_variant must be non-empty.", context), call. = FALSE)

  if (!is.matrix(sample_mat)) sample_mat <- as.matrix(sample_mat)
  if (!is.numeric(sample_mat) || length(dim(sample_mat)) != 2L) {
    stop(sprintf("[%s_SHAPE] sample_mat must be numeric matrix [sample x horizon].", context), call. = FALSE)
  }
  n_samp <- as.integer(nrow(sample_mat))
  horizon <- as.integer(ncol(sample_mat))
  if (!is.finite(n_samp) || !is.finite(horizon) || n_samp < 1L || horizon < 1L) {
    stop(sprintf("[%s_DIM] sample_mat must have nrow>=1 and ncol>=1.", context), call. = FALSE)
  }

  min_finite_share <- suppressWarnings(as.numeric(min_finite_share))
  if (!is.finite(min_finite_share) || min_finite_share < 0 || min_finite_share > 1) {
    min_finite_share <- 1
  }
  max_abs <- suppressWarnings(as.numeric(max_abs))
  if (!is.finite(max_abs) || max_abs <= 0) {
    max_abs <- NA_real_
  }

  dates <- as.Date(forecast_dates)
  if (length(dates) < horizon) {
    warning(
      sprintf("[%s_DATES_SHORT] forecast_dates length (%d) is shorter than horizon (%d); padding with NA.", context, length(dates), horizon),
      call. = FALSE
    )
    dates <- c(dates, rep(as.Date(NA), horizon - length(dates)))
  }
  if (length(dates) > horizon) {
    dates <- dates[seq_len(horizon)]
  }

  n_finite <- integer(horizon)
  n_nonfinite <- integer(horizon)
  finite_share <- numeric(horizon)
  min_vec <- rep(NA_real_, horizon)
  q01_vec <- rep(NA_real_, horizon)
  median_vec <- rep(NA_real_, horizon)
  q99_vec <- rep(NA_real_, horizon)
  max_vec <- rep(NA_real_, horizon)
  mean_vec <- rep(NA_real_, horizon)
  sd_vec <- rep(NA_real_, horizon)
  max_abs_vec <- rep(NA_real_, horizon)

  for (h in seq_len(horizon)) {
    vec <- as.numeric(sample_mat[, h])
    finite_idx <- is.finite(vec)
    n_finite[[h]] <- sum(finite_idx)
    n_nonfinite[[h]] <- sum(!finite_idx)
    finite_share[[h]] <- n_finite[[h]] / n_samp
    stats_h <- post_safe_numeric_summary(vec[finite_idx])
    min_vec[[h]] <- stats_h$min
    q01_vec[[h]] <- stats_h$q01
    median_vec[[h]] <- stats_h$median
    q99_vec[[h]] <- stats_h$q99
    max_vec[[h]] <- stats_h$max
    mean_vec[[h]] <- stats_h$mean
    sd_vec[[h]] <- stats_h$sd
    max_abs_vec[[h]] <- stats_h$max_abs
  }

  per_time <- data.frame(
    cutoff_date = as.character(as.Date(cutoff_date)),
    forecast_start_date = as.character(as.Date(forecast_start_date)),
    model_id = model_id,
    model_family = model_family,
    model_variant = model_variant,
    transfer_mode = as.character(ifelse(is.na(transfer_mode), NA_character_, transfer_mode)),
    lead_day = seq_len(horizon),
    forecast_date = as.character(dates),
    n_samples_nominal = as.integer(n_samp),
    n_finite = as.integer(n_finite),
    n_nonfinite = as.integer(n_nonfinite),
    finite_share = as.numeric(finite_share),
    min_draw = min_vec,
    q01_draw = q01_vec,
    median_draw = median_vec,
    q99_draw = q99_vec,
    max_draw = max_vec,
    mean_draw = mean_vec,
    sd_draw = sd_vec,
    max_abs_draw = max_abs_vec,
    stringsAsFactors = FALSE
  )

  n_total_cells <- as.integer(length(sample_mat))
  finite_all <- is.finite(as.numeric(sample_mat))
  n_finite_cells <- as.integer(sum(finite_all))
  n_nonfinite_cells <- as.integer(n_total_cells - n_finite_cells)
  finite_share_cells <- if (n_total_cells > 0L) n_finite_cells / n_total_cells else NA_real_
  stats_all <- post_safe_numeric_summary(sample_mat[finite_all])
  n_horizon_with_nonfinite <- as.integer(sum(n_nonfinite > 0L))
  min_finite_share_observed <- min(finite_share, na.rm = TRUE)
  if (!is.finite(min_finite_share_observed)) min_finite_share_observed <- NA_real_
  max_abs_observed <- max(max_abs_vec, na.rm = TRUE)
  if (!is.finite(max_abs_observed)) max_abs_observed <- NA_real_

  pass_min_finite_share <- is.finite(min_finite_share_observed) && min_finite_share_observed >= min_finite_share
  pass_max_abs <- if (is.na(max_abs)) TRUE else (is.finite(max_abs_observed) && max_abs_observed <= max_abs)
  pass <- n_nonfinite_cells == 0L && pass_min_finite_share && pass_max_abs

  violations <- character(0)
  if (n_nonfinite_cells > 0L) {
    violations <- c(violations, sprintf("nonfinite_cells=%d", n_nonfinite_cells))
  }
  if (!pass_min_finite_share) {
    violations <- c(violations, sprintf("min_finite_share_observed=%0.6f < threshold=%0.6f", min_finite_share_observed, min_finite_share))
  }
  if (!pass_max_abs) {
    violations <- c(violations, sprintf("max_abs_observed=%0.6f > threshold=%0.6f", max_abs_observed, max_abs))
  }

  summary <- data.frame(
    cutoff_date = as.character(as.Date(cutoff_date)),
    forecast_start_date = as.character(as.Date(forecast_start_date)),
    model_id = model_id,
    model_family = model_family,
    model_variant = model_variant,
    transfer_mode = as.character(ifelse(is.na(transfer_mode), NA_character_, transfer_mode)),
    horizon_days = as.integer(horizon),
    n_samples_nominal = as.integer(n_samp),
    n_total_cells = n_total_cells,
    n_finite_cells = n_finite_cells,
    n_nonfinite_cells = n_nonfinite_cells,
    finite_share_cells = as.numeric(finite_share_cells),
    n_horizon_with_nonfinite = n_horizon_with_nonfinite,
    min_finite_share_threshold = as.numeric(min_finite_share),
    min_finite_share_observed = as.numeric(min_finite_share_observed),
    max_abs_threshold = if (is.na(max_abs)) NA_real_ else as.numeric(max_abs),
    max_abs_observed = as.numeric(max_abs_observed),
    min_draw = stats_all$min,
    q01_draw = stats_all$q01,
    median_draw = stats_all$median,
    q99_draw = stats_all$q99,
    max_draw = stats_all$max,
    mean_draw = stats_all$mean,
    sd_draw = stats_all$sd,
    status = if (isTRUE(pass)) "pass" else "fail",
    violations = if (length(violations) == 0L) "" else paste(violations, collapse = " | "),
    stringsAsFactors = FALSE
  )

  list(
    per_time = per_time,
    summary = summary,
    pass = isTRUE(pass),
    violations = violations
  )
}

post_export_crps_tables <- function(
  per_time_df,
  summary_df,
  output_dir,
  table_formats = c("csv"),
  keep_na = TRUE,
  numeric_digits = 17L,
  file_suffix = ""
) {
  suffix <- post_sanitize_file_suffix(file_suffix)
  stems <- list(
    per_time = paste0("crps_forecast_per_time", suffix),
    summary = paste0("crps_forecast_summary", suffix)
  )
  formats <- unique(tolower(as.character(table_formats)))
  formats <- formats[formats %in% c("csv", "rds")]
  if (length(formats) == 0L) formats <- "csv"

  per_time_df <- as.data.frame(per_time_df, stringsAsFactors = FALSE)
  summary_df <- as.data.frame(summary_df, stringsAsFactors = FALSE)

  manifest <- post_export_tables(
    tables = list(per_time = per_time_df, summary = summary_df),
    output_dir = output_dir,
    file_stems = stems,
    formats = formats,
    keep_na = keep_na,
    sort_keys = list(
      per_time = c("model_id", "transfer_mode", "forecast_date", "lead_day"),
      summary = c("model_id", "transfer_mode")
    ),
    numeric_digits = numeric_digits
  )
  list(per_time = per_time_df, summary = summary_df, manifest = manifest)
}

post_export_crps_input_health_tables <- function(
  summary_df,
  per_time_df,
  output_dir,
  table_formats = c("csv"),
  keep_na = TRUE,
  numeric_digits = 17L,
  file_suffix = ""
) {
  suffix <- post_sanitize_file_suffix(file_suffix)
  stems <- list(
    summary = paste0("crps_input_health", suffix),
    per_time = paste0("crps_input_health_per_time", suffix)
  )
  formats <- unique(tolower(as.character(table_formats)))
  formats <- formats[formats %in% c("csv", "rds")]
  if (length(formats) == 0L) formats <- "csv"

  summary_df <- as.data.frame(summary_df, stringsAsFactors = FALSE)
  per_time_df <- as.data.frame(per_time_df, stringsAsFactors = FALSE)
  manifest <- post_export_tables(
    tables = list(summary = summary_df, per_time = per_time_df),
    output_dir = output_dir,
    file_stems = stems,
    formats = formats,
    keep_na = keep_na,
    sort_keys = list(
      summary = c("model_id", "transfer_mode"),
      per_time = c("model_id", "transfer_mode", "forecast_date", "lead_day")
    ),
    numeric_digits = numeric_digits
  )
  list(summary = summary_df, per_time = per_time_df, manifest = manifest)
}

dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  ### Gets the     Time Series Length / Replicate number
  y = check_ts(y)
  TT = nrow(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)

  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)

  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,1]) %*% R[1,,] %*% FF[,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1,] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2

  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,i])%*% R[i,,]%*% FF[,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i,] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }

  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }

  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }

  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
  ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    if (dim.df[j] <= 0L) next
    idx <- (ind.dfs[j]+1):ind.dfs[(j+1)]
    df.mat[idx, idx] = (1-df[j])/df[j]
  }
  return(df.mat)
}
#
check_mod = function(model){
  if(dlm::is.dlm(model)){
    model = dlmMod(model)
  }
  if(!is.vector(model$m0)){
    if(ncol(model$m0) != 1){
      stop("m0 must be a vector or a matrix with 1 column")
      }
    }
  p = length(model$m0)
  model$C0 = as.matrix(model$C0)
  if(p != dim(model$C0)[1] & p != dim(model$C0)[2]){
    stop("C0 must be a square matrix matching the dimension of m0")
    }
  if(!all.equal(model$C0, t(model$C0)) | !all(eigen(model$C0)$values >= 0)){
    stop("C0 must be a covariance matrix")
  }
  if(!is.vector(model$FF)){
    if(nrow(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }else{
    if(length(model$FF) != p){
      stop("FF must be a vector of length matching the dimension of m0, or a matrix with number of rows matching the dimension of m0")
    }
  }
  if(is.null(dim(model$GG)[3])){
    model$GG = as.matrix(model$GG)
  }else{
    if(is.na(dim(model$GG)[3])){
      model$GG = as.matrix(model$GG)
    }else{
      model$GG = as.array(model$GG)
    }
  }
  if(p != dim(model$GG)[1] & p != dim(model$GG)[2]){
    stop("GG must be a square matrix matching the dimension of m0, or an array with first two dimensions matching the dimension of m0")
  }
  model$m0 = as.matrix(model$m0)
  model$FF = as.matrix(model$FF)
  return(model)
}
#
check_logics = function(gam.init,sig.init,fix.gamma,fix.sigma,dqlm.ind){
  retval <- NULL
  retval$gam.init = gam.init
  retval$fix.gamma = fix.gamma
  retval$dqlm.ind = dqlm.ind
  if(dqlm.ind){
    if(gam.init!=0 | !fix.gamma){
      retval$gam.init <- gam.init <- 0
      retval$fix.gamma <- fix.gamma <- TRUE
    }
  }else{
    if(gam.init==0 && fix.gamma==TRUE){
      retval$dqlm.ind = TRUE
    }
  }
  if(fix.gamma & is.na(gam.init)){ stop("when fix.gamma = TRUE, gam.init must be specified") }
  if(fix.sigma & is.na(sig.init)){ stop("when fix.sigma = TRUE, sig.init must be specified") }
  return(retval)
}
#
check_ts = function(dat){
  dat = as.matrix(dat)
  if(all(dim(dat)>1)){
    stop("data must be univariate time-series")
  }
  if(dim(dat)[1]<dim(dat)[2]){
    dat = t(dat)
  }
  return(invisible(dat))
}
#
is.exdqlm = function(m){ return(inherits(m,"exdqlm")) }

parameters_path <- "/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"

# Check if the file exists
if (!file.exists(parameters_path)) {
  stop("The parameters file does not exist at the specified path: ", parameters_path)
}

lines <- readLines(parameters_path)

# Check if the lines variable is empty or not as expected
if (length(lines) == 0) {
  stop("No content found in the parameters file: ", parameters_path)
}

# Process each line and assign variables
for (line in lines) {
  # Remove leading and trailing whitespaces
  line <- trimws(line)
  
  # Skip empty lines and comments
  if (nchar(line) == 0 || grepl("^#", line)) next
  
  # Evaluate and assign
  eval(parse(text = line))
}
#
dlm_df = function(y, model, df, dim.df, s.priors = list(l0=1,S0=10), just.lik=FALSE){
  
  ### Gets the Time Series Length / Replicate number
  TT = length(y)
  ### Gets the State Parameter dimension and Prior Distribution Parameters
  m0 = model$m0
  C0 = model$C0
  l0 = s.priors$l0
  S0 = s.priors$S0
  n = length(m0)
  ### Constructs F and G
  FF = model$FF
  GG = model$GG
  ### Variable Saving
  ### Posterior Distribution
  m = matrix(0,TT,n)
  C = array(0,c(TT,n,n))
  ### Predictive State Distribution
  a = matrix(0,TT,n)
  R = array(0,dim = c(TT,n,n))
  P = array(0,dim = c(TT,n,n))
  W = array(0,dim = c(TT,n,n))
  ### One-Step Ahead Forecast
  f = matrix(0,TT,1)
  Q = array(0,c(TT,1,1))
  inv.Q = array(0,c(TT,1,1))
  ### Regression Variables
  e = matrix(0,TT,1)
  A = array(0,c(TT,n,1))
  ### Sample Variance
  S = vector("numeric",TT)
  l = vector("numeric",TT)
  
  # Prior Dim Check
  m0 = matrix(m0,n,1)
  C0 = matrix(C0,n,n)
  ### Discount Factor Blocking
  df.mat = make_df_mat(df,dim.df,n)
  
  ### First Update
  ### One-step state forecast
  a[1,]  = GG[,,1] %*% m0
  P[1,,] = GG[,,1] %*% C0 %*% t(GG[,,1])
  W[1,,] = df.mat * P[1,,]
  R[1,,] = P[1,,] + W[1,,]
  ### One-step ahead forecast
  f[1,] = t(FF[,,1]) %*% a[1,]
  Q[1,,] = as.matrix(1 + t(FF[,,1]) %*% R[1,,] %*% FF[,,1],1,1)
  inv.Q[1,,] = chol2inv(chol(Q[1,,]))
  ### Auxilary Variables
  e[1,]  = as.matrix(y[1] - f[1,],1,1)
  A[1,,] = R[1,,] %*% FF[,,1] %*% inv.Q[1,,]
  ### Variance update
  l[1] = l0 + 1
  S[1] = l0 * S0 / l[1] + (t(e[1,]) %*% inv.Q[1,,] %*% e[1,] / l[1])
  ### Posterior Distribution
  m[1,]  = a[1,] + as.matrix(A[1,,],n,1) %*% e[1,]
  C[1,,] = R[1,,] - as.matrix(A[1,,],n,1) %*% Q[1,,] %*% t(A[1,,])
  C[1,,] = (C[1,,] + t(C[1,,]))/2
  
  for(i in 2:TT){
    ### One-step state forecast
    a[i,]  = GG[,,i] %*% m[i-1,]
    P[i,,] = GG[,,i] %*% C[i-1,,] %*% t(GG[,,i])
    W[i,,] = df.mat * P[i,,]
    R[i,,] = P[i,,] + W[i,,]
    ### One-step ahead forecast
    f[i,] = t(FF[,,i]) %*% a[i,]
    Q[i,,] = matrix(1 + t(FF[,,i])%*% R[i,,]%*% FF[,,i],1,1)
    inv.Q[i,,] = chol2inv(chol(Q[i,,]))
    ### Auxilary Variables
    e[i,]  = as.matrix(y[i] - f[i,],1,1)
    A[i,,] = as.matrix(R[i,,] %*% FF[,,i] %*% inv.Q[i,,],n,1)
    ### Variance update
    l[i] = l[i-1] + 1
    S[i] = l[i-1] * S[i-1] / l[i] + (t(e[i,]) %*% inv.Q[i,,] %*% e[i,] / l[i])
    ### Posterior Distribution
    m[i,]  = a[i,] + as.matrix(A[i,,],n,1) %*% e[i,]
    C[i,,] = R[i,,] - as.matrix(A[i,,],n,1) %*% Q[i,,] %*% t(as.matrix(A[i,,],n,1))
    C[i,,] = (C[i,,] + t(C[i,,]))/2
  }
  
  ### Adjust By Variance
  R[1,,] = S0 * R[1,,]
  Q[1,,]   = S0 * Q[1,,]
  C[1,,]   = S[1] * C[1,,]
  for(i in 2:TT){
    R[i,,] = S[i-1] * R[i,,]
    Q[i,,]   = S[i-1] * Q[i,,]
    C[i,,]   = S[i] * C[i,,]
  }
  
  # Calculate Log-Likelihood
  det.Q = log(abs(Q[1,,])) ; llik = lgamma((l0+1)/2)-lgamma(l0/2)-log(pi*l0)/2-det.Q/2-(l0+1)*log(1+t(e[1,])%*%inv.Q[1,,]%*%e[1,]/l0)/2
  for(t in 2:TT){
    det.Q = log(abs(Q[t,,]))
    llik = llik + lgamma((l[t-1]+1)/2)-lgamma(l[t-1]/2)-log(pi*l[t-1])/2-det.Q/2-(l[t-1]+1)*log(1+t(e[t,])%*%inv.Q[t,,]%*%e[t,]/l[t-1])/2
  }
  if(just.lik){
    return(list(llik = llik))
  }
  
  ## SMOOTHING
  ### Initializes recursive relations
  sa = matrix(0,TT,n)
  sR = array(0, dim = c(TT,n,n))
  ### Runs the recursive equations
  sa[TT,]  = m[TT,]
  sR[TT,,] = C[TT,,]
  for(k in 1:(TT-1)){
    ### Computes the Auxilary recursion Variable B
    B = C[TT-k,,] %*% t(GG[,,TT-k+1]) %*% solve(R[TT-k+1,,])
    sa[TT-k,] = m[TT-k,] + B %*% (sa[TT-k+1,] - a[TT-k+1,])
    sR[TT-k,,] = C[TT-k,,] + B %*% (sR[TT-k+1,,] - R[TT-k+1,,]) %*% t(B)
  }
  ### Adjusts the variance update
  for(k in 1:TT){
    sR[TT-k,,] = S[TT] * sR[TT-k,,] / S[TT-k]
  }
  return(list(fm = m, fC = C, m = sa, C = sR,model = model, s = S, n = l))
}
#
make_df_mat = function(df,dim.df,n){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    if (dim.df[j] <= 0L) next
    idx <- (ind.dfs[j]+1):ind.dfs[(j+1)]
    df.mat[idx, idx] = (1-df[j])/df[j]
  }
  return(df.mat)
}
#
make_df_mat_k = function(df,dim.df,n,k){
  if(sum(dim.df)!=n){ stop("sum of component dimensions given in dim.df does not match m0") }
  if(length(df)!=length(dim.df)){ stop("length of component discount factors does not match length of component dimensions") }
  n.dfs = length(dim.df)
  ind.dfs = c(0,sapply(1:length(dim.df),function(x){sum(dim.df[1:x])}),n)
  df.mat = matrix(0,n,n)
  for(j in 1:n.dfs){
    if (dim.df[j] <= 0L) next
    idx <- (ind.dfs[j]+1):ind.dfs[(j+1)]
    df.mat[idx, idx] = (1-df[j]^k)/df[j]^k
  }
  return(df.mat)
}
#
H_t_k_r <- function(GG, t, k, r){
  n <- dim(GG)[1]
  I <- diag(n)
  for (s in (t+k-r):(t+k)) {
    I <- GG[,,s] %*% I   
  }
  return(I)
}
#
# Function to estimate log density using KDE for univariate data
estimate_log_density_kde_univariate <- function(data, points) {
  kde_result <- kde(data)
  density_estimates <- predict(kde_result, x = points)
  log_density <- log(density_estimates + .Machine$double.eps*100)  # Add small value to avoid log(0)
  return(log_density)
}
#
# Function to estimate the expectation term for univariate data
estimate_expectation_term_univariate <- function(sample_from_p, sample_size) {
  # Generate a sample from the standard normal distribution
  sample_from_normal <- rnorm(sample_size)
  
  # Estimate log density of p at points sampled from the standard normal distribution
  log_density_estimates <- estimate_log_density_kde_univariate(sample_from_p, sample_from_normal)
  
  # Compute the Monte Carlo estimate of the expectation
  expectation_estimate <- mean(log_density_estimates)
  
  return(expectation_estimate)
}
#
# Function to estimate the KL divergence D_KL(N(0, 1) || p) for univariate data
estimate_kl_divergence_univariate_normal_to_p <- function(sample_from_p, sample_size) {
  # Estimate the expectation term
  expectation_term <- estimate_expectation_term_univariate(sample_from_p, sample_size)
  
  # Compute the KL divergence
  kl_divergence <- -0.5 * log(2 * pi) - 0.5 - expectation_term
  
  return(kl_divergence)
}
#
# Function to estimate KL divergence using k-NN with entropy package for multivariate data
estimate_kl_divergence_knn_entropy <- function(sample_from_p, sample_size, k = 5) {
  # Generate a sample from the multivariate standard normal distribution
  sample_from_normal <- matrix(rnorm(sample_size * ncol(sample_from_p)), ncol = ncol(sample_from_p))
  
  # Estimate KL divergence using entropy package's KL.div function
  kl_divergence <- KL.divergence(sample_from_p, sample_from_normal, k = k)
  
  # Return only the final estimate
  return(tail(kl_divergence, n = 1))
}
#
# Unified function to estimate KL divergence based on the input sample
estimate_kl_divergence <- function(sample, sample_size = 10000) {
  # Check if the sample is univariate or multivariate
  if (is.vector(sample) || ncol(sample) == 1) {
    # Univariate case
    if (is.vector(sample)) {
      sample_from_p <- sample
    } else {
      sample_from_p <- sample[, 1]
    }
    
    # Estimate the KL divergence using the KDE-based method
    estimated_kl_divergence <- estimate_kl_divergence_univariate_normal_to_p(sample_from_p, sample_size)
    
  } else {
    # Multivariate case
    sample_from_p <- sample
    
    # Estimate the KL divergence using the k-NN based method with entropy package
    estimated_kl_divergence <- estimate_kl_divergence_knn_entropy(sample_from_p, sample_size, k = 5)
  }
  
  # Return the estimate
  return(estimated_kl_divergence)
}
#
# Function to estimate differential entropy using KDE for univariate data
estimate_differential_entropy_kde_univariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * diff(kde_result$eval.points)[1]
  return(entropy_estimate)
}
#
# Function to estimate differential entropy using KDE for multivariate data
estimate_differential_entropy_kde_multivariate <- function(data) {
  kde_result <- kde(data)
  estimates <- kde_result$estimate
  estimates[estimates <= 0] <- .Machine$double.eps*100 # Prevent log(0) issues
  log_estimates <- log(estimates)
  log_estimates[!is.finite(log_estimates)] <- 0 # Handle non-finite values
  entropy_estimate <- -sum(estimates * log_estimates) * prod(diff(kde_result$eval.points[[1]]))
  return(entropy_estimate)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for univariate data
estimate_kl_divergence_univariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_univariate(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_x2 <- mean(data^2)
  
  # Dimensionality is 1 for univariate data
  k <- 1
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_x2
  
  return(kl_divergence)
}
#
# Function to estimate the KL divergence D_KL(p || N(0, I)) for multivariate data
estimate_kl_divergence_multivariate <- function(data) {
  # Estimate the differential entropy H(p)
  H_p <- estimate_differential_entropy_kde_multivariate(data)
  
  # Dimensionality of the vectors
  k <- ncol(data)
  
  # Compute the expected value of the squared norm of the vectors
  E_p_xTx <- mean(rowSums(data^2))
  
  # Compute the KL divergence
  kl_divergence <- -H_p + (k / 2) * log(2 * pi) + (1 / 2) * E_p_xTx
  
  return(kl_divergence)
}
#
# Wrapper function for any sample
compute_kl_divergence <- function(sample) {
  # Ensure the input sample is a matrix
  sample <- as.matrix(sample)
  
  # Determine if the sample is univariate or multivariate
  if (ncol(sample) == 1) {
    kl_divergence <- estimate_kl_divergence_univariate(sample)
  } else {
    kl_divergence <- estimate_kl_divergence_multivariate(sample)
  }
  
  return(kl_divergence)
}
#
concatenate_matrix_columns <- function(matrix_input) {
  # Concatenate the columns of the matrix
  concatenated_vector <- c(matrix_input)
  return(concatenated_vector)
}
#
preallocate_matrix_list <- function(column_counts, num_rows) {
  # Initialize an empty list
  matrix_list <- vector("list", length(column_counts))
  
  # Loop through the column counts and create matrices
  for (i in seq_along(column_counts)) {
    num_cols <- column_counts[i]
    matrix_list[[i]] <- matrix(NA, nrow = num_rows, ncol = num_cols)
  }
  
  return(matrix_list)
}

# Prepare a numeric sample matrix for JSD/KDE diagnostics with strict shape checks.
prepare_jsd_sample_matrix <- function(sample, context = "jsd_sample", min_rows = 5L) {
  if (is.null(sample)) {
    stop(sprintf("[JSD_INPUT_NULL] %s is NULL; expected numeric vector/matrix.", context))
  }
  if (is.vector(sample)) {
    sample <- matrix(as.numeric(sample), ncol = 1L)
  } else {
    sample <- as.matrix(sample)
  }
  if (!is.numeric(sample)) {
    stop(sprintf("[JSD_INPUT_TYPE] %s is non-numeric; expected numeric sample matrix.", context))
  }
  if (is.null(dim(sample)) || length(dim(sample)) != 2L || ncol(sample) < 1L) {
    stop(sprintf("[JSD_INPUT_SHAPE] %s has invalid shape; expected an n x d matrix with d >= 1.", context))
  }

  keep <- apply(sample, 1L, function(row) all(is.finite(row)))
  n_drop <- sum(!keep)
  if (n_drop > 0L) {
    warning(
      sprintf("[JSD_INPUT_NONFINITE] %s dropped %d non-finite sample rows before KDE.", context, as.integer(n_drop)),
      call. = FALSE
    )
  }
  sample <- sample[keep, , drop = FALSE]

  if (nrow(sample) < as.integer(min_rows)) {
    stop(
      sprintf(
        "[JSD_INPUT_ROWS] %s has %d finite rows after filtering; need at least %d for stable KDE.",
        context,
        as.integer(nrow(sample)),
        as.integer(min_rows)
      )
    )
  }
  sample
}

normalize_jsd_gridsize <- function(gridsize, d) {
  d <- as.integer(d)
  gs <- as.integer(gridsize)
  if (length(gs) == 0L || any(!is.finite(gs))) {
    stop("[JSD_GRID_INVALID] JSD gridsize must contain at least one finite integer.")
  }
  if (length(gs) == 1L) {
    gs <- rep(gs, d)
  } else if (length(gs) < d) {
    gs <- c(gs, rep(tail(gs, 1L), d - length(gs)))
  } else if (length(gs) > d) {
    gs <- gs[seq_len(d)]
  }
  if (any(gs < 2L)) {
    stop("[JSD_GRID_RANGE] JSD gridsize entries must be >= 2.")
  }
  gs
}

extract_kde_eval_points <- function(kde_obj, d, context = "jsd_kde") {
  gp <- kde_obj$eval.points
  d <- as.integer(d)

  if (d == 1L) {
    if (is.numeric(gp)) {
      return(list(as.numeric(gp)))
    }
    if (is.list(gp) && length(gp) == 1L && is.numeric(gp[[1L]])) {
      return(list(as.numeric(gp[[1L]])))
    }
    if (is.list(gp) && length(gp) > 1L &&
        all(vapply(gp, function(v) is.numeric(v) && length(v) == 1L, logical(1)))) {
      return(list(as.numeric(unlist(gp, use.names = FALSE))))
    }
    stop(sprintf("[JSD_KDE_AXIS_1D] %s has unsupported 1D eval.points structure.", context))
  }

  if (!is.list(gp) || length(gp) != d) {
    stop(sprintf("[JSD_KDE_AXES] %s expected %d KDE eval-point axes; found %d.", context, d, length(gp)))
  }
  out <- lapply(gp, as.numeric)
  axis_lengths <- vapply(out, length, integer(1))
  if (any(axis_lengths < 2L)) {
    stop(sprintf("[JSD_KDE_AXIS_RANGE] %s contains degenerate KDE axis lengths: %s.", context, paste(axis_lengths, collapse = ",")))
  }
  out
}

jsd_warn_once <- local({
  warned <- new.env(parent = emptyenv())
  function(key, message_text) {
    if (!exists(key, envir = warned, inherits = FALSE)) {
      assign(key, TRUE, envir = warned)
      warning(message_text, call. = FALSE)
    }
    invisible(NULL)
  }
})

compute_jsd_axis_bandwidth <- function(x, context = "jsd", axis = 1L) {
  vals <- as.numeric(x[is.finite(x)])
  if (length(vals) < 2L) {
    stop(sprintf("[JSD_BANDWIDTH_ROWS] %s axis %d has fewer than 2 finite values.", context, as.integer(axis)))
  }

  bw_primary <- suppressWarnings(tryCatch(stats::bw.nrd0(vals), error = function(e) NA_real_))
  sd_x <- suppressWarnings(stats::sd(vals))
  iqr_x <- suppressWarnings(stats::IQR(vals) / 1.349)
  mad_x <- suppressWarnings(stats::mad(vals, center = stats::median(vals), constant = 1.4826))
  range_x <- suppressWarnings(diff(range(vals)))

  scale_ref <- suppressWarnings(max(c(sd_x, iqr_x, mad_x, range_x / 4, 1.0), na.rm = TRUE))
  if (!is.finite(scale_ref) || scale_ref <= 0) {
    scale_ref <- 1.0
  }

  bw_fallback <- 0.9 * scale_ref * length(vals)^(-1 / 5)
  if (!is.finite(bw_fallback) || bw_fallback <= 0) {
    bw_fallback <- scale_ref
  }

  bw_floor <- max(1.0e-6, sqrt(.Machine$double.eps) * scale_ref)
  bw <- bw_primary
  if (!is.finite(bw) || bw <= 0) {
    bw <- bw_fallback
    jsd_warn_once(
      paste0("jsd_bw_primary:", context, ":", axis),
      sprintf(
        "[JSD_BANDWIDTH_PRIMARY] %s axis %d could not use bw.nrd0; falling back to scale-based bandwidth %.6g.",
        context,
        as.integer(axis),
        bw
      )
    )
  }
  if (!is.finite(bw) || bw <= 0) {
    bw <- bw_floor
  }
  if (bw < bw_floor) {
    jsd_warn_once(
      paste0("jsd_bw_floor:", context, ":", axis),
      sprintf(
        "[JSD_BANDWIDTH_FLOOR] %s axis %d bandwidth %.6g raised to floor %.6g.",
        context,
        as.integer(axis),
        bw,
        bw_floor
      )
    )
    bw <- bw_floor
  }
  as.numeric(bw)
}

repair_jsd_bandwidth_matrix <- function(H, context = "jsd", eig_floor = 1.0e-8) {
  if (!is.numeric(H) || is.null(dim(H)) || length(dim(H)) != 2L || nrow(H) != ncol(H)) {
    return(NULL)
  }
  H <- 0.5 * (H + t(H))
  if (any(!is.finite(H))) {
    return(NULL)
  }
  eig <- tryCatch(eigen(H, symmetric = TRUE, only.values = TRUE), error = function(e) NULL)
  if (is.null(eig) || any(!is.finite(eig$values))) {
    return(NULL)
  }
  min_eig <- min(eig$values)
  floor_val <- max(as.numeric(eig_floor), .Machine$double.eps)
  if (min_eig < floor_val) {
    ridge <- floor_val - min_eig
    H <- H + diag(ridge, nrow(H))
    jsd_warn_once(
      paste0("jsd_bw_pd:", context),
      sprintf(
        "[JSD_BANDWIDTH_PD] %s added diagonal ridge %.6g to stabilize KDE bandwidth matrix.",
        context,
        ridge
      )
    )
  }
  H
}

compute_jsd_bandwidth_spec <- function(sample_m, context = "jsd") {
  d <- ncol(sample_m)
  if (d == 1L) {
    return(list(
      arg = "h",
      value = compute_jsd_axis_bandwidth(sample_m[, 1L], context = context, axis = 1L),
      strategy = "bw.nrd0"
    ))
  }

  hpi_err <- NULL
  H_full <- tryCatch(
    ks::Hpi(sample_m),
    error = function(e) {
      hpi_err <<- conditionMessage(e)
      NULL
    }
  )
  H_full <- repair_jsd_bandwidth_matrix(H_full, context = paste0(context, ".Hpi"))
  if (!is.null(H_full) && all(dim(H_full) == c(d, d))) {
    return(list(arg = "H", value = H_full, strategy = "Hpi"))
  }

  bw_diag <- vapply(
    seq_len(d),
    function(j) compute_jsd_axis_bandwidth(sample_m[, j], context = context, axis = j),
    numeric(1)
  )
  H_diag <- diag(pmax(bw_diag, 1.0e-6)^2, d)
  H_diag <- repair_jsd_bandwidth_matrix(H_diag, context = paste0(context, ".diag"))
  if (is.null(H_diag)) {
    stop(sprintf("[JSD_BANDWIDTH_DIAG] %s failed to construct a positive-definite diagonal KDE bandwidth matrix.", context))
  }

  jsd_warn_once(
    paste0("jsd_bw_fallback:", context),
    sprintf(
      "[JSD_BANDWIDTH_FALLBACK] %s falling back to diagonal KDE bandwidths%s.",
      context,
      if (!is.null(hpi_err) && nzchar(hpi_err)) paste0(" after Hpi error: ", hpi_err) else ""
    )
  )

  list(arg = "H", value = H_diag, strategy = "diag_bw")
}

# Jensen-Shannon divergence between sample KDE and standard Normal in matching dimension.
compute_jsd_to_standard_normal <- function(sample, gridsize = 100L, context = "jsd") {
  if (!requireNamespace("ks", quietly = TRUE)) {
    stop("[JSD_DEP_KS] compute_jsd_to_standard_normal requires package 'ks'.")
  }
  if (!requireNamespace("mvtnorm", quietly = TRUE)) {
    stop("[JSD_DEP_MVTNORM] compute_jsd_to_standard_normal requires package 'mvtnorm'.")
  }

  sample_m <- prepare_jsd_sample_matrix(sample, context = context)
  d <- ncol(sample_m)
  if (d > 3L) {
    stop(sprintf("[JSD_DIMENSION] %s has dimension %d; JSD KDE grid diagnostics support d <= 3.", context, as.integer(d)))
  }

  gs <- normalize_jsd_gridsize(gridsize, d)
  bandwidth_spec <- compute_jsd_bandwidth_spec(sample_m, context = context)
  kde_obj <- if (identical(bandwidth_spec$arg, "h")) {
    ks::kde(sample_m, h = bandwidth_spec$value, gridsize = gs)
  } else {
    ks::kde(sample_m, H = bandwidth_spec$value, gridsize = gs)
  }

  pdf_p <- kde_obj$estimate
  dim_p <- dim(pdf_p)
  if (is.null(dim_p)) {
    dim_p <- length(pdf_p)
  }
  dim_p <- as.integer(dim_p)
  if (length(dim_p) != d) {
    stop(
      sprintf(
        "[JSD_KDE_DIM_MISMATCH] %s KDE estimate dimension mismatch: sample d=%d but estimate dim length=%d.",
        context,
        as.integer(d),
        as.integer(length(dim_p))
      )
    )
  }
  if (any(dim_p < 2L)) {
    stop(sprintf("[JSD_KDE_DIM_RANGE] %s KDE estimate has degenerate dimensions: %s.", context, paste(dim_p, collapse = "x")))
  }

  grid_points <- extract_kde_eval_points(kde_obj, d, context = context)
  grid_df <- do.call(expand.grid, c(grid_points, KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE))
  grid_matrix <- as.matrix(grid_df)
  if (!is.numeric(grid_matrix) || ncol(grid_matrix) != d) {
    stop(sprintf("[JSD_GRID_SHAPE] %s generated invalid KDE grid matrix shape.", context))
  }

  mean_q <- rep(0, d)
  cov_q <- diag(d)
  pdf_q_vec <- mvtnorm::dmvnorm(grid_matrix, mean = mean_q, sigma = cov_q)
  if (length(pdf_q_vec) != prod(dim_p)) {
    stop(
      sprintf(
        "[JSD_DENSITY_GRID_MISMATCH] %s density-grid mismatch: q length=%d vs p grid size=%d.",
        context,
        as.integer(length(pdf_q_vec)),
        as.integer(prod(dim_p))
      )
    )
  }
  pdf_q <- array(pdf_q_vec, dim = dim_p)

  sum_p <- sum(pdf_p)
  sum_q <- sum(pdf_q)
  if (!is.finite(sum_p) || sum_p <= 0 || !is.finite(sum_q) || sum_q <= 0) {
    stop(sprintf("[JSD_DENSITY_NORMALIZATION] %s invalid KDE or reference density normalization constants.", context))
  }
  pdf_p <- pdf_p / sum_p
  pdf_q <- pdf_q / sum_q

  epsilon <- 1e-10
  kl_divergence <- function(p, q) {
    p <- p + epsilon
    q <- q + epsilon
    sum(p * log(p / q))
  }
  m <- 0.5 * (pdf_p + pdf_q)
  as.numeric(0.5 * kl_divergence(pdf_p, m) + 0.5 * kl_divergence(pdf_q, m))
}

resolve_time_cuts <- function(
  timestamps,
  cutoff_date = if (exists("CUTOFF_DATE", inherits = TRUE)) get("CUTOFF_DATE", inherits = TRUE) else NA,
  anchor_dates = c("2012-08-01", "2016-05-01", "2016-09-15", "2019-08-01"),
  anchor_tolerance_days = 3L,
  context = "time_cuts"
) {
  dates <- as.Date(timestamps)
  n <- length(dates)
  if (n < 8L) {
    stop(sprintf("[%s] need at least 8 timestamps to build stable plotting windows.", context), call. = FALSE)
  }

  sanitize_cuts <- function(idx) {
    idx <- as.integer(round(idx))
    if (length(idx) != 4L || any(!is.finite(idx))) return(NULL)
    idx <- pmin(pmax(idx, 1L), n)
    for (i in 2:4) {
      if (idx[[i]] <= idx[[i - 1L]]) idx[[i]] <- idx[[i - 1L]] + 1L
    }
    if (idx[[4L]] > n) {
      shift <- idx[[4L]] - n
      idx <- idx - shift
      if (idx[[1L]] < 1L) idx <- idx + (1L - idx[[1L]])
      for (i in 2:4) {
        if (idx[[i]] <= idx[[i - 1L]]) idx[[i]] <- idx[[i - 1L]] + 1L
      }
    }
    if (idx[[1L]] < 1L || idx[[4L]] > n || any(diff(idx) <= 0L)) return(NULL)
    idx
  }

  anchors <- as.Date(anchor_dates)
  anchor_idx_exact <- match(anchors, dates)
  if (all(!is.na(anchor_idx_exact))) {
    anchor_cuts <- sanitize_cuts(anchor_idx_exact)
    if (!is.null(anchor_cuts)) return(anchor_cuts)
  }

  nearest_index <- function(target) {
    target <- as.Date(target)
    if (is.na(target)) return(NA_integer_)
    as.integer(which.min(abs(as.numeric(dates - target))))
  }

  tol_days <- suppressWarnings(as.numeric(anchor_tolerance_days))
  if (!is.finite(tol_days) || tol_days < 0) tol_days <- 0
  anchor_idx_near <- vapply(anchors, nearest_index, integer(1))
  if (!anyNA(anchor_idx_near)) {
    anchor_dist <- abs(as.numeric(dates[anchor_idx_near] - anchors))
    if (all(is.finite(anchor_dist)) && all(anchor_dist <= tol_days)) {
      anchor_cuts <- sanitize_cuts(anchor_idx_near)
      if (!is.null(anchor_cuts)) return(anchor_cuts)
    }
  }

  cutoff_date <- suppressWarnings(as.Date(cutoff_date))
  hist_end <- if (!is.na(cutoff_date)) {
    idx <- which(dates <= cutoff_date)
    if (length(idx) > 0L) max(idx) else n
  } else {
    n
  }
  hist_end <- min(max(8L, hist_end), n)

  w2_end <- max(4L, hist_end)
  w2_start <- max(3L, w2_end - 365L * 3L)
  w1_end <- max(2L, w2_start - 1L)
  w1_start <- max(1L, w1_end - 365L * 4L)
  fallback_cuts <- sanitize_cuts(c(w1_start, w1_end, w2_start, w2_end))
  if (!is.null(fallback_cuts)) return(fallback_cuts)

  idx_grid <- unique(as.integer(round(c(0.10, 0.45, 0.55, 0.90) * (hist_end - 1L) + 1L)))
  if (length(idx_grid) < 4L) {
    idx_grid <- as.integer(round(seq(1L, hist_end, length.out = 4L)))
  } else if (length(idx_grid) > 4L) {
    idx_grid <- idx_grid[c(1L, 2L, length(idx_grid) - 1L, length(idx_grid))]
  }
  final_cuts <- sanitize_cuts(idx_grid)
  if (is.null(final_cuts)) {
    stop(sprintf("[%s] unable to derive valid time_cuts.", context), call. = FALSE)
  }
  final_cuts
}

safe_time_index <- function(start_idx, end_idx, n, context = "time_index", prefer_tail = TRUE) {
  n <- as.integer(n)
  if (!is.finite(n) || n < 1L) {
    stop(sprintf("[%s] n must be a positive integer; got: %s", context, paste(n, collapse = ",")), call. = FALSE)
  }

  s <- suppressWarnings(as.integer(round(start_idx)))
  e <- suppressWarnings(as.integer(round(end_idx)))
  if (!is.finite(s)) s <- 1L
  if (!is.finite(e)) e <- n

  s <- max(1L, min(n, s))
  e <- max(1L, min(n, e))

  if (s > e) {
    if (isTRUE(prefer_tail)) {
      width_raw <- suppressWarnings(as.integer(round(end_idx - start_idx + 1L)))
      if (!is.finite(width_raw) || width_raw < 1L) width_raw <- 1L
      width <- min(n, width_raw)
      e <- n
      s <- max(1L, e - width + 1L)
    } else {
      s <- 1L
      e <- 1L
    }
  }

  seq.int(s, e)
}
