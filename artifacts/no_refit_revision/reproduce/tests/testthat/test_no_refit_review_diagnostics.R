library(testthat)
workflow <- normalizePath(if (file.exists("R/environmetrics/no_refit_review_helpers.R")) "." else "../..")
source(file.path(workflow, "R/environmetrics/no_refit_review_helpers.R"), local = TRUE)

test_that("sorted ECDF and adjusted scores agree with independent pairwise formulas", {
  cases <- list(c(0, 2), c(-1, -1, 3), rep(4, 4), c(-3, 0, 2, 9),
                seq(-.4, 3, length.out = 48), seq(-1, 2, length.out = 64),
                seq(-.1, 4, length.out = 2000))
  for (x in cases) {
    y <- .7
    result <- nrf_sorted_scores(x, y, adjusted = TRUE)
    # Independent quadratic reference only in these small bounded tests.
    pairwise_mean <- mean(abs(outer(x, x, `-`)))
    expected <- mean(abs(x - y)) - pairwise_mean / 2
    expect_equal(result$ecdf, expected, tolerance = 1e-12)
    expect_equal(result$adjusted, mean(abs(x - y)) - pairwise_mean * length(x) / (2 * (length(x) - 1)), tolerance = 1e-12)
    expect_lt(result$legacy_identity_error, 1e-12)
    expect_equal(nrf_sorted_scores(rev(x), y, TRUE), result, tolerance = 1e-12)
  }
})

test_that("exact ECDF score agrees with a trusted independent implementation", {
  skip_if_not_installed("scoringRules")
  for (x in list(c(-1, 0, 0, 2, 5), seq(-.2, 2.8, length.out = 64), rep(.8, 51))) {
    for (y in c(-2, .3, 7)) {
      expected <- scoringRules::crps_sample(y = y, dat = matrix(x, nrow = 1L), method = "edf")
      expect_equal(nrf_sorted_scores(x, y)$ecdf, as.numeric(expected), tolerance = 1e-12)
    }
  }
})

test_that("point masses, small ensembles and support are handled without alteration", {
  for (m in c(1L, 2L, 7L, 48L, 64L, 2000L)) {
    z <- nrf_sorted_scores(rep(-.3, m), 1.2, adjusted = TRUE)
    expect_equal(z$ecdf, 1.5, tolerance = 1e-13)
    expect_equal(z$legacy, 1.5, tolerance = 1e-13)
    if (m == 1L) expect_true(is.na(z$adjusted)) else expect_equal(z$adjusted, 1.5, tolerance = 1e-13)
  }
  transformed <- nrf_inverse(matrix(c(-2, -.1, 0, 2), nrow = 2L))
  expect_identical(dim(transformed), c(2L, 2L))
  expect_true(any(transformed < 0))
  expect_equal(transformed, expm1(matrix(c(-2, -.1, 0, 2), nrow = 2L)))
  expect_error(nrf_inverse(c(0, Inf)), "Unsafe")
  expect_error(nrf_inverse(c(0, 1000)), "Unsafe")
})

test_that("score invariances and scale-aware tolerances protect large raw values", {
  x <- c(0, 1, 3, 5); y <- 2
  z <- nrf_sorted_scores(x, y, TRUE)
  shifted <- nrf_sorted_scores(x + 1e10, y + 1e10, TRUE)
  expect_equal(shifted$ecdf, z$ecdf, tolerance = 1e-12)
  expect_equal(shifted$adjusted, z$adjusted, tolerance = 1e-12)
  scaled <- nrf_sorted_scores(x * 1e12, y * 1e12, TRUE)
  expect_true(nrf_close(scaled$ecdf, z$ecdf * 1e12, atol = 1e-10, rtol = 1e-12))
  expect_false(nrf_close(NA_real_, 0))
  expect_false(nrf_close(1, 1 + 1e-5))
  expect_false(isTRUE(all.equal(mean(nrf_inverse(c(0, 3))), nrf_inverse(mean(c(0, 3))))))
})

