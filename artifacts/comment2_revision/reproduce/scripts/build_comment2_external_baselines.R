#!/usr/bin/env Rscript
# External baselines for referee major comment 2. All research fits and current
# publication scores are read only. A fresh output directory is mandatory.
# Forecast generation sees only pre-origin training observations; verification
# outcomes enter only after the three predictive distributions have been frozen.
# The curated input bundle supports an exact portable replay without raw GRIBs.

c2_assert <- function(ok, message) {
  if (length(ok) != 1L || is.na(ok) || !ok) stop(message, call. = FALSE)
}
c2_hash <- function(path) digest::digest(file = path, algo = "sha256")
c2_json <- function(x, path) jsonlite::write_json(x, path, auto_unbox = TRUE,
                                                pretty = TRUE, digits = NA, null = "null")
c2_read <- function(path) utils::read.csv(path, check.names = FALSE, stringsAsFactors = FALSE)
c2_write <- function(x, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  # Preserve binary doubles through CSV/replay; write.table normally rounds them.
  for (name in names(x)) if (is.numeric(x[[name]]))
    x[[name]] <- vapply(x[[name]], function(v) if (is.na(v)) "" else
      sprintf("%.17g", v), character(1))
  con <- if (grepl("\\.gz$", path)) gzfile(path, "wt") else file(path, "wt")
  on.exit(close(con))
  utils::write.table(x, con, sep = ",", row.names = FALSE, col.names = TRUE,
                     quote = TRUE, na = "", qmethod = "double")
}
c2_family <- function(issue_date, settings) ifelse(
  as.Date(issue_date) < as.Date(settings$product_family_switch), "GloFAS-2.x", "GloFAS-3.x")
c2_calendar_day <- function(dates, year = 2000L) as.integer(format(
  as.Date(paste0(year, "-", format(as.Date(dates), "%m-%d"))), "%j"))
c2_calendar_distance <- function(a, b) pmin(abs(a - b), 366L - abs(a - b))
c2_probabilities <- function(settings) seq_len(settings$evaluation_points) /
  (settings$evaluation_points + 1)

c2_qtnorm <- function(p, mu, sigma) {
  c2_assert(all(is.finite(mu)) && all(is.finite(sigma)) && all(sigma > 0),
            "Nonfinite or nonpositive EMOS distribution parameters")
  # Work in the survival tail to avoid subtracting nearly equal CDF values.
  log_survival_zero <- stats::pnorm(-mu / sigma, lower.tail = FALSE, log.p = TRUE)
  out <- mu + sigma * stats::qnorm(log_survival_zero + log1p(-p),
                                 lower.tail = FALSE, log.p = TRUE)
  c2_assert(all(is.finite(out)) && all(out >= -1e-10), "Invalid truncated-normal quantiles")
  pmax(0, out)
}

c2_tn_crps <- function(y, mu, sigma) {
  # Closed-form TN CRPS expressed with log-survival ratios. This is the usual
  # truncated-normal EMOS score, with stable tails where direct CDF divisions
  # in scoringRules::crps_tnorm can give 0/0 for very negative mu/sigma.
  z <- (y - mu) / sigma
  log_Z <- stats::pnorm(mu / sigma, log.p = TRUE)
  survival_ratio <- exp(stats::pnorm(z, lower.tail = FALSE, log.p = TRUE) - log_Z)
  density_ratio <- exp(stats::dnorm(z, log = TRUE) - log_Z)
  final_ratio <- exp(stats::pnorm(sqrt(2) * mu / sigma, log.p = TRUE) - 2 * log_Z)
  sigma * (z * (1 - 2 * survival_ratio) + 2 * density_ratio - final_ratio / sqrt(pi))
}
c2_valid_training_scores <- function(value, n_expected) {
  length(value) == n_expected && all(is.finite(value)) && all(value >= -1e-12)
}

c2_training <- function(history, features, origin, settings, lead = NULL) {
  T <- as.Date(origin)
  c2_assert(all(as.Date(history$date) <= T), "Training history contains post-origin outcomes")
  issue <- as.Date(features$issue_date)
  target <- as.Date(features$target_date)
  keep <- issue < T & issue >= T - settings$emos_training_issue_days & target <= T &
    target >= as.Date(settings$historical_start) &
    features$product_family == c2_family(origin, settings)
  if (!is.null(lead)) keep <- keep & features$lead_day == lead
  train <- features[keep, , drop = FALSE]
  train$observed <- history$Y[match(train$target_date, history$date)]
  c2_assert(nrow(train) > 0L && all(is.finite(train$observed)), "Missing matured training observations")
  c2_assert(all(as.Date(train$issue_date) < T) && all(as.Date(train$target_date) <= T),
            "Training issue/target dates violate origin")
  train[order(train$lead_day, train$issue_date), , drop = FALSE]
}

