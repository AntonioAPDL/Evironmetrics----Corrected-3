#!/usr/bin/env python3
"""Check conditional-density identities on fixed synthetic inputs.

These checks draw no random values, read no fitted objects, and implement no
Markov chain. They check the historical augmented kernels and conditional
Gaussian FFBS formulas used to delimit the manuscript's mathematical scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def exal_constants(gamma: float, p0: float = 0.5) -> tuple[float, float, float]:
    g = math.exp(0.5 * gamma * gamma) * math.erfc(abs(gamma) / math.sqrt(2.0))
    negative = float(gamma < 0.0)
    p = (p0 - negative) / g + negative
    if not 0.0 < p < 1.0:
        raise ValueError("Synthetic gamma is outside its admissible quantile support")
    return (1.0 - 2.0 * p) / (p * (1.0 - p)), 2.0 / (p * (1.0 - p)), 1.0 / (float(gamma > 0.0) - p)


def normal_log_kernel(y: np.ndarray, mu: np.ndarray, v: np.ndarray, s: np.ndarray, sigma: float, gamma: float) -> float:
    a, b, c = exal_constants(gamma)
    variance = b * sigma * v
    residual = y - mu - a * v - c * sigma * abs(gamma) * s
    return float(np.sum(-0.5 * np.log(variance) - residual * residual / (2.0 * variance)))


def constant_difference(full: list[float], reduced: list[float], atol: float = 2e-11) -> float:
    differences = np.asarray(full) - np.asarray(reduced)
    error = float(np.max(np.abs(differences - differences[0])))
    if not math.isfinite(error) or error > atol:
        raise AssertionError(f"Kernel differences are not constant: {error}")
    return error


def check_augmentation_kernels() -> dict[str, float]:
    y = np.array([0.7, -0.2, 1.3])
    mu = np.array([0.1, 0.2, 0.4])
    v = np.array([0.3, 0.7, 1.2])
    s = np.array([0.2, 0.8, 0.5])
    sigma, gamma = 0.8, 0.3
    a, b, c = exal_constants(gamma)
    r = y - mu

    full, reduced = [], []
    shape = 0.5
    psi = (a * a / b + 2.0) / sigma
    chi = (r[0] - c * sigma * abs(gamma) * s[0]) ** 2 / (b * sigma)
    for value in [0.05, 0.2, 0.6, 1.5, 4.0]:
        trial = v.copy()
        trial[0] = value
        full.append(normal_log_kernel(y, mu, trial, s, sigma, gamma) - value / sigma)
        reduced.append((shape - 1.0) * math.log(value) - 0.5 * (psi * value + chi / value))
    v_error = constant_difference(full, reduced)

    variance = 1.0 / (1.0 + c * c * gamma * gamma * sigma / (b * v[0]))
    mean = variance * c * abs(gamma) * (r[0] - a * v[0]) / (b * v[0])
    full, reduced = [], []
    for value in [0.01, 0.15, 0.5, 1.1, 3.0]:
        trial = s.copy()
        trial[0] = value
        full.append(normal_log_kernel(y, mu, v, trial, sigma, gamma) - 0.5 * value * value)
        reduced.append(-0.5 * (value - mean) ** 2 / variance)
    s_error = constant_difference(full, reduced)

    prior_shape, prior_scale = 2.3, 1.7
    shape = -prior_shape - 1.5 * len(y)
    psi = float(np.sum((c * abs(gamma) * s) ** 2 / (b * v)))
    chi = float(np.sum((r - a * v) ** 2 / (b * v)) + 2.0 * np.sum(v) + 2.0 * prior_scale)
    full, reduced = [], []
    for value in [0.07, 0.2, 0.8, 1.6, 4.1]:
        full.append(normal_log_kernel(y, mu, v, s, value, gamma) - len(y) * math.log(value) - float(np.sum(v)) / value - (prior_shape + 1.0) * math.log(value) - prior_scale / value)
        reduced.append((shape - 1.0) * math.log(value) - 0.5 * (psi * value + chi / value))
    sigma_error = constant_difference(full, reduced)

    # The zero-quadratic-coefficient scale conditional is an inverse gamma.
    gamma_zero = 0.0
    a_zero, b_zero, _ = exal_constants(gamma_zero)
    ig_shape = prior_shape + 1.5 * len(y)
    ig_scale = float(np.sum((r - a_zero * v) ** 2 / (b_zero * v)) / 2.0 + np.sum(v) + prior_scale)
    full, reduced = [], []
    for value in [0.1, 0.4, 1.0, 2.4]:
        full.append(normal_log_kernel(y, mu, v, s, value, gamma_zero) - len(y) * math.log(value) - float(np.sum(v)) / value - (prior_shape + 1.0) * math.log(value) - prior_scale / value)
        reduced.append(-(ig_shape + 1.0) * math.log(value) - ig_scale / value)
    sigma_zero_error = constant_difference(full, reduced)

    # Gamma-dependent terms must all be evaluated at each proposal.
    prior_df, prior_scale_gamma = 5.0, 0.7
    full, reduced = [], []
    for value in [-0.45, -0.2, 0.1, 0.35, 0.5]:
        aa, bb, cc = exal_constants(value)
        log_prior = -0.5 * (prior_df + 1.0) * math.log1p(value * value / (prior_df * prior_scale_gamma * prior_scale_gamma))
        full.append(normal_log_kernel(y, mu, v, s, sigma, value) + log_prior)
        reduced.append(log_prior - 0.5 * len(y) * math.log(bb) - float(np.sum((r - aa * v - cc * sigma * abs(value) * s) ** 2 / v)) / (2.0 * bb * sigma))
    gamma_error = constant_difference(full, reduced)
    return {
        "augmentation_v_kernel_max_constant_difference_error": v_error,
        "augmentation_s_kernel_max_constant_difference_error": s_error,
        "scale_kernel_max_constant_difference_error": sigma_error,
        "scale_zero_quadratic_coefficient_limit_max_constant_difference_error": sigma_zero_error,
        "gamma_kernel_max_constant_difference_error": gamma_error,
    }


def check_ffbs_conditionals() -> dict[str, float]:
    t_count, dim = 3, 2
    m0 = np.array([0.2, -0.1])
    c0 = np.array([[0.7, 0.08], [0.08, 0.4]])
    transition = np.array([[0.9, 0.1], [0.0, 0.8]])
    innovation = np.array([[0.12, 0.02], [0.02, 0.09]])
    loading = np.array([[1.0, 0.3], [-0.2, 0.9]])
    measurement = np.diag([0.25, 0.35])
    offset = np.array([0.05, -0.03])
    observations = np.array([[0.6, -0.1], [0.2, 0.3], [0.8, -0.2]])

    prior_mean = np.zeros((t_count + 1, dim))
    prior_mean[0] = m0
    prior_cov = np.zeros(((t_count + 1) * dim, (t_count + 1) * dim))
    prior_cov[:dim, :dim] = c0
    for t in range(1, t_count + 1):
        sl = slice(t * dim, (t + 1) * dim)
        prev = slice((t - 1) * dim, t * dim)
        prior_mean[t] = transition @ prior_mean[t - 1]
        for j in range(t):
            other = slice(j * dim, (j + 1) * dim)
            prior_cov[sl, other] = transition @ prior_cov[prev, other]
            prior_cov[other, sl] = prior_cov[sl, other].T
        prior_cov[sl, sl] = transition @ prior_cov[prev, prev] @ transition.T + innovation
    design = np.zeros((t_count * dim, (t_count + 1) * dim))
    for t in range(1, t_count + 1):
        design[(t - 1) * dim:t * dim, t * dim:(t + 1) * dim] = loading.T
    noise = np.kron(np.eye(t_count), measurement)
    vector_mean = prior_mean.reshape(-1)
    residual = (observations - offset).reshape(-1) - design @ vector_mean
    gain = np.linalg.solve(design @ prior_cov @ design.T + noise, design @ prior_cov).T
    posterior_mean = vector_mean + gain @ residual
    posterior_cov = prior_cov - gain @ design @ prior_cov

    filtered_mean = [m0]
    filtered_cov = [c0]
    forecast_mean, forecast_cov = [None], [None]
    for t in range(1, t_count + 1):
        aa = transition @ filtered_mean[-1]
        rr = transition @ filtered_cov[-1] @ transition.T + innovation
        qq = loading.T @ rr @ loading + measurement
        gg = np.linalg.solve(qq, loading.T @ rr).T
        filtered_mean.append(aa + gg @ (observations[t - 1] - loading.T @ aa - offset))
        filtered_cov.append(rr - gg @ loading.T @ rr)
        forecast_mean.append(aa)
        forecast_cov.append(rr)
    terminal_mean_error = float(np.max(np.abs(filtered_mean[-1] - posterior_mean[-dim:])))
    terminal_cov_error = float(np.max(np.abs(filtered_cov[-1] - posterior_cov[-dim:, -dim:])))
    mean_errors, cov_errors = [], []
    fixed_next_state = np.array([0.4, -0.25])
    for t in range(t_count):
        sl = slice(t * dim, (t + 1) * dim)
        nxt = slice((t + 1) * dim, (t + 2) * dim)
        cond_gain = np.linalg.solve(posterior_cov[nxt, nxt], posterior_cov[nxt, sl]).T
        exact_mean = posterior_mean[sl] + cond_gain @ (fixed_next_state - posterior_mean[nxt])
        exact_cov = posterior_cov[sl, sl] - cond_gain @ posterior_cov[nxt, sl]
        backward_gain = np.linalg.solve(forecast_cov[t + 1], transition @ filtered_cov[t]).T
        recursion_mean = filtered_mean[t] + backward_gain @ (fixed_next_state - forecast_mean[t + 1])
        recursion_cov = filtered_cov[t] - backward_gain @ transition @ filtered_cov[t]
        mean_errors.append(float(np.max(np.abs(recursion_mean - exact_mean))))
        cov_errors.append(float(np.max(np.abs(recursion_cov - exact_cov))))
    results = {
        "ffbs_terminal_mean_error": terminal_mean_error,
        "ffbs_terminal_covariance_error": terminal_cov_error,
        "ffbs_backward_conditional_mean_error": max(mean_errors),
        "ffbs_backward_conditional_covariance_error": max(cov_errors),
    }
    if any(not math.isfinite(v) or v > 2e-12 for v in results.values()):
        raise AssertionError(results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    checks = {**check_augmentation_kernels(), **check_ffbs_conditionals()}
    report = {
        "status": "PASS",
        "scope": "deterministic conditional identities for a historical submodel with specified covariance",
        "checks": checks,
        "checks_count": len(checks),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "numpy_version": np.__version__,
        "random_values_drawn": 0,
        "fitted_objects_read": 0,
        "article_data_used": False,
        "sampler_implemented": False,
        "mcmc_accuracy_assessed": False,
        "historical_or_forecast_results_modified": False,
    }
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