test_that("empirical ties and closed interval endpoints retain exact partitions", {
  y <- c(0, 1, 1 + .Machine$double.eps, 2)
  q <- rep(1, 4)
  events <- nrf_quantile_events(y, q)
  expect_identical(events$hit_strict, c(1L, 0L, 0L, 0L))
  expect_identical(events$hit_weak, c(1L, 1L, 0L, 0L))
  expect_identical(events$is_exact_tie, c(0L, 1L, 0L, 0L))
  expect_identical(events$hit_weak, events$hit_strict + events$is_exact_tie)
  z <- nrf_interval_events(c(-1, 0, 1, 2, 3), rep(0, 5), rep(2, 5))
  expect_identical(z$inside, c(0L, 1L, 1L, 1L, 0L))
  expect_equal(rowSums(z[, c("lower_miss", "inside", "upper_miss")]), rep(1, 5))
  expect_equal(z$interval_score, c(42, 2, 2, 2, 42))
  expect_error(nrf_interval_events(1, 2, 0), "Invalid")
})

test_that("finite representation policy never treats grids as random samples", {
  expect_equal(nrf_representation_policy("N-U-T1")$n, 64L)
  expect_equal(nrf_representation_policy("N-M-T0")$n, 48L)
  expect_equal(nrf_representation_policy("exAL-M-T1")$n, 2000L)
  expect_equal(nrf_representation_policy("RAW-NWS")$leads, 8L)
  expect_equal(nrf_representation_policy("RAW-GLOFAS")$n, 51L)
  for (model in c("CLIM-SEASONAL", "EMOS-GLOFAS", "PERSISTENCE")) {
    policy <- nrf_representation_policy(model)
    expect_equal(policy$random, 0L)
    expect_false(nrf_adjustable(policy$status))
    expect_equal(policy$qtype, 1L)
  }
  expect_true(nrf_adjustable(nrf_representation_policy("N-M-T1")$status))
  expect_error(nrf_representation_policy("unknown"), "Unknown")
})

test_that("unexpected nonfinite values and wrong member counts fail closed", {
  expect_error(nrf_predictive_matrix(matrix(c(0, NA), 2, 1), 2L, 1L), "nonfinite")
  expect_error(nrf_predictive_matrix(matrix(0, 6, 8), 7L, 8L), "dimensions")
  expect_error(nrf_sorted_scores(c(0, NA), 1), "Nonfinite")
  expect_error(nrf_sorted_scores(numeric(0), 1), "Nonfinite")
  expect_error(nrf_unique(data.frame(id = c("a", "a")), "id"), "duplicate")
  expect_error(nrf_unique(data.frame(id = c("a", NA)), "id"), "duplicate")
})

test_that("raw reader enforces dates, members, units and duplicate multiplicity", {
  root <- tempfile("no_refit_raw_"); dir.create(root)
  raw <- data.frame(target_date = c("2022-01-01", "2022-01-02"), member_01 = c(1, 3), member_02 = c(1, 4))
  nrf_write_csv(raw, file.path(root, "raw.csv"))
  rep <- data.frame(reader_kind = "raw_csv", input_snapshot_relpath = "raw.csv", n_values_nominal = 2L, available_leads = 2L)
  z <- nrf_load_representation(rep, root, raw$target_date)
  expect_equal(z, t(log1p(as.matrix(raw[, -1]))), ignore_attr = TRUE)
  expect_equal(unname(z[1, 1]), unname(z[2, 1]))
  expect_error(nrf_load_representation(rep, root, rev(raw$target_date)), "date mismatch")
  rep$n_values_nominal <- 3L
  expect_error(nrf_load_representation(rep, root, raw$target_date), "dimensions")
  unlink(root, recursive = TRUE)
})