c2_emos_fit <- function(train, settings) {
  c2_assert(nrow(train) >= settings$emos_minimum_cases_per_lead,
            "Too few mature, version-compatible EMOS training cases")
  y <- train$observed; m <- train$ensemble_mean; v <- train$ensemble_variance
  c2_assert(all(is.finite(c(y, m, v))) && all(y >= 0) && all(v >= 0), "Invalid EMOS training values")
  lower <- as.numeric(settings$emos_lower_bounds); upper <- as.numeric(settings$emos_upper_bounds)
  objective <- function(theta) {
    sigma <- sqrt(exp(theta[[3L]]) + theta[[4L]] * v)
    value <- tryCatch(suppressWarnings(c2_tn_crps(
      y, mu = theta[[1L]] + theta[[2L]] * m, sigma = sigma)),
      error = function(e) rep(NA_real_, length(y)))
    # A CRPS cannot be negative. Extreme, irrelevant optimizer explorations can
    # lose precision through tail cancellation, so reject those evaluations.
    if (!c2_valid_training_scores(value, length(y))) return(1e10)
    mean(pmax(0, value))
  }
  ols <- stats::lm.fit(cbind(1, m), y)$coefficients
  if (any(!is.finite(ols))) ols <- c(mean(y), 0)
  ols <- pmax(lower[1:2], pmin(upper[1:2], ols))
  residual_variance <- max(mean((y - ols[[1L]] - ols[[2L]] * m)^2), 1e-4)
  variance_coefficient_scale <- max(1, min(1e5, residual_variance / max(mean(v), 1e-10)))
  starts <- list(
    c(ols, log(residual_variance), 0),
    c(ols, log(residual_variance / 2), 0.5),
    c(0, 1, log(max(stats::var(y - m) / 2, 1e-4)), 1),
    c(mean(y), 0, log(max(stats::var(y), 1e-4)), 0)
  )
  attempts <- vector("list", length(starts))
  fits <- vector("list", length(starts))
  for (i in seq_along(starts)) {
    initial <- pmax(lower, pmin(upper, starts[[i]]))
    fit <- tryCatch(stats::optim(initial, objective, method = "L-BFGS-B",
      lower = lower, upper = upper, control = list(maxit = settings$emos_optimizer_maxit,
        factr = 1e5, pgtol = 1e-8, ndeps = rep(1e-5, 4),
        parscale = c(1, 1, 1, variance_coefficient_scale))), error = function(e) NULL)
    fits[[i]] <- fit
    attempts[[i]] <- data.frame(start = i, converged = !is.null(fit) && fit$convergence == 0,
      convergence_code = if (is.null(fit)) 999L else fit$convergence,
      objective = if (is.null(fit)) NA_real_ else fit$value,
      message = if (is.null(fit)) "optimizer error" else if (is.null(fit$message)) "" else as.character(fit$message))
  }
  attempts <- do.call(rbind, attempts)
  eligible <- which(attempts$converged & is.finite(attempts$objective) & attempts$objective < 1e9)
  c2_assert(length(eligible) > 0L, "No converged EMOS multistart fit")
  chosen <- eligible[which.min(attempts$objective[eligible])]
  fit <- fits[[chosen]]; theta <- fit$par
  gradient <- vapply(seq_along(theta), function(j) {
    step <- 1e-5 * max(1, abs(theta[[j]]))
    plus <- minus <- theta
    plus[[j]] <- min(upper[[j]], theta[[j]] + step)
    minus[[j]] <- max(lower[[j]], theta[[j]] - step)
    (objective(plus) - objective(minus)) / (plus[[j]] - minus[[j]])
  }, numeric(1))
  lower_active <- abs(theta - lower) < 1e-5
  upper_active <- abs(theta - upper) < 1e-5
  projected <- gradient
  projected[lower_active & gradient > 0] <- 0
  projected[upper_active & gradient < 0] <- 0
  projected_scaled <- projected * c(1, 1, 1, variance_coefficient_scale)
  c2_assert(max(abs(projected_scaled)) <= settings$emos_projected_gradient_tolerance,
            sprintf("EMOS scaled projected gradient too large: %.5g", max(abs(projected_scaled))))
  # b=0 or d=0 are valid reduced EMOS models; arbitrary safety bounds must be inactive.
  c2_assert(!any(upper_active) && !lower_active[[1L]] && !lower_active[[3L]],
            paste("EMOS fit reaches an artificial numerical safety bound:",
                  paste(c("a", "b", "log_c", "d"), signif(theta, 8), collapse = ", ")))
  attempts$selected <- seq_len(nrow(attempts)) == chosen
  list(theta = theta, objective = objective(theta), chosen_start = chosen,
       attempts = attempts, projected_gradient = max(abs(projected_scaled)),
       projected_gradient_raw = max(abs(projected)), variance_coefficient_scale = variance_coefficient_scale,
       active_bounds = paste(c("a", "b", "log_c", "d")[lower_active | upper_active], collapse = "|"))
}

