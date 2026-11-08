# Pure, bounded helpers for diagnostics of already saved forecast values.
# These helpers never fit, optimize, generate random values, or mutate sources.
nrf_assert <- function(ok, message) {
  if (!isTRUE(ok)) stop(paste0("[NO_REFIT_INPUT] ", message), call. = FALSE)
  invisible(TRUE)
}
nrf_close <- function(a, b, atol = 1e-12, rtol = 1e-12) {
  length(a) == length(b) && all(is.finite(a)) && all(is.finite(b)) &&
    all(abs(a - b) <= atol + rtol * pmax(abs(a), abs(b)))
}
nrf_hash <- function(path) digest::digest(file = path, algo = "sha256")
nrf_read_csv <- function(path) utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
nrf_write_csv <- function(x, path) {
  # write.table uses digits=15 internally; format numeric cells explicitly to
  # preserve full binary-double round-trip precision in the durable CSV files.
  out <- x
  for (key in names(out)) if (is.double(out[[key]])) {
    out[[key]] <- ifelse(is.na(out[[key]]), NA_character_, sprintf("%.17g", out[[key]]))
  }
  utils::write.table(out, path, sep = ",", row.names = FALSE, col.names = TRUE,
                     quote = TRUE, na = "", eol = "\n", fileEncoding = "UTF-8")
  invisible(path)
}
nrf_key <- function(x, keys) do.call(paste, c(x[keys], sep = "|"))
nrf_unique <- function(x, keys, label = "table") {
  nrf_assert(all(keys %in% names(x)), paste(label, "missing keys"))
  nrf_assert(!anyNA(x[keys]) && !anyDuplicated(nrf_key(x, keys)), paste(label, "duplicate/missing keys"))
  invisible(TRUE)
}
nrf_bind <- function(rows) {
  nrf_assert(length(rows) > 0L, "No result rows")
  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}