test_that("input manifest paths and hashes prevent source substitution", {
  root <- tempfile("no_refit_snapshot_"); dir.create(root); dir.create(file.path(root, "inputs"))
  path <- file.path(root, "inputs/value.txt"); writeLines("frozen", path)
  manifest <- list(schema_version = 1L, files = list(list(input_snapshot_relpath = "inputs/value.txt", sha256 = nrf_hash(path), bytes = unname(file.info(path)$size))))
  mp <- file.path(root, "inputs/manifest.json")
  jsonlite::write_json(manifest, mp, auto_unbox = TRUE)
  expect_silent(nrf_verify_inputs(mp))
  expect_error(nrf_safe_relative_path(root, "../escape"), "Invalid")
  expect_error(nrf_safe_relative_path(root, "/tmp/escape"), "Invalid")
  writeLines("changed", path)
  expect_error(nrf_verify_inputs(mp), "hash/size mismatch")
  unlink(root, recursive = TRUE)
})

test_that("CSV numeric precision and inverse-interval convention are explicit", {
  path <- tempfile(fileext = ".csv")
  x <- data.frame(value = c(pi, 1 + .Machine$double.eps, 1e-12, 1e14))
  nrf_write_csv(x, path)
  expect_identical(nrf_read_csv(path)$value, x$value)
  unlink(path)
  sample <- c(0, 1, 4, 8)
  inverse_limit <- expm1(quantile(sample, .975, type = 8))
  raw_recomputed <- quantile(expm1(sample), .975, type = 8)
  # Use a probability in an interpolation region to expose noncommutation.
  expect_false(isTRUE(all.equal(expm1(quantile(sample, .6, type = 8)), quantile(expm1(sample), .6, type = 8))))
  expect_true(is.finite(inverse_limit) && is.finite(raw_recomputed))
})

test_that("sealed outputs have matched cases, proper applicability and exact counts", {
  result <- Sys.getenv("NO_REFIT_RESULT_DIR", file.path(workflow, "Evironmetrics---REVISED-DOC-Corrected-2/artifacts/no_refit_revision/results"))
  skip_if_not(file.exists(file.path(result, "scores_per_case.csv")), "Set NO_REFIT_RESULT_DIR to a derived result bundle")
  scores <- nrf_read_csv(file.path(result, "scores_per_case.csv"))
  means <- nrf_read_csv(file.path(result, "summary_by_origin_horizon.csv"))
  cal <- nrf_read_csv(file.path(result, "calibration_summary.csv"))
  bands <- nrf_read_csv(file.path(result, "interval_summary.csv"))
  expect_equal(nrow(scores), 3720L); expect_equal(nrow(means), 270L)
  expect_equal(nrow(cal), 2268L); expect_equal(nrow(bands), 324L)
  expect_true(all(scores$lead_day[scores$model_id == "RAW-NWS"] <= 8L))
  expect_true(all(means$n_expected_cases == means$n_valid_cases))
  expect_true(all(cal$n_weak == cal$n_strict + cal$n_tie))
  expect_true(all(bands$n_lower_miss + bands$n_inside + bands$n_upper_miss == bands$n_valid))
  expected_na <- scores$model_id %in% c("CLIM-SEASONAL", "EMOS-GLOFAS", "PERSISTENCE")
  expect_identical(is.na(scores$iid_adjusted_crps), expected_na)
  expect_identical(scores$is_original_published_score, scores$score_scale == "log1p_cms")
  for (h in c(8L, 28L)) {
    use <- scores$model_id == "exAL-M-T1" & scores$score_scale == "log1p_cms" & scores$lead_day <= h
    actual <- mean(scores$exact_ecdf_crps[use])
    same <- scores$model_id == "CLIM-SEASONAL" & scores$score_scale == "log1p_cms" & scores$lead_day <= h
    expected_skill <- 1 - actual / mean(scores$exact_ecdf_crps[same])
    pooled <- nrf_read_csv(file.path(result, "summary_pooled.csv"))
    selected <- pooled[pooled$model_id == "exAL-M-T1" & pooled$score_scale == "log1p_cms" & pooled$horizon_days == h, ]
    expect_equal(selected$mean_exact_ecdf_crps, actual, tolerance = 1e-13)
    expect_equal(selected$ecdf_crpss, expected_skill, tolerance = 1e-13)
  }
})