c2_predict_origin <- function(history, features, origin, settings) {
  T <- as.Date(origin)
  c2_assert(all(as.Date(history$date) <= T), "Prediction history contains post-origin outcomes")
  dates <- as.character(T + seq_len(settings$horizon_days))
  p <- c2_probabilities(settings)
  current <- features[features$issue_date == origin, , drop = FALSE]
  current <- current[order(current$lead_day), , drop = FALSE]
  c2_assert(identical(as.integer(current$lead_day), seq_len(settings$horizon_days)) &&
              identical(as.character(current$target_date), dates), "Forecast feature dates/leads do not match origin")
  c2_assert(tail(history$date, 1L) == origin, "Persistence requires an observation at the origin")
  prediction <- list(
    `CLIM-SEASONAL` = matrix(NA_real_, length(p), length(dates)),
    PERSISTENCE = matrix(tail(history$Y, 1L), length(p), length(dates)),
    `EMOS-GLOFAS` = matrix(NA_real_, length(p), length(dates)))
  parameters <- diagnostics <- attempts <- training <- vector("list", length(dates))
  history_calendar <- c2_calendar_day(history$date, settings$climatology_calendar_year)
  for (lead in seq_along(dates)) {
    use <- c2_calendar_distance(history_calendar,
      c2_calendar_day(dates[[lead]], settings$climatology_calendar_year)) <= settings$climatology_half_window_days
    c2_assert(sum(use) >= 100L, "Too few climatology observations")
    prediction[["CLIM-SEASONAL"]][, lead] <- stats::quantile(history$Y[use], p,
      type = settings$climatology_quantile_type, names = FALSE)
    train <- c2_training(history, features, origin, settings, lead)
    fit <- c2_emos_fit(train, settings)
    theta <- fit$theta
    mu <- theta[[1L]] + theta[[2L]] * current$ensemble_mean[[lead]]
    sigma <- sqrt(exp(theta[[3L]]) + theta[[4L]] * current$ensemble_variance[[lead]])
    prediction[["EMOS-GLOFAS"]][, lead] <- c2_qtnorm(p, mu, sigma)
    parameters[[lead]] <- data.frame(cutoff_date = origin, lead_day = lead,
      a = theta[[1L]], b = theta[[2L]], c = exp(theta[[3L]]), d = theta[[4L]],
      training_mean_analytic_crps = fit$objective, selected_start = fit$chosen_start,
      projected_gradient = fit$projected_gradient, active_bounds = fit$active_bounds,
      projected_gradient_raw = fit$projected_gradient_raw,
      variance_coefficient_optimizer_scale = fit$variance_coefficient_scale,
      forecast_mu = mu, forecast_sigma = sigma)
    diagnostics[[lead]] <- data.frame(cutoff_date = origin, lead_day = lead,
      training_cases = nrow(train), first_issue_date = min(train$issue_date),
      last_issue_date = max(train$issue_date), first_target_date = min(train$target_date),
      last_target_date = max(train$target_date), product_family = unique(train$product_family),
      training_observed_min = min(train$observed), training_observed_max = max(train$observed),
      climatology_cases = sum(use), climatology_first_date = min(history$date[use]),
      climatology_last_date = max(history$date[use]),
      converged_starts = sum(fit$attempts$converged), attempted_starts = nrow(fit$attempts))
    attempts[[lead]] <- cbind(cutoff_date = origin, lead_day = lead, fit$attempts)
    training[[lead]] <- cbind(cutoff_date = origin, train)
  }
  list(predictions = prediction, parameters = do.call(rbind, parameters),
       training_diagnostics = do.call(rbind, diagnostics), attempts = do.call(rbind, attempts),
       training_pairs = do.call(rbind, training), dates = dates)
}

