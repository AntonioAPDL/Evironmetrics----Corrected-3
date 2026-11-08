#!/usr/bin/env Rscript
# Optional diagnostics from already generated quantile-fit cubes. No new draws.

n14_require <- function(condition, message) {
  if (!isTRUE(condition)) stop(message, call. = FALSE)
}
n14_hash <- function(path) digest::digest(file = path, algo = "sha256", serialize = FALSE)
n14_read <- function(path) utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE,
                                         colClasses = "character")
n14_num <- function(x) trimws(formatC(as.numeric(x), digits = 17L, format = "g"))
n14_write <- function(data, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(data, path, row.names = FALSE, na = "", quote = TRUE)
}
n14_json <- function(value, path) {
  jsonlite::write_json(value, path, auto_unbox = TRUE, pretty = TRUE, null = "null", digits = NA)
}
n14_levels <- c(.05, .20, .35, .50, .65, .80, .95)
n14_models <- c("AL-U-T1", "AL-M-T0", "AL-M-T1", "exAL-U-T1", "exAL-M-T0", "exAL-M-T1")

n14_own_anchors <- function(cube, levels = n14_levels) {
  n14_require(is.numeric(cube) && identical(length(dim(cube)), 3L), "Expected numeric 3D predictive cube")
  n14_require(dim(cube)[1L] == length(levels) && all(is.finite(cube)), "Invalid cube levels or finite support")
  out <- matrix(NA_real_, nrow = length(levels), ncol = dim(cube)[3L])
  for (h in seq_len(ncol(out))) for (k in seq_along(levels)) {
    out[k, h] <- stats::quantile(cube[k, , h], levels[k], type = 7L, names = FALSE)
  }
  out
}
n14_isotonic <- function(anchors, levels = n14_levels) {
  n14_require(is.matrix(anchors) && nrow(anchors) == length(levels) && all(is.finite(anchors)),
              "Invalid predictive anchors")
  apply(anchors, 2L, function(x) stats::isoreg(x = levels, y = x)$yf)
}
n14_loss <- function(observed, prediction, tau) {
  error <- observed - prediction
  (tau - as.numeric(error < 0)) * error
}
n14_crossings <- function(quantiles) {
  gap <- diff(quantiles)
  c(n_crossings = sum(gap < 0), max_negative_gap = min(c(0, gap)))
}

