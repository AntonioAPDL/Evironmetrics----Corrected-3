#!/usr/bin/env Rscript
# Deterministic diagnostics from frozen, already computed forecast values.
# Freeze once: --freeze-from PROJECT --source-article ARTICLE --output-dir NEW
# Replay: --inputs-manifest BUNDLE/inputs/manifest.json --output-dir NEW
main_args <- commandArgs(trailingOnly = TRUE)
script_arg <- grep("^--file=", commandArgs(), value = TRUE)
if (length(script_arg) != 1L) stop("Run with Rscript --vanilla.")
script_file <- normalizePath(sub("^--file=", "", script_arg), mustWork = TRUE)
code_root <- dirname(dirname(script_file))
helper_file <- file.path(code_root, "R/environmetrics/no_refit_review_helpers.R")
config_file <- file.path(code_root, "config/no_refit_review_diagnostics.json")
Sys.setenv(OPENBLAS_NUM_THREADS = "1", OMP_NUM_THREADS = "1", MKL_NUM_THREADS = "1", VECLIB_MAXIMUM_THREADS = "1")
for (p in c("jsonlite", "digest", "ggplot2")) if (!requireNamespace(p, quietly = TRUE)) stop(paste("Required installed package:", p))
if (requireNamespace("RhpcBLASctl", quietly = TRUE)) {
  RhpcBLASctl::blas_set_num_threads(1L); RhpcBLASctl::omp_set_num_threads(1L)
}
source(helper_file)
config <- jsonlite::fromJSON(config_file, simplifyVector = TRUE)
executed_hashes <- c(builder = nrf_hash(script_file), helpers = nrf_hash(helper_file), config = nrf_hash(config_file))
started <- proc.time()
nrf_assert(length(main_args) > 0L && length(main_args) %% 2L == 0L, "Supply named CLI pairs")
keys <- main_args[seq.int(1L, length(main_args), by = 2L)]
nrf_assert(all(keys %in% c("--freeze-from", "--source-article", "--inputs-manifest", "--output-dir")) && !anyDuplicated(keys), "Unknown or duplicate argument")
opts <- setNames(main_args[seq.int(2L, length(main_args), by = 2L)], keys)
nrf_assert("--output-dir" %in% keys && xor("--freeze-from" %in% keys, "--inputs-manifest" %in% keys), "Select exactly one freeze or replay mode")
output <- opts[["--output-dir"]]
nrf_assert(!file.exists(output) && dir.exists(dirname(output)), "Output must be a fresh directory with an existing parent")
nrf_assert(dir.create(output), "Cannot create output directory")
output <- normalizePath(output)
for (d in c("results", "verification", "reproduce/scripts", "reproduce/R/environmetrics", "reproduce/config")) dir.create(file.path(output, d), recursive = TRUE)
for (pair in list(c(script_file, "reproduce/scripts/build_no_refit_review_diagnostics.R"),
                  c(helper_file, "reproduce/R/environmetrics/no_refit_review_helpers.R"),
                  c(config_file, "reproduce/config/no_refit_review_diagnostics.json"))) {
  nrf_assert(file.copy(pair[[1L]], file.path(output, pair[[2L]]), overwrite = FALSE, copy.mode = FALSE), "Could not archive executed source")
}