c2_source_row <- function(path, role) data.frame(role = role,
  source_path = normalizePath(path, mustWork = TRUE), sha256 = c2_hash(path),
  bytes = file.info(path)$size, stringsAsFactors = FALSE)
c2_source_check <- function(rows) {
  c2_assert(all(file.exists(rows$source_path)), "An original input disappeared during construction")
  after <- vapply(rows$source_path, c2_hash, character(1))
  c2_assert(identical(unname(after), rows$sha256), "An original input changed during construction")
}

c2_legacy_inputs <- function(article) {
  manifest_path <- file.path(article, "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv")
  manifest <- c2_read(manifest_path)
  scores <- source_rows <- list(); k <- 0L
  source_rows[[1L]] <- c2_source_row(manifest_path, "frozen_publication_manifest")
  for (i in seq_len(nrow(manifest))) {
    row <- manifest[i, ]
    path <- file.path(dirname(row$score_source), "crps_forecast_per_time.csv")
    all_rows <- c2_read(path)
    rows <- all_rows[all_rows$model_variant == row$family, , drop = FALSE]
    rows <- rows[order(rows$lead_day), , drop = FALSE]
    c2_assert(identical(as.integer(rows$lead_day), 1:28), "Incomplete frozen model-score leads")
    c2_assert(abs(mean(rows$crps) - as.numeric(row$crps_exact)) < 1e-12,
              "Existing 28-day scores do not match the frozen manifest")
    k <- k + 1L
    scores[[k]] <- data.frame(cutoff_date = rows$cutoff_date,
      model = row$manuscript_label, forecast_date = rows$forecast_date,
      lead_day = rows$lead_day, crps = rows$crps,
      n_samples_nominal = rows$n_samples_nominal, score_method = rows$score_method,
      tau_rule = rows$tau_rule, score_scale = rows$score_scale,
      source_class = "frozen_existing_score", source_path = path)
    source_rows[[length(source_rows) + 1L]] <- c2_source_row(path, "existing_model_per_time_scores")
    source_rows[[length(source_rows) + 1L]] <- c2_source_row(row$score_source, "existing_model_score_summary")
    if (row$manuscript_label == "exAL-M-T1") {
      for (id in c("glofas_ensemble", "nws_nwm_ensemble")) {
        raw <- all_rows[all_rows$model_id == id, , drop = FALSE]
        k <- k + 1L
        scores[[k]] <- data.frame(cutoff_date = raw$cutoff_date,
          model = if (id == "glofas_ensemble") "RAW-GLOFAS" else "RAW-NWS",
          forecast_date = raw$forecast_date, lead_day = raw$lead_day, crps = raw$crps,
          n_samples_nominal = raw$n_samples_nominal, score_method = raw$score_method,
          tau_rule = raw$tau_rule, score_scale = raw$score_scale,
          source_class = "frozen_existing_score", source_path = path)
      }
    }
  }
  list(scores = do.call(rbind, scores), sources = unique(do.call(rbind, source_rows)))
}