n14_extract <- function(article, output) {
  core <- file.path(article, "artifacts/no_refit_revision")
  manifest <- n14_read(file.path(article, "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv"))
  selected <- manifest[manifest$manuscript_label %in% n14_models, , drop = FALSE]
  n14_require(nrow(selected) == 30L, "Expected thirty selected AL/exAL origins")
  representations <- n14_read(file.path(core, "inputs/representations.csv"))
  final_q <- n14_read(file.path(core, "results/quantiles_per_case.csv"))
  final_q <- final_q[final_q$model_id %in% n14_models & final_q$score_scale == "log1p_cms", , drop = FALSE]
  observations <- n14_read(file.path(core, "results/observations.csv"))
  n14_require(nrow(final_q) == 5880L && nrow(observations) == 140L, "Core quantile/date dimensions differ")
  endpoints <- sources <- support <- vector("list", nrow(selected))
  for (i in seq_len(nrow(selected))) {
    row <- selected[i, , drop = FALSE]
    model <- row$manuscript_label
    origin <- format(as.Date(row$cutoff, "%Y%m%d"), "%Y-%m-%d")
    id <- paste(row$cutoff, model, sep = "__")
    representation <- representations[representations$representation_id == id, , drop = FALSE]
    n14_require(nrow(representation) == 1L && representation$source_run_id == row$run_id,
                "Selected run identity differs from frozen representation")
    cache <- file.path(row$artifact_run_root, "post/cache")
    if (grepl("-U-", model)) {
      cube_path <- file.path(cache, "y_forecast_uni.rds")
    } else {
      candidates <- list.files(cache, pattern = "y_reps_f_new_smoke[.]rds$", full.names = TRUE)
      n14_require(length(candidates) == 1L, "Ambiguous selected predictive cube")
      cube_path <- candidates[[1L]]
    }
    config_path <- row$resolved_config_path
    config_hash <- n14_hash(config_path)
    config <- yaml::read_yaml(config_path)
    raw_scale <- config$scale_contract$analysis_scale_post_internal
    n14_require(identical(raw_scale, "log1p_cms"), "Predictive cube requires an independently verified scale mapping")
    cube_hash <- n14_hash(cube_path)
    cube <- readRDS(cube_path)
    n14_require(identical(dim(cube), c(7L, 2000L, 28L)), "Unexpected predictive cube shape")
    anchors <- n14_own_anchors(cube)
    isotonic <- n14_isotonic(anchors)
    raw_cache_hash <- ""
    raw_cache_error <- NA_real_
    if (grepl("-U-", model)) {
      raw_cache <- file.path(cache, "univar_raw_forecast_quantiles_log1p.rds")
      raw_cache_hash <- n14_hash(raw_cache)
      raw_cache_error <- max(abs(anchors - readRDS(raw_cache)))
      n14_require(raw_cache_error <= 1e-12, "Univariate own-fit anchor/scale parity failed")
    }
    final_path <- file.path(core, representation$input_snapshot_relpath)
    n14_require(n14_hash(final_path) == representation$source_sha256, "Frozen final prediction hash changed")
    final_matrix <- readRDS(final_path)
    n14_require(identical(dim(final_matrix), c(2000L, 28L)) && all(is.finite(final_matrix)),
                "Invalid saved final predictive matrix")
    qrows <- final_q[final_q$representation_id == id, , drop = FALSE]
    n14_require(nrow(qrows) == 196L, "Final quantile case set incomplete")
    qrows <- qrows[order(as.integer(qrows$lead_day), as.numeric(qrows$tau)), , drop = FALSE]
    n14_require(identical(as.numeric(qrows$tau), rep(n14_levels, 28L)), "Final tau order differs")
    observed <- observations[observations$origin_date == origin, , drop = FALSE]
    observed <- observed[order(as.integer(observed$lead_day)), , drop = FALSE]
    n14_require(nrow(observed) == 28L && identical(qrows$target_date, rep(observed$target_date, each = 7L)),
                "Final quantile/observation dates differ")
    n14_require(all(abs(as.numeric(qrows$check_loss) - n14_loss(rep(as.numeric(observed$observed_log1p_cms), each = 7L),
                                                            as.numeric(qrows$quantile_value), as.numeric(qrows$tau))) <= 1e-12),
                "Core final quantile check loss differs")
    endpoints[[i]] <- data.frame(representation_id = id, model_id = model, origin_date = origin,
                                 source_run_id = row$run_id,
                                 lead_day = rep(seq_len(28L), each = 7L), target_date = qrows$target_date,
                                 tau = rep(sprintf("%.2f", n14_levels), 28L),
                                 own_fit_anchor = n14_num(as.numeric(anchors)),
                                 isotonic_anchor = n14_num(as.numeric(isotonic)),
                                 final_quantile = qrows$quantile_value,
                                 observed_log1p_cms = rep(observed$observed_log1p_cms, each = 7L),
                                 own_anchor_definition = "empirical_own_fit_predictive_quantile_type7",
                                 isotonic_definition = "equal_weight_isoreg_of_own_fit_anchors",
                                 final_quantile_definition = qrows$quantile_definition,
                                 final_quantile_source = qrows$quantile_source,
                                 stringsAsFactors = FALSE)
    sources[[i]] <- data.frame(representation_id = id, source_run_id = row$run_id,
                               source_cube = cube_path, source_cube_sha256 = cube_hash,
                               source_cube_bytes = as.character(file.info(cube_path)$size),
                               cube_dimensions = "7x2000x28", cube_scale = raw_scale,
                               config_path = config_path, config_sha256 = config_hash,
                               final_prediction_sha256 = representation$source_sha256,
                               own_anchor_type = "7", final_quantile_definition = unique(qrows$quantile_definition),
                               own_cache_sha256 = raw_cache_hash,
                               own_cache_max_abs_error = if (is.finite(raw_cache_error)) n14_num(raw_cache_error) else "not_applicable",
                               stringsAsFactors = FALSE)
    support[[i]] <- data.frame(representation_id = id, model_id = model,
                               raw_cube_negative_log_values = sum(cube < 0),
                               raw_cube_minimum = n14_num(min(cube)),
                               final_prediction_negative_log_values = sum(final_matrix < 0),
                               final_prediction_minimum = n14_num(min(final_matrix)),
                               clipped_values = 0L, stringsAsFactors = FALSE)
    n14_require(n14_hash(cube_path) == cube_hash && n14_hash(config_path) == config_hash,
                "Source changed during bounded extraction")
  }
  input_dir <- file.path(output, "inputs")
  dir.create(input_dir, recursive = TRUE, showWarnings = FALSE)
  n14_write(do.call(rbind, endpoints), file.path(input_dir, "anchors.csv"))
  n14_write(do.call(rbind, sources), file.path(input_dir, "sources.csv"))
  n14_write(do.call(rbind, support), file.path(input_dir, "support.csv"))
  n14_json(list(extraction = "thirty frozen raw cubes and selected final matrices read once; no fitted state objects",
                replay = "compact anchors, definitions, observations and source hashes only; original cubes not required",
                original_scale_rule = "expm1 of declared log-scale quantiles and observed values; no clipping",
                source_files = lapply(c("R/environmetrics/02_helpers_core.R", "R/environmetrics/30_univariate_and_misc.R",
                                       "R/environmetrics/40_figures_smoke_fast.R", "R/environmetrics/utils_data.R"),
                                      function(x) list(path = x, sha256 = n14_hash(file.path(dirname(article), "workflow", x)))),
                core_quantile_sha256 = n14_hash(file.path(core, "results/quantiles_per_case.csv")),
                published_manifest_sha256 = n14_hash(file.path(article, "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv"))),
           file.path(input_dir, "source_evidence.json"))
}