freeze_inputs <- function(project, article, output) {
  dir.create(file.path(output, "inputs"))
  files <- list()
  record <- function(path, rel, role, original = path, derived = FALSE) {
    files[[length(files) + 1L]] <<- list(input_snapshot_relpath = rel, role = role,
      original_source_path = as.character(original), sha256 = nrf_hash(path), bytes = unname(file.info(path)$size), derived = derived)
  }
  copy_input <- function(source, rel, role, expected_sha = NULL) {
    before <- nrf_hash(source)
    if (!is.null(expected_sha)) nrf_assert(identical(before, expected_sha), paste("Authority mismatch", role))
    destination <- file.path(output, rel)
    dir.create(dirname(destination), recursive = TRUE, showWarnings = FALSE)
    nrf_assert(file.copy(source, destination, overwrite = FALSE, copy.mode = FALSE), paste("Copy failed", rel))
    nrf_assert(identical(before, nrf_hash(destination)) && identical(before, nrf_hash(source)), paste("Input changed during copy", role))
    record(destination, rel, role, normalizePath(source))
    before
  }
  authority_path <- file.path(project, config$authority_inventory)
  authority <- jsonlite::fromJSON(authority_path, simplifyVector = FALSE)
  publication_path <- file.path(article, config$publication_manifest)
  nrf_assert(identical(nrf_hash(publication_path), authority$publication_manifest_sha256), "Publication authority changed")
  publication <- nrf_read_csv(publication_path)
  nrf_assert(nrow(publication) == 45L && length(authority$rows) == 45L, "Expected 45 selected fits")
  truth_sha <- copy_input(file.path(article, config$verification_observations), "inputs/usgs_verification.csv", "verification_observations", authority$verification_sha256)
  copy_input(file.path(article, config$legacy_scores), "inputs/legacy_scores.csv", "all_existing_daily_scores")
  copy_input(file.path(article, config$existing_quantiles), "inputs/existing_HE4_quantiles.csv", "existing_target_quantiles")
  copy_input(authority_path, "inputs/original_cache_authority.json", "original_cache_inventory")
  external_checks <- nrf_read_csv(file.path(article, "artifacts/comment2_revision/external_baselines/SHA256SUMS.csv"))
  nrf_assert(identical(nrf_hash(file.path(output, "inputs/legacy_scores.csv")), external_checks$sha256[external_checks$file == "per_time.csv"]), "Original score checksum differs from its published bundle")
  reps <- list()
  append_rep <- function(model, origin, path, rel, run, reader, object = "", sha = nrf_hash(path)) {
    policy <- nrf_representation_policy(model)
    reps[[length(reps) + 1L]] <<- data.frame(representation_id = paste0(gsub("-", "", origin), "__", model),
      model_id = model, origin_date = origin, source_run_id = run,
      original_source_path = normalizePath(path), input_snapshot_relpath = rel, source_sha256 = sha,
      representation_kind = policy$kind, source_scale = if (reader == "raw_csv") "discharge_cms" else "log1p_cms",
      available_leads = policy$leads, n_values_nominal = policy$n, n_random_draws = policy$random,
      grid_probability_rule = if (policy$kind == "deterministic_quantile_grid") "k/2001; k=1,...,2000" else "not_applicable",
      equal_weight_definition = "all_stored_values_with_multiplicity", reader_kind = reader, object_key = object,
      generator_evidence_id = if (reader == "matrix_rds") "recorded_model_marginal_generator" else if (reader == "raw_csv") "frozen_raw_product_adapter" else "frozen_external_inverse_cdf_grid",
      adjustment_status = policy$status, stringsAsFactors = FALSE)
  }
  for (entry in authority$rows) {
    p <- publication[as.character(publication$cutoff) == entry$cutoff & publication$manuscript_label == entry$model, , drop = FALSE]
    nrf_assert(nrow(p) == 1L, "Publication/inventory identity mismatch")
    root <- if (nzchar(p$artifact_run_root)) p$artifact_run_root else p$run_root
    nrf_assert(startsWith(entry$prediction_file, paste0(root, "/post/cache/")), "Prediction is outside selected cache")
    origin <- as.character(as.Date(entry$cutoff, "%Y%m%d"))
    rel <- paste0("inputs/predictions/", entry$cutoff, "__", entry$model, ".rds")
    sha <- copy_input(entry$prediction_file, rel, "selected_model_prediction", entry$prediction_sha256)
    append_rep(entry$model, origin, entry$prediction_file, rel, p$run_id, "matrix_rds", sha = sha)
  }
  for (origin in config$origins) {
    cutoff <- gsub("-", "", origin)
    selected <- publication[as.character(publication$cutoff) == cutoff & publication$manuscript_label == "exAL-M-T1", , drop = FALSE]
    root <- if (nzchar(selected$artifact_run_root)) selected$artifact_run_root else selected$run_root
    for (product in c("glofas", "nws")) {
      path <- file.path(root, "inputs/shared/forecasts", paste0(product, "_forecast.csv"))
      rel <- paste0("inputs/raw/", cutoff, "__", product, ".csv")
      sha <- copy_input(path, rel, "raw_product_members")
      append_rep(if (product == "glofas") "RAW-GLOFAS" else "RAW-NWS", origin, path, rel, selected$run_id, "raw_csv", sha = sha)
    }
    path <- file.path(article, config$external_prediction_directory, paste0(cutoff, ".rds"))
    rel <- paste0("inputs/external/", cutoff, ".rds")
    expected <- external_checks$sha256[external_checks$file == paste0("predictions/", cutoff, ".rds")]
    nrf_assert(length(expected) == 1L, "External prediction checksum missing")
    sha <- copy_input(path, rel, "existing_external_predictions", expected)
    for (model in c("CLIM-SEASONAL", "PERSISTENCE", "EMOS-GLOFAS")) append_rep(model, origin, path, rel, "comment2_frozen_external_reference", "external_list_rds", model, sha)
    path <- file.path(article, "artifacts/five_cutoff_main_model_synthesis", paste0(cutoff, "_exal_m_t1"), "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv")
    copy_input(path, paste0("inputs/figure_quantiles/", cutoff, ".csv"), "selected_figure_quantile_export")
  }
  representations <- nrf_bind(reps)
  representations <- representations[order(representations$origin_date, match(representations$model_id, config$methods)), ]
  nrf_unique(representations, "representation_id", "representation registry")
  nrf_write_csv(representations, file.path(output, "inputs/representations.csv"))
  record(file.path(output, "inputs/representations.csv"), "inputs/representations.csv", "derived_representation_registry", "derived_from_selected_authority", TRUE)
  # Archive only the two original pure scoring functions, rather than executing
  # a model module or copying unrelated application settings into this bundle.
  definitions <- list()
  scorer_source <- file.path(project, "R/environmetrics/02_helpers_core.R")
  for (expression in parse(scorer_source)) if (is.call(expression) && identical(expression[[1L]], as.name("<-")) &&
      is.symbol(expression[[2L]]) && as.character(expression[[2L]]) %in% c("check_loss_fn", "post_crps_quantile_approx")) definitions[[length(definitions) + 1L]] <- expression
  nrf_assert(length(definitions) == 2L, "Original scorer definitions missing")
  scorer_rel <- "inputs/original_score_functions.R"
  writeLines(unlist(lapply(definitions, function(z) deparse(z, width.cutoff = 100L))), file.path(output, scorer_rel))
  record(file.path(output, scorer_rel), scorer_rel, "extracted_original_pure_score_functions", normalizePath(scorer_source), TRUE)
  generator_paths <- c("R/environmetrics/02_helpers_core.R", "R/environmetrics/40_figures_ndlm_only.R",
    "R/unified/families/ndlm_main/08_vb_cavi_exact.R", "R/unified/families/ndlm_univar/03_filter_forecast_fit.R")
  generator_evidence <- list(workflow_source_commit = config$authority_workflow_commit,
    scope = "recorded generator source basis; sampled forecast matrices themselves are immutable authority",
    files = lapply(generator_paths, function(rel) list(path = rel, sha256 = nrf_hash(file.path(project, rel)))))
  generator_rel <- "inputs/generator_evidence.json"
  jsonlite::write_json(generator_evidence, file.path(output, generator_rel), pretty = TRUE, auto_unbox = TRUE)
  record(file.path(output, generator_rel), generator_rel, "generator_source_evidence", "selected_source_basis", TRUE)
  for (rel in c("reproduce/scripts/build_no_refit_review_diagnostics.R", "reproduce/R/environmetrics/no_refit_review_helpers.R", "reproduce/config/no_refit_review_diagnostics.json")) record(file.path(output, rel), rel, "executed_source_snapshot")
  manifest <- list(schema_version = 1L, article_commit = config$authority_article_commit, workflow_commit = config$authority_workflow_commit,
    selected_publication_manifest_sha256 = authority$publication_manifest_sha256, original_scorer_source_sha256 = nrf_hash(scorer_source),
    verification_sha256 = truth_sha, representations = "inputs/representations.csv", observations = "inputs/usgs_verification.csv",
    legacy_scores = "inputs/legacy_scores.csv", existing_quantiles = "inputs/existing_HE4_quantiles.csv", original_score_functions = scorer_rel,
    files = files, no_model_fits = TRUE, no_forecast_regeneration = TRUE)
  manifest_path <- file.path(output, "inputs/manifest.json")
  jsonlite::write_json(manifest, manifest_path, pretty = TRUE, auto_unbox = TRUE, digits = 17L)
  nrf_assert(all(Sys.chmod(c(manifest_path, vapply(files, function(z) file.path(output, z$input_snapshot_relpath), character(1))), mode = "0444")), "Could not make frozen snapshot files read-only")
  manifest_path
}