c2_prepare_inputs <- function(config, article, scorer_path, directory) {
  settings <- config$settings
  master <- c2_read(config$usgs_master)
  c2_assert(all(c("date", "discharge_cms") %in% names(master)), "USGS master schema changed")
  master <- master[master$date >= settings$historical_start, c("date", "discharge_cms")]
  master <- master[order(master$date), ]
  c2_assert(!anyDuplicated(master$date) && all(is.finite(master$discharge_cms)) &&
              all(master$discharge_cms >= 0), "Invalid USGS dates or discharge")
  master$Y <- log1p(master$discharge_cms)
  all_files <- sort(list.files(config$glofas_archive, pattern = "glofas_members\\.csv$",
                              recursive = TRUE, full.names = TRUE))
  issue_dates <- sub("^issue_date=", "", basename(dirname(all_files)))
  use <- issue_dates <= max(settings$origins)
  files <- all_files[use]; issue_dates <- issue_dates[use]
  c2_assert(length(files) > 0L && !anyDuplicated(issue_dates), "Missing/duplicate GloFAS archive issues")
  features <- sources <- vector("list", length(files))
  for (i in seq_along(files)) {
    rows <- c2_read(files[[i]])
    members <- grep("^member_[0-9]+$", names(rows), value = TRUE)
    c2_assert(length(members) == 51L && nrow(rows) == settings$horizon_days,
              paste("GloFAS archive shape changed:", files[[i]]))
    values <- as.matrix(rows[members])
    c2_assert(all(is.finite(values)) && all(values >= 0), "Invalid GloFAS archive member")
    lead <- as.integer(as.Date(rows$target_date) - as.Date(issue_dates[[i]]))
    c2_assert(identical(lead, seq_len(settings$horizon_days)), "GloFAS target/lead dates are not contiguous")
    Y <- log1p(values)
    features[[i]] <- data.frame(issue_date = issue_dates[[i]], target_date = rows$target_date,
      lead_day = lead, product_family = c2_family(issue_dates[[i]], settings),
      ensemble_mean = rowMeans(Y), ensemble_variance = apply(Y, 1L, stats::var),
      n_members = ncol(Y))
    sources[[i]] <- c2_source_row(files[[i]], "glofas_member_archive")
  }
  features <- do.call(rbind, features)
  history <- master[master$date <= max(settings$origins), ]
  dates <- unique(unlist(lapply(settings$origins, function(t)
    as.character(as.Date(t) + seq_len(settings$horizon_days)))))
  verification <- master[match(sort(dates), master$date), ]
  c2_assert(all(!is.na(verification$date)) && nrow(verification) == length(dates), "Missing verification observations")
  legacy <- c2_legacy_inputs(article)
  sources <- unique(rbind(do.call(rbind, sources),
    c2_source_row(config$usgs_master, "usgs_master"), legacy$sources,
    c2_source_row(scorer_path, "unchanged_current_scorer")))
  dir.create(directory, recursive = TRUE)
  c2_write(history, file.path(directory, "usgs_history.csv.gz"))
  c2_write(verification, file.path(directory, "usgs_verification.csv"))
  c2_write(features, file.path(directory, "forecast_features.csv.gz"))
  c2_write(legacy$scores, file.path(directory, "legacy_per_time.csv"))
  c2_write(sources, file.path(directory, "source_manifest.csv"))
  file.copy(scorer_path, file.path(directory, "current_scorer.R"))
  c2_json(settings, file.path(directory, "settings.json"))
  files <- sort(list.files(directory, full.names = TRUE))
  index <- data.frame(file = basename(files), sha256 = vapply(files, c2_hash, character(1)),
                      bytes = file.info(files)$size)
  c2_write(index, file.path(directory, "bundle_checksums.csv"))
  c2_source_check(sources)
  invisible(sources)
}

c2_load_bundle <- function(path, settings) {
  index <- c2_read(file.path(path, "bundle_checksums.csv"))
  c2_assert(all(!grepl("/|\\\\|^\\.", index$file)), "Unsafe curated bundle path")
  for (i in seq_len(nrow(index))) c2_assert(
    file.exists(file.path(path, index$file[[i]])) &&
      c2_hash(file.path(path, index$file[[i]])) == index$sha256[[i]], "Curated bundle checksum mismatch")
  frozen <- jsonlite::read_json(file.path(path, "settings.json"), simplifyVector = TRUE)
  c2_assert(isTRUE(all.equal(frozen, settings, check.attributes = FALSE)),
            "Curated bundle computational settings do not match configuration")
  history <- c2_read(file.path(path, "usgs_history.csv.gz"))
  features <- c2_read(file.path(path, "forecast_features.csv.gz"))
  verification <- c2_read(file.path(path, "usgs_verification.csv"))
  legacy <- c2_read(file.path(path, "legacy_per_time.csv"))
  c2_assert(all(is.finite(history$Y)) && !anyDuplicated(history$date), "Invalid curated training history")
  expected_history_dates <- as.character(seq.Date(as.Date(settings$historical_start),
    as.Date(max(settings$origins)), by = "day"))
  c2_assert(identical(history$date, expected_history_dates), "Curated USGS history is not complete and daily")
  c2_assert(all(is.finite(features$ensemble_mean)) && all(is.finite(features$ensemble_variance)) &&
              all(features$ensemble_variance >= 0) && all(features$n_members == 51), "Invalid curated features")
  c2_assert(!anyDuplicated(paste(features$issue_date, features$lead_day)), "Duplicate curated forecast cases")
  c2_assert(all(features$product_family == c2_family(features$issue_date, settings)) &&
    all(as.integer(as.Date(features$target_date) - as.Date(features$issue_date)) == features$lead_day),
    "Curated forecast family/date labels are inconsistent")
  c2_assert(all(legacy$score_method == settings$score_method) &&
              all(legacy$score_scale == settings$score_scale), "Frozen evaluation score contract changed")
  c2_assert(all(as.Date(legacy$forecast_date) == as.Date(legacy$cutoff_date) + legacy$lead_day),
    "Frozen score verification dates do not match leads")
  scorer <- new.env(parent = globalenv())
  sys.source(file.path(path, "current_scorer.R"), envir = scorer)
  list(history = history, features = features, verification = verification, legacy = legacy, scorer = scorer,
       sources = c2_read(file.path(path, "source_manifest.csv")))
}