nrf_groups <- function(x, keys, fun) {
  ids <- split(seq_len(nrow(x)), nrf_key(x, keys))
  nrf_bind(lapply(ids, function(idx) {
    d <- x[idx, , drop = FALSE]
    cbind(d[1L, keys, drop = FALSE], fun(d), stringsAsFactors = FALSE)
  }))
}
nrf_predictive_matrix <- function(x, n_values, horizon) {
  nrf_assert(is.matrix(x) && is.numeric(x) && identical(dim(x), as.integer(c(n_values, horizon))), "Wrong predictive matrix dimensions")
  nrf_assert(all(is.finite(x)), "Unexpected nonfinite forecast value; no partial-member policy")
  x
}
nrf_sorted_scores <- function(values, observed, adjusted = FALSE) {
  nrf_assert(is.numeric(values) && length(values) > 0L && all(is.finite(values)) &&
               length(observed) == 1L && is.finite(observed), "Nonfinite or empty score input")
  x <- sort(values)
  m <- length(x)
  # The centered form avoids cancellation of a large common offset.
  pair_sum <- if (m == 1L) 0 else sum((2 * seq_len(m) - m - 1) * (x - x[[1L]]))
  accuracy <- mean(abs(x - observed))
  empirical <- accuracy - pair_sum / m^2
  iid <- if (isTRUE(adjusted) && m > 1L) accuracy - pair_sum / (m * (m - 1)) else NA_real_
  residual <- observed - x
  tau <- seq_len(m) / (m + 1)
  legacy <- 2 * mean(residual * (tau - as.numeric(residual < 0)))
  nrf_assert(all(is.finite(c(empirical, legacy))), "Nonfinite score output")
  list(legacy = legacy, ecdf = empirical, adjusted = iid, pair_sum = pair_sum,
       legacy_identity_error = abs(legacy - empirical - pair_sum / (m^2 * (m + 1))))
}
nrf_quantile_events <- function(observed, quantile) {
  nrf_assert(length(observed) == length(quantile) && all(is.finite(observed)) && all(is.finite(quantile)), "Invalid quantile events")
  data.frame(hit_strict = as.integer(observed < quantile), hit_weak = as.integer(observed <= quantile),
             is_exact_tie = as.integer(observed == quantile))
}
nrf_interval_events <- function(observed, lower, upper, alpha = .05) {
  nrf_assert(length(observed) == length(lower) && length(lower) == length(upper) &&
               all(is.finite(c(observed, lower, upper))) && all(lower <= upper) && alpha > 0 && alpha < 1,
             "Invalid interval inputs")
  below <- observed < lower; above <- observed > upper
  data.frame(lower_miss = as.integer(below), inside = as.integer(!below & !above), upper_miss = as.integer(above),
    width = upper - lower,
    interval_score = upper - lower + (2 / alpha) * (lower - observed) * below + (2 / alpha) * (observed - upper) * above)
}
nrf_inverse <- function(x) {
  nrf_assert(is.numeric(x) && all(is.finite(x)) && all(x < log(.Machine$double.xmax)), "Unsafe original-scale transform")
  out <- expm1(x)
  nrf_assert(all(is.finite(out)), "Nonfinite original-scale prediction")
  out
}
nrf_representation_policy <- function(model) {
  if (model %in% c("RAW-GLOFAS", "RAW-NWS")) return(list(kind = "physical_ensemble", n = if (model == "RAW-GLOFAS") 51L else 7L,
    leads = if (model == "RAW-GLOFAS") 28L else 8L, random = NA_integer_, status = "physical_ensemble_iid_assumption_only", qtype = 1L))
  if (model == "PERSISTENCE") return(list(kind = "point_mass", n = 2000L, leads = 28L, random = 0L,
    status = "not_applicable_point_mass", qtype = 1L))
  if (model %in% c("CLIM-SEASONAL", "EMOS-GLOFAS")) return(list(kind = "deterministic_quantile_grid", n = 2000L, leads = 28L,
    random = 0L, status = "not_applicable_deterministic_grid", qtype = 1L))
  if (grepl("^N-", model)) return(list(kind = "model_marginal_mc", n = if (model == "N-U-T1") 64L else 48L, leads = 28L,
    random = if (model == "N-U-T1") 64L else 48L, status = "model_mc_recorded_generator", qtype = 8L))
  nrf_assert(model %in% c("AL-U-T1", "AL-M-T0", "AL-M-T1", "exAL-U-T1", "exAL-M-T0", "exAL-M-T1"), "Unknown model")
  list(kind = "model_inversecdf_mc", n = 2000L, leads = 28L, random = 2000L, status = "model_mc_conditional_curve", qtype = 8L)
}
nrf_adjustable <- function(status) status %in% c("model_mc_conditional_curve", "model_mc_recorded_generator", "physical_ensemble_iid_assumption_only")
nrf_case_set <- function(origin, horizon) paste0(ifelse(origin == "POOL", "five_origins", origin), "_leads_1_", horizon)
nrf_safe_relative_path <- function(root, path) {
  nrf_assert(is.character(path) && length(path) == 1L && nzchar(path) && !grepl("^/|(^|/)\\.\\.(/|$)", path), "Invalid portable input path")
  joined <- normalizePath(file.path(root, path), mustWork = TRUE)
  base <- normalizePath(root, mustWork = TRUE)
  nrf_assert(startsWith(joined, paste0(base, "/")), "Input path escapes its bundle")
  joined
}
nrf_verify_inputs <- function(manifest_path) {
  manifest <- jsonlite::fromJSON(manifest_path, simplifyVector = FALSE)
  root <- dirname(dirname(normalizePath(manifest_path, mustWork = TRUE)))
  nrf_assert(identical(manifest$schema_version, 1L), "Unsupported input manifest")
  for (entry in manifest$files) {
    p <- nrf_safe_relative_path(root, entry$input_snapshot_relpath)
    nrf_assert(unname(file.info(p)$size) == entry$bytes && identical(nrf_hash(p), entry$sha256), paste("Snapshot hash/size mismatch", entry$input_snapshot_relpath))
  }
  list(root = root, manifest = manifest)
}
nrf_load_representation <- function(rep, bundle_root, expected_dates) {
  path <- nrf_safe_relative_path(bundle_root, rep$input_snapshot_relpath)
  if (rep$reader_kind == "raw_csv") {
    z <- nrf_read_csv(path)
    nrf_assert(identical(as.character(z$target_date), expected_dates), "Raw product date mismatch")
    members <- as.matrix(z[, grepl("^member_", names(z)), drop = FALSE])
    nrf_assert(is.numeric(members) && all(is.finite(members)) && all(members >= 0), "Invalid raw product members")
    values <- t(log1p(members))
  } else if (rep$reader_kind == "external_list_rds") {
    z <- readRDS(path)
    nrf_assert(identical(z$dates, expected_dates) && identical(z$probabilities, seq_len(2000L) / 2001), "External grid dates/probabilities mismatch")
    values <- z$predictions[[rep$object_key]]
    nrf_assert(all(values >= 0) && all(apply(values, 2L, function(x) all(diff(x) >= 0))), "Invalid deterministic grid")
  } else {
    nrf_assert(rep$reader_kind == "matrix_rds", "Unknown forecast reader")
    values <- readRDS(path)
  }
  nrf_predictive_matrix(values, rep$n_values_nominal, rep$available_leads)
}