if ("--freeze-from" %in% keys) {
  project <- normalizePath(opts[["--freeze-from"]], mustWork = TRUE)
  article <- if ("--source-article" %in% keys) normalizePath(opts[["--source-article"]], mustWork = TRUE) else file.path(project, config$article_directory)
  input_manifest <- freeze_inputs(project, article, output)
} else input_manifest <- normalizePath(opts[["--inputs-manifest"]], mustWork = TRUE)
verified <- nrf_verify_inputs(input_manifest)
bundle_root <- verified$root
manifest <- verified$manifest
input_manifest_hash <- nrf_hash(input_manifest)
for (name in names(executed_hashes)) {
  ending <- switch(name, builder = "scripts/build_no_refit_review_diagnostics.R", helpers = "R/environmetrics/no_refit_review_helpers.R", config = "config/no_refit_review_diagnostics.json")
  archived <- nrf_safe_relative_path(bundle_root, paste0("reproduce/", ending))
  nrf_assert(identical(executed_hashes[[name]], nrf_hash(archived)), paste("Executing source differs from frozen input", name))
}
representations <- nrf_read_csv(nrf_safe_relative_path(bundle_root, manifest$representations))
truth <- nrf_read_csv(nrf_safe_relative_path(bundle_root, manifest$observations))
old <- nrf_read_csv(nrf_safe_relative_path(bundle_root, manifest$legacy_scores))
he4 <- nrf_read_csv(nrf_safe_relative_path(bundle_root, manifest$existing_quantiles))
old_key <- paste(old$cutoff_date, old$model, old$lead_day)
nrf_assert(nrow(old) == 1860L && !anyDuplicated(old_key), "Unexpected original-score registry")
old_env <- new.env(parent = baseenv())
sys.source(nrf_safe_relative_path(bundle_root, manifest$original_score_functions), envir = old_env)
observation_rows <- lapply(config$origins, function(origin) {
  dates <- as.character(as.Date(origin) + seq_len(28L)); index <- match(dates, truth$date)
  nrf_assert(!anyNA(index), "Missing frozen verification date")
  data.frame(observation_case_id = paste0(gsub("-", "", origin), "_", sprintf("%02d", seq_len(28L))),
    site_id = config$site_id, origin_date = origin, lead_day = seq_len(28L), target_date = dates,
    observed_log1p_cms = truth$Y[index], observed_discharge_cms = truth$discharge_cms[index],
    truth_source_sha256 = manifest$verification_sha256, stringsAsFactors = FALSE)
})
observations <- nrf_bind(observation_rows)
nrf_assert(nrf_close(nrf_inverse(observations$observed_log1p_cms), observations$observed_discharge_cms), "Observation scales disagree")
case_rows <- score_rows <- quantile_rows <- interval_rows <- source_rows <- support_rows <- parity_rows <- list()
figure_error <- 0; original_helper_error <- 0; row_counter <- 0L
for (i in seq_len(nrow(representations))) {
  rep <- representations[i, ]; model <- rep$model_id; origin <- rep$origin_date
  policy <- nrf_representation_policy(model)
  obs <- observations[observations$origin_date == origin & observations$lead_day <= rep$available_leads, ]
  values <- nrf_load_representation(rep, bundle_root, obs$target_date)
  cases <- data.frame(representation_id = rep$representation_id, model_id = model, origin_date = origin,
    observation_case_id = obs$observation_case_id, lead_day = obs$lead_day, target_date = obs$target_date,
    n_values_nominal = nrow(values), n_values_finite = colSums(is.finite(values)), availability_status = "AVAILABLE", stringsAsFactors = FALSE)
  case_rows[[i]] <- cases
  q_log <- t(apply(values, 2L, stats::quantile, probs = config$target_probabilities, type = policy$qtype, names = FALSE))
  matrix_q_log <- q_log
  q_definition <- if (policy$qtype == 1L) "empirical_inverse_type1" else "new_sample_quantiles_type8"
  q_source <- "saved_prediction_matrix"
  if (model %in% config$existing_quantile_methods) {
    selected <- he4[as.character(he4$cutoff) == gsub("-", "", origin) & he4$manuscript_label == model, ]
    nrf_assert(nrow(selected) == 196L, "Missing original HE4 quantiles")
    for (k in seq_along(config$target_probabilities)) {
      d <- selected[selected$tau == config$target_probabilities[[k]], ]; idx <- match(obs$target_date, d$forecast_date)
      nrf_assert(!anyNA(idx) && nrf_close(d$observed[idx], obs$observed_log1p_cms), "HE4 target/date mismatch")
      q_log[, k] <- d$predicted_quantile[idx]
    }
    q_definition <- "frozen_HE4_target_quantile"; q_source <- "existing_HE4_export"
  }
  interval_log <- t(apply(values, 2L, stats::quantile, probs = c(.025, .975), type = policy$qtype, names = FALSE))
  interval_definition <- if (policy$qtype == 1L) "empirical_inverse_type1_95" else "sample_type8_95"
  if (model == "exAL-M-T1") {
    exported <- nrf_read_csv(nrf_safe_relative_path(bundle_root, paste0("inputs/figure_quantiles/", gsub("-", "", origin), ".csv")))
    exported <- exported[exported$segment == "forecast", ]
    nrf_assert(identical(exported$date, obs$target_date), "Figure quantile date mismatch")
    figure_error <- max(figure_error, max(abs(matrix_q_log - as.matrix(exported[, c("q05", "q20", "q35", "q50", "q65", "q80", "q95")]))), max(abs(matrix_q_log - q_log)))
    nrf_assert(figure_error <= config$tolerance$quantile_parity_absolute, "Selected figure quantiles differ")
  }
  replay_old <- old_env$post_crps_quantile_approx(obs$observed_log1p_cms, values)$crps
  match_old <- match(paste(origin, model, obs$lead_day), old_key)
  nrf_assert(!anyNA(match_old), "Original scored case missing")
  original_helper_error <- max(original_helper_error, max(abs(replay_old - old$crps[match_old])))
  nrf_assert(original_helper_error <= config$tolerance$legacy_absolute, "Original scorer parity failed")
  support_rows[[i]] <- data.frame(representation_id = rep$representation_id, model_id = model, origin_date = origin,
    n_values_total = length(values), negative_log_values = sum(values < 0), minimum_log_value = min(values), maximum_log_value = max(values),
    nonfinite_values = sum(!is.finite(values)), overflow_risk_values = sum(values >= log(.Machine$double.xmax)), stringsAsFactors = FALSE)
  for (scale in config$scales) {
    raw_scale <- scale == "discharge_cms"
    mat <- if (raw_scale) nrf_inverse(values) else values
    y <- if (raw_scale) obs$observed_discharge_cms else obs$observed_log1p_cms
    q <- if (raw_scale) nrf_inverse(q_log) else q_log
    intervals <- if (raw_scale) nrf_inverse(interval_log) else interval_log
    qdef <- if (raw_scale) paste0("inverse_of_", q_definition) else q_definition
    idef <- if (raw_scale) paste0("inverse_of_log_", interval_definition) else interval_definition
    sc <- lapply(seq_len(ncol(mat)), function(j) nrf_sorted_scores(mat[, j], y[[j]], nrf_adjustable(rep$adjustment_status)))
    scores <- data.frame(cases, score_scale = scale,
      original_grid_formula_score = vapply(sc, `[[`, numeric(1), "legacy"),
      is_original_published_score = !raw_scale,
      exact_ecdf_crps = vapply(sc, `[[`, numeric(1), "ecdf"),
      iid_adjusted_crps = vapply(sc, `[[`, numeric(1), "adjusted"), adjustment_status = rep$adjustment_status,
      median_absolute_error = abs(y - q[, 4L]), predictive_mean = colMeans(mat),
      observed = y, source_id = rep$representation_id, representation_kind = rep$representation_kind,
      median_definition = qdef, stringsAsFactors = FALSE)
    score_rows[[length(score_rows) + 1L]] <- scores
    if (!raw_scale) {
      err <- abs(scores$original_grid_formula_score - old$crps[match_old])
      nrf_assert(all(err <= config$tolerance$legacy_absolute), "Legacy sorted-score parity failed")
      parity_rows[[i]] <- data.frame(cases[, c("representation_id", "model_id", "origin_date", "lead_day", "target_date")],
        original_score = old$crps[match_old], replay_score = scores$original_grid_formula_score, absolute_error = err,
        original_helper_error = abs(replay_old - old$crps[match_old]), stringsAsFactors = FALSE)
    }
    for (k in seq_along(config$target_probabilities)) {
      events <- nrf_quantile_events(obs$observed_log1p_cms, q_log[, k])
      # Original-scale indicator labels deliberately use the unchanged log event.
      loss <- (y - q[, k]) * (config$target_probabilities[[k]] - as.numeric(y < q[, k]))
      quantile_rows[[length(quantile_rows) + 1L]] <- data.frame(cases, score_scale = scale,
        tau = config$target_probabilities[[k]], quantile_value = q[, k], quantile_definition = qdef,
        quantile_source = q_source, events, check_loss = loss, event_scale = "log1p_cms", stringsAsFactors = FALSE)
    }
    ie <- nrf_interval_events(y, intervals[, 1L], intervals[, 2L])
    log_events <- nrf_interval_events(obs$observed_log1p_cms, interval_log[, 1L], interval_log[, 2L])
    ie[, c("lower_miss", "inside", "upper_miss")] <- log_events[, c("lower_miss", "inside", "upper_miss")]
    interval_rows[[length(interval_rows) + 1L]] <- data.frame(cases, score_scale = scale,
      nominal_coverage = .95, lower_probability = .025, upper_probability = .975,
      lower = intervals[, 1L], upper = intervals[, 2L], interval_definition = idef, ie, event_scale = "log1p_cms", stringsAsFactors = FALSE)
    if (rep$representation_kind == "physical_ensemble") {
      mean_value <- colMeans(mat); med <- apply(mat, 2L, stats::quantile, probs = .5, type = 1L, names = FALSE)
      source_rows[[length(source_rows) + 1L]] <- data.frame(source_id = model, origin_date = origin,
        lead_day = obs$lead_day, target_date = obs$target_date, score_scale = scale, n_members = nrow(mat),
        observed = y, ensemble_mean = mean_value, ensemble_median = med, ensemble_sd = apply(mat, 2L, stats::sd),
        mean_error = mean_value - y, absolute_mean_error = abs(mean_value - y),
        mean_member_absolute_error = colMeans(abs(sweep(mat, 2L, y, `-`))), stringsAsFactors = FALSE)
    }
  }
}
forecast_cases <- nrf_bind(case_rows); scores_per_case <- nrf_bind(score_rows)
quantiles_per_case <- nrf_bind(quantile_rows); intervals_per_case <- nrf_bind(interval_rows)
source_lead_diagnostics <- nrf_bind(source_rows)