c2_aggregate <- function(per_time, horizons) {
  rows <- list(); k <- 0L
  for (origin in sort(unique(per_time$cutoff_date))) for (model in sort(unique(per_time$model))) {
    selected <- per_time[per_time$cutoff_date == origin & per_time$model == model, ]
    for (h in horizons) {
      use <- selected[selected$lead_day <= h, ]
      if (nrow(use) != h) next
      c2_assert(identical(sort(as.integer(use$lead_day)), seq_len(h)), "Incomplete/duplicate score leads")
      k <- k + 1L
      rows[[k]] <- data.frame(cutoff_date = origin, model = model, horizon_days = h,
        n_valid = nrow(use), mean_crps = mean(use$crps),
        mean_climatology_crps = mean(use$climatology_crps),
        crpss = 1 - mean(use$crps) / mean(use$climatology_crps))
    }
  }
  by_origin <- do.call(rbind, rows)
  rows <- list(); k <- 0L
  for (model in sort(unique(by_origin$model))) for (h in horizons) {
    use <- by_origin[by_origin$model == model & by_origin$horizon_days == h, ]
    if (nrow(use) == 0L) next
    c2_assert(nrow(use) == length(unique(per_time$cutoff_date)), "Pooled comparison misses an origin")
    k <- k + 1L
    rows[[k]] <- data.frame(model = model, horizon_days = h, origins = nrow(use),
      n_valid = sum(use$n_valid), mean_crps = weighted.mean(use$mean_crps, use$n_valid),
      mean_climatology_crps = weighted.mean(use$mean_climatology_crps, use$n_valid),
      crpss = 1 - sum(use$mean_crps * use$n_valid) /
        sum(use$mean_climatology_crps * use$n_valid))
  }
  list(by_origin = by_origin, aggregate = do.call(rbind, rows))
}