n14_derive <- function(inputs) {
  anchors <- n14_read(file.path(inputs, "anchors.csv"))
  n14_require(nrow(anchors) == 5880L && length(unique(anchors$representation_id)) == 30L,
              "Incomplete thirty-origin anchor registry")
  key <- paste(anchors$representation_id, anchors$lead_day, anchors$tau)
  n14_require(!anyDuplicated(key), "Duplicate anchor key")
  numeric_columns <- c("own_fit_anchor", "isotonic_anchor", "final_quantile", "observed_log1p_cms", "tau")
  n14_require(all(vapply(anchors[numeric_columns], function(x) all(is.finite(as.numeric(x))), logical(1))),
              "Nonfinite compact anchor input")
  role_columns <- c(own_fit_predictive = "own_fit_anchor", isotonic_anchor = "isotonic_anchor",
                    final_synthesized = "final_quantile")
  products <- list()
  per_case <- crossing <- list()
  for (scale in c("log1p_cms", "discharge_cms")) {
    y_log <- as.numeric(anchors$observed_log1p_cms)
    y <- y_log
    raw <- as.numeric(anchors$own_fit_anchor)
    if (scale == "discharge_cms") { y <- expm1(y); raw <- expm1(raw) }
    for (role in names(role_columns)) {
      prediction_log <- as.numeric(anchors[[role_columns[[role]]]])
      prediction <- prediction_log
      if (scale == "discharge_cms") prediction <- expm1(prediction)
      n14_require(all(is.finite(prediction)), "Nonfinite inverse-transformed anchor")
      per_case[[length(per_case) + 1L]] <- data.frame(
        anchors[c("representation_id", "model_id", "origin_date", "lead_day", "target_date", "tau")],
        role = role, score_scale = scale, quantile_value = n14_num(prediction), observed = n14_num(y),
        hit_strict = as.integer(y_log < prediction_log), hit_weak = as.integer(y_log <= prediction_log),
        exact_tie = as.integer(y_log == prediction_log),
        check_loss = n14_num(n14_loss(y, prediction, as.numeric(anchors$tau))),
        displacement_from_own_anchor = n14_num(prediction - raw), stringsAsFactors = FALSE)
    }
  }
  cases <- do.call(rbind, per_case)
  for (role in names(role_columns)) {
    for (id in unique(anchors$representation_id)) {
      selected <- anchors[anchors$representation_id == id, , drop = FALSE]
      for (h in seq_len(28L)) {
        values <- selected[as.integer(selected$lead_day) == h, , drop = FALSE]
        values <- values[order(as.numeric(values$tau)), , drop = FALSE]
        cc <- n14_crossings(as.numeric(values[[role_columns[[role]]]]))
        crossing[[length(crossing) + 1L]] <- data.frame(representation_id = id, model_id = selected$model_id[1L],
                                                       origin_date = selected$origin_date[1L], lead_day = h,
                                                       role = role, n_crossings = as.integer(cc[1L]),
                                                       has_crossing = as.integer(cc[1L] > 0),
                                                       max_negative_gap = n14_num(cc[2L]), stringsAsFactors = FALSE)
      }
    }
  }
  cross <- do.call(rbind, crossing)
  summarize <- function(data, pooled) {
    out <- list()
    for (horizon in c(8L, 28L)) {
      limited <- data[as.integer(data$lead_day) <= horizon, , drop = FALSE]
      group_columns <- c("model_id", if (!pooled) "origin_date", "tau", "role", "score_scale")
      group <- do.call(paste, c(limited[group_columns], sep = "|"))
      for (indices in split(seq_len(nrow(limited)), group)) {
        block <- limited[indices, , drop = FALSE]
        out[[length(out) + 1L]] <- data.frame(block[1L, group_columns, drop = FALSE],
          horizon_days = horizon, n = nrow(block),
          n_strict = sum(as.integer(block$hit_strict)), n_weak = sum(as.integer(block$hit_weak)),
          n_tie = sum(as.integer(block$exact_tie)),
          rate_strict = n14_num(mean(as.integer(block$hit_strict))),
          rate_weak = n14_num(mean(as.integer(block$hit_weak))),
          mean_check_loss = n14_num(mean(as.numeric(block$check_loss))),
          mean_displacement = n14_num(mean(as.numeric(block$displacement_from_own_anchor))),
          mean_absolute_displacement = n14_num(mean(abs(as.numeric(block$displacement_from_own_anchor)))),
          stringsAsFactors = FALSE)
      }
    }
    do.call(rbind, out)
  }
  cross_summary <- aggregate(cbind(has_crossing, n_crossings) ~ model_id + role, cross, sum)
  cross_summary$n_dates <- 140L
  products[["per_case.csv"]] <- cases
  products[["summary_by_origin_horizon.csv"]] <- summarize(cases, FALSE)
  products[["summary_pooled.csv"]] <- summarize(cases, TRUE)
  products[["crossings_per_case.csv"]] <- cross
  products[["crossing_summary.csv"]] <- cross_summary
  products
}