summarize_scores <- function(x, horizon, pool = FALSE) {
  d <- x[x$lead_day <= horizon & if (horizon == 28L) x$model_id != "RAW-NWS" else TRUE, ]
  keys <- c("model_id", if (!pool) "origin_date", "score_scale")
  out <- nrf_groups(d, keys, function(z) data.frame(horizon_days = horizon,
    n_expected_cases = horizon * if (pool) 5L else 1L, n_valid_cases = nrow(z),
    mean_original_grid_score = mean(z$original_grid_formula_score), mean_exact_ecdf_crps = mean(z$exact_ecdf_crps),
    mean_iid_adjusted_crps = if (all(is.na(z$iid_adjusted_crps))) NA_real_ else mean(z$iid_adjusted_crps),
    adjustment_status = z$adjustment_status[[1L]], representation_kind = z$representation_kind[[1L]],
    mean_median_absolute_error = mean(z$median_absolute_error), stringsAsFactors = FALSE))
  if (pool) out$origin_or_pool <- "POOL"
  baseline <- out[out$model_id == "CLIM-SEASONAL", ]
  match_keys <- c(if (!pool) "origin_date", "score_scale")
  ref <- baseline$mean_exact_ecdf_crps[match(nrf_key(out, match_keys), nrf_key(baseline, match_keys))]
  nrf_assert(all(is.finite(ref)) && all(ref > 0) && all(out$n_valid_cases == out$n_expected_cases), "Invalid score reference/case count")
  out$mean_climatology_exact_ecdf_crps <- ref
  out$ecdf_crpss <- 1 - out$mean_exact_ecdf_crps / ref
  out$comparison_case_set_id <- nrf_case_set(if (pool) "POOL" else out$origin_date, horizon)
  out$climatology_representation_id <- if (pool) "CLIM-SEASONAL__five_frozen_grids" else paste0(gsub("-", "", out$origin_date), "__CLIM-SEASONAL")
  out
}
summary_by_origin_horizon <- nrf_bind(lapply(config$horizons, function(h) summarize_scores(scores_per_case, h)))
summary_pooled <- nrf_bind(lapply(config$horizons, function(h) summarize_scores(scores_per_case, h, TRUE)))

