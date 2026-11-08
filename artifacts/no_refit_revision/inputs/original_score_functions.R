check_loss_fn <- function(p0, diff) {
    diff * p0 - diff * as.numeric(diff < 0)
}
post_crps_quantile_approx <- function(obs, sample_mat, context = "crps.quantile") {
    if (!is.matrix(sample_mat)) {
        sample_mat <- as.matrix(sample_mat)
    }
    if (!is.numeric(sample_mat) || length(dim(sample_mat)) != 2L) {
        stop(sprintf("[%s_SHAPE] sample_mat must be a numeric 2D matrix [sample x horizon].", context), 
            call. = FALSE)
    }
    n_samp <- as.integer(nrow(sample_mat))
    horizon <- as.integer(ncol(sample_mat))
    if (!is.finite(n_samp) || !is.finite(horizon) || n_samp < 2L || horizon < 1L) {
        stop(sprintf("[%s_DIM] sample_mat must have at least 2 samples and 1 horizon point.", context), 
            call. = FALSE)
    }
    obs_num <- as.numeric(obs)
    if (length(obs_num) < horizon) {
        warning(sprintf("[%s_OBS_SHORT] obs length (%d) is shorter than horizon (%d); padding with NA.", 
            context, length(obs_num), horizon), call. = FALSE)
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
        tau <- seq_len(mm)/(mm + 1)
        out[[t_idx]] <- 2 * mean(check_loss_fn(tau, yy - sample_vec))
    }
    list(crps = out, n_samples_eff = as.integer(n_eff), n_samples_nominal = n_samp, tau_rule = "k_over_m_plus_1", 
        method = "quantile_check_loss_sum")
}