n14_main <- function(arguments = commandArgs(TRUE)) {
  Sys.setenv(OMP_NUM_THREADS = "1", OPENBLAS_NUM_THREADS = "1", MKL_NUM_THREADS = "1")
  started <- proc.time()[["elapsed"]]
  arg <- function(name) { j <- match(name, arguments); if (is.na(j)) return(NULL); arguments[j + 1L] }
  output <- arg("--output-dir")
  n14_require(!is.null(output), "--output-dir is required")
  check <- "--check" %in% arguments
  inputs <- arg("--inputs-dir")
  article <- arg("--article-root")
  if (check) {
    manifest <- jsonlite::read_json(file.path(output, "manifest.json"), simplifyVector = TRUE)
    for (rel in names(manifest$files)) n14_require(n14_hash(file.path(output, rel)) == manifest$files[[rel]],
                                                  paste("Artifact checksum differs:", rel))
    cat("Validated synthesis diagnostic checksums; no source objects read.\n")
    return(invisible(NULL))
  }
  n14_require(!dir.exists(output), "Output directory must be fresh")
  dir.create(output, recursive = TRUE)
  if (is.null(inputs)) {
    n14_require(!is.null(article), "Extraction requires --article-root")
    n14_extract(normalizePath(article), output)
    inputs <- file.path(output, "inputs")
  } else {
    dir.create(file.path(output, "inputs"))
    files <- list.files(inputs, full.names = TRUE)
    n14_require(all(file.copy(files, file.path(output, "inputs"))), "Portable input copy failed")
    inputs <- file.path(output, "inputs")
  }
  products <- n14_derive(inputs)
  for (name in names(products)) n14_write(products[[name]], file.path(output, name))
  dir.create(file.path(output, "reproduce"))
  script_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
  script <- sub("^--file=", "", script_arg[[1L]])
  file.copy(script, file.path(output, "reproduce/build_no_refit_synthesis_diagnostics.R"))
  support <- n14_read(file.path(inputs, "support.csv"))
  verified <- list(status = "COMPLETE", new_fits = FALSE, new_draws = FALSE, source_objects = "predictive cubes only",
                   anchor_rows = nrow(n14_read(file.path(inputs, "anchors.csv"))),
                   per_case_rows = nrow(products$per_case.csv),
                   raw_cube_bytes_hashed = sum(as.numeric(n14_read(file.path(inputs, "sources.csv"))$source_cube_bytes)),
                   negative_final_log_representations = sum(as.numeric(support$final_prediction_negative_log_values) > 0),
                   negative_values_clipped = 0L,
                   pre_synthesis_CRPS = "not_defined_or_computed; own-fit anchors do not define a single predictive distribution")
  n14_json(verified, file.path(output, "verification.json"))
  writeLines(c("Optional own-fit/isotonic/final synthesis diagnostics from frozen predictions.",
               "Own-fit anchors are empirical predictive quantiles, not latent state locations.",
               "Final HE4 targets retain their existing values; other final targets use declared type8.",
               "Anchor crossings describe separate quantile-fit curves, not joint posterior sample paths.",
               "No pre-synthesis CRPS, clipping, fitting, draw generation or synthesis call occurs.",
               "Portable replay uses compact anchors/observations; the original cubes are required only for first extraction.",
               "From this directory, run into a fresh destination:",
               "  Rscript --vanilla reproduce/build_no_refit_synthesis_diagnostics.R --inputs-dir inputs --output-dir /tmp/synthesis_replay",
               "Read-only checksums:",
               "  Rscript --vanilla reproduce/build_no_refit_synthesis_diagnostics.R --output-dir . --check"),
             file.path(output, "README.txt"))
  files <- list.files(output, recursive = TRUE)
  manifest <- list(schema = "no_refit_synthesis_diagnostics_v1", files = setNames(lapply(files, function(x) n14_hash(file.path(output, x))), files))
  n14_json(manifest, file.path(output, "manifest.json"))
  elapsed <- proc.time()[["elapsed"]] - started
  cat(sprintf("Completed deterministic synthesis diagnostics in %.3f seconds: %d anchor rows, %d role/scale rows.\n",
              elapsed, verified$anchor_rows, verified$per_case_rows))
}

if (sys.nframe() == 0L) n14_main()