summarize_calibration <- function(x, horizon, pool = FALSE) {
  d <- x[x$lead_day <= horizon & if (horizon == 28L) x$model_id != "RAW-NWS" else TRUE, ]
  d$origin_or_pool <- if (pool) "POOL" else d$origin_date
  nrf_groups(d, c("model_id", "origin_or_pool", "score_scale", "tau", "quantile_definition"), function(z) data.frame(
    horizon_days = horizon, n_expected = horizon * if (pool) 5L else 1L, n_valid = nrow(z),
    n_strict = sum(z$hit_strict), n_weak = sum(z$hit_weak), n_tie = sum(z$is_exact_tie),
    rate_strict = mean(z$hit_strict), rate_weak = mean(z$hit_weak), nominal_tau = z$tau[[1L]],
    mean_check_loss = mean(z$check_loss), case_set_id = nrf_case_set(z$origin_or_pool[[1L]], horizon), stringsAsFactors = FALSE))
}
calibration_summary <- nrf_bind(lapply(config$horizons, function(h) nrf_bind(list(summarize_calibration(quantiles_per_case, h), summarize_calibration(quantiles_per_case, h, TRUE)))))
summarize_intervals <- function(x, horizon, pool = FALSE) {
  d <- x[x$lead_day <= horizon & if (horizon == 28L) x$model_id != "RAW-NWS" else TRUE, ]
  d$origin_or_pool <- if (pool) "POOL" else d$origin_date
  nrf_groups(d, c("model_id", "origin_or_pool", "score_scale", "interval_definition"), function(z) data.frame(
    horizon_days = horizon, n_expected = horizon * if (pool) 5L else 1L, n_valid = nrow(z),
    n_lower_miss = sum(z$lower_miss), n_inside = sum(z$inside), n_upper_miss = sum(z$upper_miss),
    empirical_coverage = mean(z$inside), mean_width = mean(z$width), mean_interval_score = mean(z$interval_score),
    case_set_id = nrf_case_set(z$origin_or_pool[[1L]], horizon), stringsAsFactors = FALSE))
}
interval_summary <- nrf_bind(lapply(config$horizons, function(h) nrf_bind(list(summarize_intervals(intervals_per_case, h), summarize_intervals(intervals_per_case, h, TRUE)))))
source_lead_summary <- nrf_groups(source_lead_diagnostics, c("source_id", "lead_day", "score_scale"), function(z) data.frame(
  n_origins = nrow(z), mean_error = mean(z$mean_error), mean_absolute_error = mean(z$absolute_mean_error), mean_ensemble_sd = mean(z$ensemble_sd)))