c2_build <- function(config_path, output, input_bundle = NULL) {
  for (key in c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"))
    do.call(Sys.setenv, setNames(list("1"), key))
  for (package in c("jsonlite", "digest", "scoringRules"))
    c2_assert(requireNamespace(package, quietly = TRUE), paste("Missing package:", package))
  c2_assert(!file.exists(output), "Output directory already exists; choose a fresh directory")
  config_path <- normalizePath(config_path, mustWork = TRUE)
  config <- jsonlite::read_json(config_path, simplifyVector = TRUE)
  settings <- config$settings
  workflow <- normalizePath(file.path(dirname(config_path), config$workflow_root), mustWork = TRUE)
  article <- file.path(workflow, config$article_root)
  scorer_path <- file.path(workflow, "R/environmetrics/02_helpers_core.R")
  c2_assert(settings$evaluation_points == 2000 && settings$ensemble_variance_ddof == 1 &&
              settings$climatology_calendar_year == 2000 && settings$climatology_quantile_type == 1,
            "Unsupported representation, variance or calendar convention")
  dir.create(output, recursive = TRUE)
  file.copy(config_path, file.path(output, "configuration.json"))
  bundle <- file.path(output, "inputs")
  if (is.null(input_bundle)) {
    message("Preparing curated inputs and verifying frozen sources")
    c2_prepare_inputs(config, article, scorer_path, bundle)
  } else {
    input_bundle <- normalizePath(input_bundle, mustWork = TRUE)
    c2_load_bundle(input_bundle, settings)
    dir.create(bundle)
    c2_assert(all(file.copy(list.files(input_bundle, full.names = TRUE), bundle)), "Could not copy replay input bundle")
  }
  inputs <- c2_load_bundle(bundle, settings)
  p <- c2_probabilities(settings)
  baseline_scores <- parameters <- diagnostics <- attempts <- training <- summaries <- list()
  prediction_checks <- list()
  dir.create(file.path(output, "predictions"))
  for (i in seq_along(settings$origins)) {
    origin <- settings$origins[[i]]
    message("Fitting fixed external baselines at ", origin)
    history <- inputs$history[inputs$history$date <= origin, , drop = FALSE]
    history <- history[order(history$date), ]
    result <- c2_predict_origin(history, inputs$features, origin, settings)
    # The verification vector is deliberately constructed after prediction/fit.
    observed <- inputs$verification$Y[match(result$dates, inputs$verification$date)]
    c2_assert(all(is.finite(observed)), "Missing held-out verification outcomes")
    rows <- summary_rows <- list()
    for (model in names(result$predictions)) {
      samples <- result$predictions[[model]]
      score <- inputs$scorer$post_crps_quantile_approx(observed, samples, "comment2.external")
      rows[[model]] <- data.frame(cutoff_date = origin, model = model,
        forecast_date = result$dates, lead_day = seq_len(settings$horizon_days), crps = score$crps,
        n_samples_nominal = nrow(samples), score_method = score$method,
        tau_rule = score$tau_rule, score_scale = settings$score_scale,
        source_class = "new_external_baseline", source_path = "computed_from_curated_inputs")
      probs <- c(0.025, .05, .2, .35, .5, .65, .8, .95, .975)
      q <- t(apply(samples, 2L, stats::quantile, probs = probs, type = 1, names = FALSE))
      summary_rows[[model]] <- data.frame(cutoff_date = origin, model = model,
        forecast_date = result$dates, lead_day = seq_along(result$dates),
        observed = observed, predictive_grid_mean = colMeans(samples),
        q025 = q[,1], q05 = q[,2], q20 = q[,3], q35 = q[,4], q50 = q[,5],
        q65 = q[,6], q80 = q[,7], q95 = q[,8], q975 = q[,9])
      c2_assert(all(is.finite(samples)) && all(samples >= 0) &&
        all(apply(samples, 2L, function(x) all(diff(x) >= 0))), "Invalid baseline predictive representation")
    }
    persistence_error <- max(abs(rows$PERSISTENCE$crps - abs(observed - tail(history$Y, 1))))
    c2_assert(persistence_error < 1e-12, "Point-mass CRPS does not equal MAE")
    prediction_file <- file.path(output, "predictions", paste0(gsub("-", "", origin), ".rds"))
    saveRDS(list(probabilities = p, dates = result$dates, predictions = result$predictions),
            prediction_file, compress = "xz", version = 2)
    prediction_checks[[i]] <- data.frame(cutoff_date = origin,
      persistence_mae_max_error = persistence_error, prediction_sha256 = c2_hash(prediction_file))
    baseline_scores[[i]] <- do.call(rbind, rows)
    summaries[[i]] <- do.call(rbind, summary_rows)
    parameters[[i]] <- result$parameters; diagnostics[[i]] <- result$training_diagnostics
    attempts[[i]] <- result$attempts; training[[i]] <- result$training_pairs
  }
  new_scores <- do.call(rbind, baseline_scores)
  per_time <- rbind(inputs$legacy, new_scores)
  reference <- new_scores[new_scores$model == "CLIM-SEASONAL", ]
  key <- paste(per_time$cutoff_date, per_time$lead_day)
  refkey <- paste(reference$cutoff_date, reference$lead_day)
  per_time$climatology_crps <- reference$crps[match(key, refkey)]
  c2_assert(all(is.finite(per_time$crps)) && all(is.finite(per_time$climatology_crps)) &&
    !anyDuplicated(paste(key, per_time$model)), "Invalid or duplicate scored cases")
  per_time <- per_time[order(per_time$cutoff_date, per_time$model, per_time$lead_day), ]
  aggregate <- c2_aggregate(per_time, settings$report_horizons)
  outputs <- list(per_time = per_time, by_origin_horizon = aggregate$by_origin,
    aggregate = aggregate$aggregate, parameters = do.call(rbind, parameters),
    training_diagnostics = do.call(rbind, diagnostics), optimizer_attempts = do.call(rbind, attempts),
    prediction_checks = do.call(rbind, prediction_checks), predictive_summary = do.call(rbind, summaries))
  for (name in names(outputs)) c2_write(outputs[[name]], file.path(output, paste0(name, ".csv")))
  c2_write(do.call(rbind, training), file.path(output, "training_pairs.csv.gz"))
  c2_assert(identical(inputs$legacy$crps, per_time$crps[match(
    paste(inputs$legacy$cutoff_date, inputs$legacy$model, inputs$legacy$lead_day),
    paste(per_time$cutoff_date, per_time$model, per_time$lead_day))]), "Existing scores changed")
  if (is.null(input_bundle)) c2_source_check(inputs$sources)
  manifest <- list(schema_version = 1, configuration_sha256 = c2_hash(config_path),
    builder_sha256 = c2_hash(file.path(workflow, "scripts/build_comment2_external_baselines.R")),
    build_mode = if (is.null(input_bundle)) "audited_raw_sources" else "curated_input_replay",
    settings = settings, score_contract = list(
      evaluation = "Unchanged current post_crps_quantile_approx; sorted grid with tau=k/(2001)",
      training = "Analytic truncated-normal CRPS, averaged across pre-origin mature forecast pairs",
      predictive_grid = "2000 deterministic quantiles p=k/2001; climatology type-1 empirical quantiles; persistence repeats last observation",
      skill = "1 - sum(model scores)/sum(matched seasonal climatology scores); no daily-ratio average",
      calendar = "Circular 366-slot reference year 2000; February 29 retained as its own slot; +/-15 slots"),
    training_isolation = "Each fit receives only USGS dates <=T, issues<T, matured targets<=T, current product family; verification is matched only after prediction",
    optimizer = list(method = "L-BFGS-B", starts = 4, selection = "lowest analytic training CRPS among converged starts", variance = "unbiased within-ensemble sample variance of log1p members (ddof=1)",
      parameters = "mu=a+b*m; sigma2=exp(log_c)+d*v; monotone b>=0, d>=0; numeric safety bounds audited",
      gradient = "Projected gradient infinity norm in scaled optimizer coordinates; raw norm also retained"),
    r_version = R.version.string, packages = setNames(lapply(c("jsonlite", "digest", "scoringRules"),
      function(x) as.character(utils::packageVersion(x))), c("jsonlite", "digest", "scoringRules")),
    rows = vapply(outputs, nrow, integer(1)),
    input_bundle_sha256 = c2_hash(file.path(bundle, "bundle_checksums.csv")),
    external_raw_sources_required_for_replay = FALSE,
    existing_publication_scores_unchanged = TRUE)
  c2_json(manifest, file.path(output, "run_manifest.json"))
  c2_json(list(passed = TRUE, existing_scores_imported_verbatim = nrow(inputs$legacy),
    baseline_scores = nrow(new_scores), origins = length(settings$origins),
    predictions_finite_nonnegative_nondecreasing = TRUE,
    persistence_point_mass_equals_mae = TRUE, all_emos_fits_converged = TRUE,
    original_source_hashes_unchanged = if (is.null(input_bundle)) TRUE else NULL),
    file.path(output, "verification.json"))
  files <- list.files(output, recursive = TRUE, full.names = TRUE)
  files <- files[!dir.exists(files)]
  index <- data.frame(file = substring(files, nchar(output) + 2L),
    sha256 = vapply(files, c2_hash, character(1)), bytes = file.info(files)$size)
  c2_write(index, file.path(output, "SHA256SUMS.csv"))
  message("Completed baseline bundle: ", output)
  invisible(outputs)
}

c2_main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  script_arg <- grep("^--file=", commandArgs(), value = TRUE)
  script <- normalizePath(sub("^--file=", "", script_arg[[1L]]), mustWork = TRUE)
  workflow <- dirname(dirname(script))
  config <- file.path(workflow, "config/comment2_external_baselines.json")
  output <- bundle <- NULL
  while (length(args)) {
    c2_assert(length(args) >= 2L, "Expected --config PATH, --output-root PATH or --input-bundle PATH")
    if (args[[1L]] == "--config") config <- args[[2L]] else
    if (args[[1L]] == "--output-root") output <- args[[2L]] else
    if (args[[1L]] == "--input-bundle") bundle <- args[[2L]] else stop("Unknown option: ", args[[1L]])
    args <- args[-c(1L, 2L)]
  }
  c2_assert(!is.null(output), "--output-root is required")
  c2_build(config, normalizePath(output, mustWork = FALSE), bundle)
}
if (sys.nframe() == 0L) c2_main()
