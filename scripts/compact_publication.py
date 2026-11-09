#!/usr/bin/env python3
"""Render compact publication displays from a bounded set of archived summaries.

This module never fits models, loads posterior caches or computes forecast scores.
It averages only the already archived daily check losses. All input validation is
completed before any output is written. ``--check`` regenerates in memory and
compares bytes without modifying either inputs or outputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = "tables/compact_publication"
ARTIFACT_DIR = "artifacts/compact_publication"
ORIGINS = ("20210123", "20211112", "20211221", "20220511", "20221225")
ORIGIN_LABELS = ("Jan 2021", "Nov 2021", "Dec 2021", "May 2022", "Dec 2022")
METHODS = ("N-U-T1", "N-M-T0", "N-M-T1", "AL-U-T1", "AL-M-T0", "AL-M-T1",
           "exAL-U-T1", "exAL-M-T0", "exAL-M-T1", "RAW-GLOFAS", "RAW-NWS",
           "CLIM-SEASONAL", "PERSISTENCE", "EMOS-GLOFAS")
QUANTILE_METHODS = ("AL-M-T1", "AL-U-T1", "exAL-M-T1", "exAL-U-T1")
TAUS = (.05, .20, .35, .50, .65, .80, .95)
COMPONENTS = ("RAW-GLOFAS", "RAW-NWS", "exAL-M-T1 (full)",
              "exAL-M-T1-noTrend", "exAL-M-noTF", "exAL-M-T1-noH1",
              "exAL-M-T1-noH2", "exAL-M-T1-noH3")
DISPLAY = {"RAW-GLOFAS": "GloFAS", "RAW-NWS": "NWS",
           "CLIM-SEASONAL": "Seasonal climatology", "PERSISTENCE": "Persistence",
           "EMOS-GLOFAS": "GloFAS EMOS"}
INPUTS = {
    "aggregate": "artifacts/comment2_revision/external_baselines/aggregate.csv",
    "origin_scores": "artifacts/comment2_revision/external_baselines/by_origin_horizon.csv",
    "components": "tables/generated_tex/he3_ablation_crps_horizon_summary.csv",
    "fits": "artifacts/comment2_revision/component_diagnostics/fit_ledger.csv",
    "runs": "artifacts/comment2_revision/component_diagnostics/run_ledger.csv",
    "losses": "artifacts/he4_quantile_check_loss_current_publication/he4_quantile_check_loss_per_day.csv",
    "pooled_scores": "artifacts/no_refit_revision/results/summary_pooled.csv",
    "intervals": "artifacts/no_refit_revision/results/interval_summary.csv",
    "interval_cases": "artifacts/no_refit_revision/results/intervals_per_case.csv",
}
for _origin in ORIGINS:
    INPUTS["forecast_" + _origin] = (
        f"artifacts/five_cutoff_main_model_synthesis/{_origin}_exal_m_t1/"
        "exdqlm_multivar_synth_keep_focus_render_numeric_contract.csv")

MODEL_NOTE = ("N, AL and exAL denote normal, asymmetric Laplace and extended asymmetric "
              "Laplace likelihoods; U and M denote one and multiple observation sources. "
              "T1 retains the transfer contribution at forecast leads and T0 omits it.")
SCALE_NOTE = r"Scores use $\log(1+x)$ discharge, with $x$ in m$^3$/s."


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iso(value: str) -> str:
    return date.fromisoformat(value).strftime("%Y%m%d") if "-" in value else date.fromisoformat(
        f"{value[:4]}-{value[4:6]}-{value[6:8]}").strftime("%Y%m%d")


def number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Nonfinite numerical input: {value!r}")
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def keyed(rows, key, expected=None, name="input"):
    result = {}
    for row in rows:
        k = key(row)
        require(k not in result, f"Duplicate {name} key: {k}")
        result[k] = row
    if expected is not None:
        require(set(result) == set(expected),
                f"Incorrect {name} keys: missing={set(expected)-set(result)}, extra={set(result)-set(expected)}")
    return result


def model_horizon_keys():
    return {(m, h) for m in METHODS for h in (28, 8) if (m, h) != ("RAW-NWS", 28)}


def load(root: Path):
    """Load and validate every required scientific key before rendering outputs."""
    raw = {name: (root / rel).read_bytes() for name, rel in INPUTS.items()}
    data = {name: list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))
            for name, blob in raw.items()}
    mh = model_horizon_keys()
    aggregate = keyed(data["aggregate"], lambda r: (r["model"], int(r["horizon_days"])), mh, "aggregate")
    origins = keyed(data["origin_scores"], lambda r: (iso(r["cutoff_date"]), r["model"], int(r["horizon_days"])),
                    {(o, m, h) for o in ORIGINS for m, h in mh}, "origin score")
    for (m, h), row in aggregate.items():
        require(int(row["n_valid"]) == 5*h and int(row["origins"]) == 5, "Incorrect pooled case count")
        values = [number(origins[o, m, h]["mean_crps"]) for o in ORIGINS]
        require(math.isclose(number(row["mean_crps"]), math.fsum(values)/5, abs_tol=1e-12), "Pooled score differs from origin means")
        require(math.isclose(number(row["crpss"]), 1-number(row["mean_crps"])/number(row["mean_climatology_crps"]), abs_tol=1e-12), "Incorrect pooled skill")
    for (_, _, h), row in origins.items():
        require(int(row["n_valid"]) == h, "Incorrect origin case count")
        for field in ("mean_crps", "mean_climatology_crps", "crpss"):
            number(row[field])
    component_keys = {(o, m, h) for o in ORIGINS for m in COMPONENTS for h in (28, 8)
                      if (m, h) != ("RAW-NWS", 28)}
    components = keyed(data["components"], lambda r: (iso(r["cutoff"]), r["row_label"], int(r["horizon_days"])), component_keys, "component")
    for row in components.values():
        number(row["mean_crps"])
    for (o, m, h), row in components.items():
        reference = "exAL-M-T1" if m == "exAL-M-T1 (full)" else m
        if reference in ("exAL-M-T1", "RAW-GLOFAS", "RAW-NWS"):
            require(math.isclose(number(row["mean_crps"]), number(origins[o, reference, h]["mean_crps"]), abs_tol=1e-12), "Component reference differs from origin scores")
    losses = keyed(data["losses"], lambda r: (iso(r["cutoff"]), r["forecast_date"], r["manuscript_label"], number(r["tau"])),
                   {(o, (date.fromisoformat(f"{o[:4]}-{o[4:6]}-{o[6:8]}")+timedelta(days=d)).isoformat(), m, t)
                    for o in ORIGINS for d in range(1, 29) for m in QUANTILE_METHODS for t in TAUS}, "daily check loss")
    daily_values = defaultdict(list)
    origin_values = defaultdict(list)
    observed = {}
    for (o, target, m, t), row in losses.items():
        require(row["score_scale"] == "log_cms_plus1", "Incorrect check-loss scale")
        v = number(row["check_loss"])
        require(v >= 0, "Negative check loss")
        number(row["predicted_quantile"])
        y = number(row["observed"])
        if (o, target) in observed:
            require(observed[o, target] == y, "Check-loss observations disagree")
        observed[o, target] = y
        daily_values[m, t].append(v)
        origin_values[o, m, t].append(v)
    pooled_losses = {k: math.fsum(v)/len(v) for k, v in daily_values.items()}
    origin_losses = {k: math.fsum(v)/len(v) for k, v in origin_values.items()}
    require(all(len(v) == 140 for v in daily_values.values()), "Incorrect pooled check-loss count")
    require(all(len(v) == 28 for v in origin_values.values()), "Incorrect origin check-loss count")
    for t in TAUS:
        expected = "exAL-M-T1" if t <= .50 else "AL-M-T1"
        require(min(QUANTILE_METHODS, key=lambda m: pooled_losses[m, t]) == expected, "Unexpected pooled loss ordering")
    scores = keyed(data["pooled_scores"], lambda r: (r["score_scale"], r["model_id"], int(r["horizon_days"])),
                   {(s, m, h) for s in ("log1p_cms", "discharge_cms") for m, h in mh}, "exact score")
    for (_, _, h), row in scores.items():
        require(int(row["n_valid_cases"]) == 5*h == int(row["n_expected_cases"]), "Incorrect exact-score count")
        exact = number(row["mean_exact_ecdf_crps"])
        require(math.isclose(number(row["ecdf_crpss"]), 1-exact/number(row["mean_climatology_exact_ecdf_crps"]), abs_tol=1e-10), "Incorrect exact-score skill")
        if row["mean_iid_adjusted_crps"]:
            number(row["mean_iid_adjusted_crps"])
        require(bool(row["adjustment_status"]) and bool(row["representation_kind"]), "Missing adjustment provenance")
    interval_keys = {(s, o, m, h) for s in ("log1p_cms", "discharge_cms") for o in (*ORIGINS, "POOL") for m, h in mh}
    intervals = keyed(data["intervals"], lambda r: (r["score_scale"], "POOL" if r["origin_or_pool"] == "POOL" else iso(r["origin_or_pool"]), r["model_id"], int(r["horizon_days"])), interval_keys, "interval")
    for (_, o, _, h), row in intervals.items():
        n = h * (5 if o == "POOL" else 1)
        require(int(row["n_valid"]) == n == int(row["n_expected"]), "Incorrect interval case count")
        require(sum(int(row[k]) for k in ("n_lower_miss", "n_inside", "n_upper_miss")) == n, "Interval classification mismatch")
        require(math.isclose(number(row["empirical_coverage"]), int(row["n_inside"])/n, abs_tol=1e-14), "Incorrect coverage")
    interval_cases = keyed(data["interval_cases"], lambda r: (r["score_scale"], iso(r["origin_date"]), r["model_id"], r["target_date"]), name="per-case interval")
    focus_cases = {k: r for k, r in interval_cases.items() if k[0] == "log1p_cms" and k[2] == "exAL-M-T1"}
    require(len(focus_cases) == 140, "Incomplete exact forecast interval evidence")
    fits = keyed(data["fits"], lambda r: (r["study"], iso(r["cutoff"]), r["label"], r["quantile"]), name="fit")
    runs = keyed(data["runs"], lambda r: (r["study"], iso(r["cutoff"]), r["label"]), name="run")
    require(len(fits) == 400 and len(runs) == 70, "Incorrect fit/run counts")
    require({k[:3] for k in fits} == set(runs), "Fit/run keys disagree")
    statuses = Counter(r["stopping_status"] for r in fits.values())
    require(statuses == {"converged": 16, "budget_limited": 314, "unknown": 70}, "Incorrect stopping classifications")
    require(all(r["stopping_status"] == "budget_limited" for r in fits.values() if r["label"] == "exAL-M-T1"), "Full-reference stopping evidence changed")
    exceptions = [r for r in fits.values() if r["study"] == "component_removal" and r["stopping_status"] == "converged"]
    require(len(exceptions) == 1 and exceptions[0]["label"] == "exAL-M-T1-noH1" and iso(exceptions[0]["cutoff"]) == ORIGINS[0] and number(exceptions[0]["quantile"]) == 50, "Unexpected converged reduction")
    forecasts = {}
    for o in ORIGINS:
        rows = data["forecast_"+o]
        dates = [date.fromisoformat(r["date"]) for r in rows]
        origin = date.fromisoformat(f"{o[:4]}-{o[4:6]}-{o[6:8]}")
        require(dates == [origin+timedelta(days=i) for i in range(-18, 29)], "Forecast plot dates must retain all 47 archived rows")
        require(Counter(r["segment"] for r in rows) == {"history": 19, "forecast": 28}, "Incorrect forecast plot segments")
        for r in rows:
            require(r["segment"] == ("history" if date.fromisoformat(r["date"]) <= origin else "forecast"), "Forecast plot segment/date mismatch")
            values = [number(r[k]) for k in ("observed", "model_mean", "interval_low", "q05", "q95", "interval_high")]
            require(values[2] <= values[3] <= values[4] <= values[5], "Invalid exact 95% interval")
            if r["segment"] == "forecast":
                exact = focus_cases["log1p_cms", o, "exAL-M-T1", r["date"]]
                require(math.isclose(values[2], number(exact["lower"]), abs_tol=1e-12) and math.isclose(values[5], number(exact["upper"]), abs_tol=1e-12), "Forecast plot must preserve exact 95% endpoints")
        lower = sum(number(r["observed"]) < number(r["interval_low"]) for r in rows if r["segment"] == "forecast")
        upper = sum(number(r["observed"]) > number(r["interval_high"]) for r in rows if r["segment"] == "forecast")
        expected = intervals["log1p_cms", o, "exAL-M-T1", 28]
        require((lower, upper) == (int(expected["n_lower_miss"]), int(expected["n_upper_miss"])), "Forecast plot misses differ from interval summary")
        forecasts[o] = rows
    # Once the presentation is materialized, even scientifically compatible
    # source edits require an explicit new review rather than silent adoption.
    manifest_path = root / ARTIFACT_DIR / "manifest.json"
    if manifest_path.is_file():
        frozen = json.loads(manifest_path.read_text())["source_files"]
        require(set(frozen) == set(INPUTS.values()), "Compact source inventory changed")
        for name, rel in INPUTS.items():
            require(digest(raw[name]) == frozen[rel]["sha256"], f"Archived compact source changed: {rel}")
    return dict(raw=raw, aggregate=aggregate, origins=origins, components=components,
                pooled_losses=pooled_losses, origin_losses=origin_losses, scores=scores,
                intervals=intervals, fits=fits, runs=runs, forecasts=forecasts)


def display(model):
    return DISPLAY.get(model, model)


def fmt(value, bold=False):
    if value is None or value == "":
        return "---"
    v = float(value)
    if v != 0 and abs(v) >= 1e7:
        exponent = int(math.floor(math.log10(abs(v))))
        s = rf"${v/10**exponent:.5f}\times 10^{{{exponent}}}$"
    else:
        s = f"{v:.5f}"
    return rf"\textbf{{{s}}}" if bold else s


def table(caption, label, columns, body, note):
    return ("% Generated by scripts/compact_publication.py; edit the generator.\n"
            "\\begin{table}[!htbp]\n\\centering\n\\begin{threeparttable}\n"
            f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
            "\\setlength{\\tabcolsep}{4pt}\n"
            f"\\begin{{tabular}}{{{columns}}}\n\\hline\n" + body +
            "\\hline\n\\end{tabular}\n\\begin{tablenotes}\\footnotesize\n"
            f"\\item \\textit{{Note:}} {note}\n"
            "\\end{tablenotes}\n\\end{threeparttable}\n\\end{table}\n")


def row(*cells):
    return " & ".join(cells) + r" \\" + "\n"


def panel(horizon, columns, title=None):
    return (f"% horizon_days={horizon}\n" +
            rf"\multicolumn{{{columns}}}{{l}}{{\textit{{{title or str(horizon)+'-day horizon'}}}}} \\" + "\n")


def render_tables(data):
    result = {}
    body = row("Method", "28-day CRPS", "28-day CRPSS", "8-day CRPS", "8-day CRPSS") + "\\hline\n"
    for m in METHODS:
        cells = [display(m)]
        for h in (28, 8):
            r = data["aggregate"].get((m, h))
            cells.extend(fmt(r[k]) if r else "---" for k in ("mean_crps", "crpss"))
        body += row(*cells)
    result["main_aggregate.tex"] = table("Mean forecast CRPS and skill relative to seasonal climatology across five origins.", "tab:external_benchmarks", "lrrrr", body,
        SCALE_NOTE + " CRPS denotes the continuous ranked probability score; lower values are better. CRPSS is one minus the ratio of pooled mean CRPS to the matching climatology mean; higher values are better. Means use 140 daily cases at leads 1--28 and 40 at leads 1--8. NWS has eight daily leads. Scores use quantile-grid integration. " + MODEL_NOTE)
    body = row("Method", *(f"${t:.2f}$" for t in TAUS)) + "\\hline\n"
    for m in QUANTILE_METHODS:
        body += row(m, *(fmt(data["pooled_losses"][m, t], data["pooled_losses"][m, t] == min(data["pooled_losses"][n, t] for n in QUANTILE_METHODS)) for t in TAUS))
    result["main_quantile_loss.tex"] = table("Mean daily quantile check loss pooled over five 28-day forecast windows.", "tab:quantile_check_loss_pooled", "lrrrrrrr", body,
        "Columns are target probabilities; each entry averages 140 archived daily losses. Lower values are better; bold marks the minimum in each column. " + SCALE_NOTE + " " + MODEL_NOTE)
    body = row("Method", r"\multicolumn{3}{c}{28 days}", r"\multicolumn{3}{c}{8 days}")
    body += row("", "Covered", "Width", "Interval score", "Covered", "Width", "Interval score") + "\\hline\n"
    for m in ("exAL-M-T1", "AL-M-T1", "exAL-U-T1", "AL-U-T1", "RAW-GLOFAS", "RAW-NWS", "CLIM-SEASONAL", "PERSISTENCE", "EMOS-GLOFAS"):
        cells = [display(m)]
        for h in (28, 8):
            r = data["intervals"].get(("log1p_cms", "POOL", m, h))
            cells.extend([f"{r['n_inside']}/{r['n_valid']}", fmt(r["mean_width"]), fmt(r["mean_interval_score"])] if r else ["---"]*3)
        body += row(*cells)
    result["main_calibration.tex"] = table("Coverage, mean width and mean interval score of central 95\\% observation predictive intervals.", "tab:no_refit_calibration", "lrrrrrr", body,
        "Covered is the number of observations within the closed 2.5th--97.5th percentile interval divided by the case count. Width and interval score are averaged on the $\\log(1+x)$ scale, with discharge $x$ in m$^3$/s; lower interval score is better. Persistence has zero width. Numerical quantile conventions are specified in Appendix~\\ref{app:numericalprediction}. The monotone inverse transformation preserves coverage. " + MODEL_NOTE)
    body = row("Method", *ORIGIN_LABELS) + "\\hline\n"
    for h in (28, 8):
        body += panel(h, 6)
        for m in METHODS:
            if (m, h) == ("RAW-NWS", 28):
                continue
            body += row(display(m), *(fmt(data["origins"][o, m, h]["mean_crps"]) for o in ORIGINS))
        if h == 28:
            body += "\\hline\n"
    result["si_origin_crps.tex"] = table("Mean quantile-grid CRPS by forecast origin and horizon.", "tab:crps_all_origins", "lrrrrr", body,
        SCALE_NOTE + " Each entry averages the stated number of daily leads; lower is better. Origins are January 23, November 12 and December 21, 2021, and May 11 and December 25, 2022. NWS has only eight daily leads. " + MODEL_NOTE)
    body = row("Method", *ORIGIN_LABELS) + "\\hline\n"
    for h in (28, 8):
        body += panel(h, 6)
        for m in COMPONENTS:
            if (m, h) == ("RAW-NWS", 28):
                continue
            body += row(display(m), *(fmt(data["components"][o, m, h]["mean_crps"]) for o in ORIGINS))
        if h == 28:
            body += "\\hline\n"
    result["si_component_comparison.tex"] = table("Mean CRPS for the full exAL-M-T1 model and component-removal comparisons.", "tab:component_comparison", "lrrrrr", body,
        SCALE_NOTE + " Scores use quantile-grid integration and the five origins listed in Table~\\ref{tab:crps_all_origins}. Suffixes noTrend, noTF and noH1--noH3 remove the trend, transfer component and respective harmonic blocks. Structural removal of the transfer component differs from T0, which omits its forecast contribution. GloFAS and NWS are uncorrected references; NWS has eight leads. Lower scores are better. Recorded stopping evidence is reported in Table~\\ref{tab:fitting_status}.")
    groups = [
        ("Three normal configurations", set(METHODS[:3])),
        ("Two univariate quantile configurations", {"AL-U-T1", "exAL-U-T1"}),
        ("Four multivariate quantile configurations", {"AL-M-T0", "AL-M-T1", "exAL-M-T0", "exAL-M-T1"}),
        ("noH1 component removal", {"exAL-M-T1-noH1"}),
        ("Other four component removals", {"exAL-M-T1-noTrend", "exAL-M-noTF", "exAL-M-T1-noH2", "exAL-M-T1-noH3"}),
    ]
    body = row("Configuration group", "Runs", "Fits", "Converged", "Limit", "Unrecorded") + "\\hline\n"
    counts = []
    for name, members in groups:
        f = [r for r in data["fits"].values() if r["label"] in members]
        n = sum(r["label"] in members for r in data["runs"].values())
        c = Counter(r["stopping_status"] for r in f)
        numbers = (n, len(f), c["converged"], c["budget_limited"], c["unknown"])
        counts.append(numbers)
        body += row(name, *(str(x) for x in numbers))
    require(tuple(sum(x[i] for x in counts) for i in range(5)) == (70, 400, 16, 314, 70), "Fitting groups must cover every fit exactly once")
    require(counts == [(15, 15, 15, 0, 0), (10, 70, 0, 0, 70), (20, 140, 0, 140, 0),
                       (5, 35, 1, 34, 0), (20, 140, 0, 140, 0)], "Fitting group classifications changed")
    body += "\\hline\n" + row("Total", "70", "400", "16", "314", "70")
    result["si_fitting_status.tex"] = table("Recorded stopping classifications for the comparison fits.", "tab:fitting_status", "lrrrrr", body,
        "Normal configurations are N-U-T1, N-M-T0 and N-M-T1; univariate quantile configurations are AL-U-T1 and exAL-U-T1; multivariate quantile configurations are AL-M-T0/T1 and exAL-M-T0/T1. Other removals are noTrend, noTF, noH2 and noH3. Converged means the recorded criteria were satisfied; Limit means the iteration limit was reached with criteria unmet. Unrecorded is insufficient stopping evidence, rather than demonstrated failure. The only converged removal is the January 23, 2021 median noH1 fit; all 35 full-reference exAL-M-T1 quantile fits reached their limits. Three AL-M-T0 runs have terminal held updates. These classifications do not establish model adequacy.")
    body = row("Method", *(f"${t:.2f}$" for t in TAUS)) + "\\hline\n"
    for o in ORIGINS:
        d = date.fromisoformat(f"{o[:4]}-{o[4:6]}-{o[6:8]}")
        body += f"% Origin {d:%m/%d/%Y}\n" + rf"\multicolumn{{8}}{{l}}{{\textit{{{d:%B %d, %Y}}}}} \\" + "\n"
        for m in QUANTILE_METHODS:
            body += row(m, *(fmt(data["origin_losses"][o, m, t]) for t in TAUS))
    result["si_quantile_loss.tex"] = table("Mean daily quantile check loss by forecast origin and probability.", "tab:quantile_check_loss", "lrrrrrrr", body,
        "Each entry averages 28 archived daily losses at the column probability. Lower values are better. " + SCALE_NOTE + " " + MODEL_NOTE)
    body = row("Method", "Exact CRPS", "CRPSS", "Adjusted CRPS") + "\\hline\n"
    for h in (28, 8):
        body += panel(h, 4)
        for m in METHODS:
            if (m, h) == ("RAW-NWS", 28):
                continue
            r = data["scores"]["log1p_cms", m, h]
            body += row(display(m), *(fmt(r[k]) for k in ("mean_exact_ecdf_crps", "ecdf_crpss", "mean_iid_adjusted_crps")))
        if h == 28:
            body += "\\hline\n"
    result["si_exact_score_sensitivity.tex"] = table("Exact empirical-distribution scores and independent-draw sensitivity.", "tab:exact_score_sensitivity", "lrrr", body,
        SCALE_NOTE + " Exact CRPS gives equal weight to each predictive sample or grid value; CRPSS uses the matching exact climatology score. Means pool 140 or 40 cases. Adjusted CRPS applies the pairwise correction for independent, identically distributed predictive draws. Independence of physical ensemble members is a sensitivity assumption. Counts are 2,000 for AL/exAL, 64 for N-U-T1, 48 for N-M-T0/T1, 51 for GloFAS and seven for NWS. The adjustment is inapplicable to deterministic climatology and EMOS grids and to persistence; dashes denote this inapplicability. Adjusted skill is not reported. " + MODEL_NOTE)
    body = row("Method", "28-day CRPS", "28-day CRPSS", "8-day CRPS", "8-day CRPSS") + "\\hline\n"
    for m in METHODS:
        cells = [display(m)]
        for h in (28, 8):
            r = data["scores"].get(("discharge_cms", m, h))
            cells.extend(fmt(r[k]) if r else "---" for k in ("mean_exact_ecdf_crps", "ecdf_crpss"))
        body += row(*cells)
    result["si_discharge_score.tex"] = table("Exact empirical-distribution forecast scores on the discharge scale.", "tab:discharge_scale_scores", "lrrrr", body,
        r"Each predictive value is transformed by $\exp(y)-1$ before scoring; transformed-scale scores are not exponentiated. CRPS is in m$^3$/s and CRPSS is dimensionless. The empirical distribution weights each sample or grid value equally. Skill uses matching seasonal-climatology scores. Means pool 140 or 40 daily cases; NWS has eight leads. " + MODEL_NOTE)
    body = row("Method", *ORIGIN_LABELS) + "\\hline\n"
    for h in (28, 8):
        body += panel(h, 6)
        for m in METHODS:
            if (m, h) == ("RAW-NWS", 28):
                continue
            cells = [display(m)]
            for o in ORIGINS:
                r = data["intervals"]["log1p_cms", o, m, h]
                cells.append(f"{r['n_inside']}/{r['n_valid']}")
            body += row(*cells)
        if h == 28:
            body += "\\hline\n"
    result["si_origin_coverage.tex"] = table("Central 95\\% observation predictive interval coverage by origin and horizon.", "tab:origin_interval_coverage", "lrrrrr", body,
        "Entries count observations within the closed 2.5th--97.5th percentile interval divided by available cases. Origins match Table~\\ref{tab:crps_all_origins}. Limits use type-8 sample quantiles for simulated model values and inverse empirical-distribution quantiles for raw ensembles and deterministic grids. Monotone inverse transformation preserves coverage. Successive daily cases are not treated as independent replicates. " + MODEL_NOTE)
    return {f"{TABLE_DIR}/{name}": text.encode() for name, text in result.items()}


def render_figure(data, origins):
    """Preserve the archived layers and all 47 dates; render no new estimates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 9,
                         "axes.titlesize": 10, "axes.labelsize": 9,
                         "xtick.labelsize": 8, "ytick.labelsize": 8,
                         "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False}):
        fig, axes = plt.subplots(2, 1, figsize=(6.35, 5.3))
        for i, (ax, o) in enumerate(zip(axes, origins)):
            rows = data["forecasts"][o]
            x = [date.fromisoformat(r["date"]) for r in rows]
            origin = date.fromisoformat(f"{o[:4]}-{o[4:6]}-{o[6:8]}")
            ax.fill_between(x, [number(r["interval_low"]) for r in rows],
                            [number(r["interval_high"]) for r in rows],
                            color="#4477AA", alpha=.20, linewidth=0, label="95% predictive interval")
            ax.plot(x, [number(r["model_mean"]) for r in rows], color="#4477AA", linewidth=1.2,
                    linestyle="--", label="Predictive mean")
            ax.plot(x, [number(r["observed"]) for r in rows], color="#222222", linewidth=.85,
                    marker="o", markersize=2.5, label="Observed discharge")
            ax.axvline(origin, color="#AA3377", linestyle=":", linewidth=1.1, label="Forecast origin")
            ax.set_title(f"({chr(97+i)}) {origin:%B %d, %Y}", loc="left", pad=5)
            ax.set_ylabel(r"$\log(1+x)$")
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            ax.set_xlim(x[0], x[-1])
            ax.margins(y=.08)
            ax.grid(axis="y", linewidth=.35, color=".85")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .005),
                   ncol=2, frameon=False, fontsize=8)
        fig.subplots_adjust(left=.11, right=.985, bottom=.15, top=.95, hspace=.45)
        stream = io.BytesIO()
        fig.savefig(stream, format="pdf", metadata={"Creator": "compact_publication.py",
                    "CreationDate": None, "ModDate": None, "Title": "exAL-M-T1 predictive synthesis"})
        plt.close(fig)
        return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def generate(root: Path):
    data = load(root)
    outputs = render_tables(data)
    outputs["Figures/manuscript/compact_forecasts_2021_early.pdf"] = render_figure(data, ORIGINS[:2])
    outputs["Figures/manuscript/compact_forecasts_2021_2022.pdf"] = render_figure(data, ORIGINS[2:4])
    records = {
        "main_aggregate": [{"method": m, "horizon_days": h, **r} for (m, h), r in sorted(data["aggregate"].items())],
        "pooled_quantile_loss": [{"method": m, "tau": t, "n_cases": 140, "mean_check_loss": v} for (m, t), v in sorted(data["pooled_losses"].items())],
        "origin_quantile_loss": [{"origin": o, "method": m, "tau": t, "n_cases": 28, "mean_check_loss": v} for (o, m, t), v in sorted(data["origin_losses"].items())],
        "exact_score_provenance": [{**r} for k, r in sorted(data["scores"].items())],
        "forecast_layers": {o: [{k: r[k] for k in ("date", "segment", "observed", "model_mean", "interval_low", "interval_high")} for r in data["forecasts"][o]] for o in ORIGINS[:4]},
    }
    outputs[f"{ARTIFACT_DIR}/scientific_records.json"] = json_bytes(records)
    manifest = {
        "schema_version": 1,
        "generator": "scripts/compact_publication.py",
        "generator_sha256": digest((ROOT / "scripts/compact_publication.py").read_bytes()),
        "command": "python3 scripts/compact_publication.py",
        "check_command": "python3 scripts/compact_publication.py --check",
        "scope": "Presentation of archived summaries; no fits, predictive-cache reads, new draws or forecast scoring.",
        "source_files": {rel: {"sha256": digest(data["raw"][name]), "rows": len(list(csv.DictReader(io.StringIO(data["raw"][name].decode("utf-8-sig")))))} for name, rel in INPUTS.items()},
        "outputs": {rel: {"sha256": digest(blob)} for rel, blob in outputs.items()},
        "key_counts": {"aggregate_method_horizon": 27, "origin_method_horizon": 135, "component_origin_horizon": 75,
                       "daily_check_loss": 3920, "pooled_quantile_loss": 28, "origin_quantile_loss": 140,
                       "exact_score_scale_method_horizon": 54, "interval_scale_origin_method_horizon": 324,
                       "fits": 400, "runs": 70, "forecast_rows_per_origin": 47},
        "plot_contract": {"supporting_origins": list(ORIGINS[:4]), "historical_rows": 19, "forecast_rows": 28,
                          "layers": ["observed", "model_mean", "interval_low", "interval_high"],
                          "interval": "2.5th--97.5th percentile, from exact archived focus-render endpoints",
                          "forecast_misses": [1, 0, 7, 0], "independent_panel_y_scales": True},
    }
    outputs[f"{ARTIFACT_DIR}/manifest.json"] = json_bytes(manifest)
    return outputs


def run(root: Path, check=False):
    outputs = generate(root)
    changed = [rel for rel, blob in outputs.items() if not (root/rel).is_file() or (root/rel).read_bytes() != blob]
    if check:
        require(not changed, "Stale compact publication outputs: " + ", ".join(changed))
    else:
        # Validation and rendering have both succeeded before any promotion.
        staged = []
        try:
            for rel, blob in outputs.items():
                target = root/rel
                target.parent.mkdir(parents=True, exist_ok=True)
                handle, temp = tempfile.mkstemp(prefix=".compact-", dir=target.parent)
                with os.fdopen(handle, "wb") as stream:
                    stream.write(blob)
                staged.append((Path(temp), target))
            for temp, target in staged:
                os.replace(temp, target)
        finally:
            for temp, _ in staged:
                temp.unlink(missing_ok=True)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="Validate and compare without writing")
    args = parser.parse_args()
    changed = run(args.root.resolve(), args.check)
    print("Compact publication outputs verified." if args.check else f"Rendered {len(changed)} changed compact publication outputs.")


if __name__ == "__main__":
    main()