tables <- list(observations = observations, representations = representations, forecast_cases = forecast_cases,
  scores_per_case = scores_per_case, quantiles_per_case = quantiles_per_case, intervals_per_case = intervals_per_case,
  summary_by_origin_horizon = summary_by_origin_horizon, summary_pooled = summary_pooled,
  calibration_summary = calibration_summary, interval_summary = interval_summary,
  source_lead_diagnostics = source_lead_diagnostics, source_lead_summary = source_lead_summary,
  support_audit = nrf_bind(support_rows), legacy_parity = nrf_bind(parity_rows))
for (name in names(config$expected_rows)) nrf_assert(nrow(tables[[name]]) == config$expected_rows[[name]], paste("Unexpected row count", name))
nrf_assert(all(calibration_summary$n_weak == calibration_summary$n_strict + calibration_summary$n_tie) && all(calibration_summary$n_expected == calibration_summary$n_valid), "Calibration count identity failed")
nrf_assert(all(interval_summary$n_lower_miss + interval_summary$n_inside + interval_summary$n_upper_miss == interval_summary$n_valid) && all(interval_summary$n_expected == interval_summary$n_valid), "Interval partition failed")
nrf_unique(observations, c("site_id", "origin_date", "lead_day")); nrf_unique(forecast_cases, c("representation_id", "observation_case_id"))
nrf_unique(scores_per_case, c("representation_id", "observation_case_id", "score_scale"))
nrf_unique(quantiles_per_case, c("representation_id", "observation_case_id", "score_scale", "tau", "quantile_definition"))
nrf_unique(intervals_per_case, c("representation_id", "observation_case_id", "score_scale", "interval_definition"))
for (name in names(tables)) nrf_write_csv(tables[[name]], file.path(output, "results", paste0(name, ".csv")))

plot_data <- calibration_summary[calibration_summary$origin_or_pool == "POOL" & calibration_summary$score_scale == "log1p_cms" & calibration_summary$model_id %in% config$plot_methods, ]
plot_data$model_id <- factor(plot_data$model_id, levels = config$plot_methods)
plot_data$horizon <- factor(plot_data$horizon_days, levels = c(8, 28), labels = c("Eight days (40 verification dates)", "28 days (140 verification dates)"))
colors <- c("exAL-M-T1" = "#222222", "RAW-GLOFAS" = "#0072B2", "RAW-NWS" = "#D55E00", "EMOS-GLOFAS" = "#009E73", "CLIM-SEASONAL" = "#CC79A7")
styles <- c("exAL-M-T1" = "solid", "RAW-GLOFAS" = "dashed", "RAW-NWS" = "dotdash", "EMOS-GLOFAS" = "longdash", "CLIM-SEASONAL" = "dotted")
plot <- ggplot2::ggplot(plot_data, ggplot2::aes(x = tau, y = rate_weak, color = model_id, linetype = model_id, shape = model_id, group = model_id)) +
  ggplot2::geom_abline(slope = 1, intercept = 0, color = "grey60", linewidth = .5) +
  ggplot2::geom_line(linewidth = .7) + ggplot2::geom_point(size = 1.9) +
  ggplot2::facet_wrap(~horizon, nrow = 1) + ggplot2::scale_color_manual(values = colors) + ggplot2::scale_linetype_manual(values = styles) +
  ggplot2::scale_shape_manual(values = c(16, 17, 15, 18, 4)) +
  ggplot2::scale_x_continuous(breaks = c(.05, .2, .35, .5, .65, .8, .95), limits = c(0, 1)) +
  ggplot2::scale_y_continuous(breaks = seq(0, 1, .2), limits = c(0, 1)) +
  ggplot2::coord_fixed() + ggplot2::labs(x = "Nominal quantile probability", y = "Observed proportion at or below forecast quantile", color = NULL, linetype = NULL, shape = NULL) +
  ggplot2::theme_bw(base_size = 10) + ggplot2::theme(legend.position = "bottom", legend.text = ggplot2::element_text(size = 9),
    panel.grid.minor = ggplot2::element_blank(), strip.background = ggplot2::element_rect(fill = "grey95"), axis.text.x = ggplot2::element_text(size = 8)) +
  ggplot2::guides(color = ggplot2::guide_legend(nrow = 2, byrow = TRUE), linetype = ggplot2::guide_legend(nrow = 2, byrow = TRUE), shape = ggplot2::guide_legend(nrow = 2, byrow = TRUE))
ggplot2::ggsave(file.path(output, "results/no_refit_quantile_reliability.png"), plot, width = 7.4, height = 4.8, units = "in", dpi = 300, bg = "white")

invisible(nrf_verify_inputs(input_manifest))
nrf_assert(identical(input_manifest_hash, nrf_hash(input_manifest)), "Input manifest changed")
nrf_assert(identical(executed_hashes, c(builder = nrf_hash(script_file), helpers = nrf_hash(helper_file), config = nrf_hash(config_file))), "Executing source changed during derivation")
verification <- list(schema_version = 1L, status = "VALIDATED", input_manifest_sha256 = input_manifest_hash,
  executed_source_sha256 = as.list(executed_hashes), source_hashes_verified_after = TRUE,
  no_model_fits = TRUE, no_baseline_training = TRUE, no_random_generation = TRUE, workers = 1L, library_threads = 1L,
  row_counts = lapply(tables, nrow), original_helper_max_absolute_error = original_helper_error,
  selected_figure_quantile_max_absolute_error = figure_error,
  original_score_max_absolute_error = max(tables$legacy_parity$absolute_error),
  primary_score = config$policies$primary_score, qualified_sensitivity = config$policies$sensitivity,
  adjusted_skill_reported = FALSE, event_definition = "strict/weak exact ties; closed interval; inverse-scale events inherited from log limits",
  packages = lapply(c("jsonlite", "digest", "ggplot2"), function(p) list(name = p, version = as.character(utils::packageVersion(p)))),
  R_version = as.character(getRversion()), elapsed_seconds = unname((proc.time() - started)[["elapsed"]]))
jsonlite::write_json(verification, file.path(output, "verification/verification.json"), pretty = TRUE, auto_unbox = TRUE, digits = 17L)
writeLines(capture.output(utils::sessionInfo()), file.path(output, "verification/session_info.txt"))
all_files <- sort(list.files(output, recursive = TRUE, full.names = TRUE))
all_files <- all_files[!dir.exists(all_files)]
checksums <- data.frame(path = substring(all_files, nchar(output) + 2L), sha256 = vapply(all_files, nrf_hash, character(1)),
                        bytes = unname(file.info(all_files)$size), stringsAsFactors = FALSE)
nrf_write_csv(checksums, file.path(output, "verification/checksums.csv"))
cat(sprintf("Validated %d representations, %d forecast cases, %d scores; legacy max error %.17g. Output: %s\n",
  nrow(representations), nrow(forecast_cases), nrow(scores_per_case), verification$original_score_max_absolute_error, output))
