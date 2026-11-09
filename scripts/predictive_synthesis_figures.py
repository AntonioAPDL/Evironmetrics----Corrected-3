#!/usr/bin/env python3
"""Render three publication figures from bounded, archived display inputs only.

The portable adapters retain their existing log1p_cms values. No model fitting,
forecasting, sampling, scoring, or predictive-cache access occurs. ``--check``
renders in temporary space and compares the complete published outputs without
writing the article tree. A write validates all inputs and both independent
exports before promoting any of the three PDFs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, timedelta
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = "artifacts/predictive_synthesis_figures"
ORIGINS = ("20210123", "20211112", "20211221", "20220511", "20221225")
TRACES = (1, 221, 442, 662, 882, 1119, 1339, 1559, 1780, 2000)
OUTPUTS = tuple("Figures/manuscript/" + name for name in (
    "predictive_synthesis_2022_12_25.pdf", "compact_forecasts_2021_early.pdf",
    "compact_forecasts_2021_2022.pdf"))
CONFIG = "config/predictive_synthesis_figures.yaml"
WRAPPER = "scripts/render_predictive_synthesis_figures.R"
FROZEN_RENDERER = "artifacts/comment1_figure_revision/renderer_sources/R/unified/post_publication_figures.R"
FROZEN_RENDERER_SHA = "e6c45ef094aabe8cb4cdd996a2ce849b968da5a25b588d5a97c9c5820ae1e155"


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(root, rel):
    """Reject absolute/traversing paths and symlinks escaping the article."""
    path = Path(rel)
    require(not path.is_absolute() and ".." not in path.parts, f"Nonlocal display input: {rel}")
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root.resolve()), f"Nonlocal display input: {rel}")
    return resolved


def rows(blob):
    return list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))


def finite(value):
    n = float(value)
    require(math.isfinite(n), "Nonfinite display value")
    return n


def dates_for(origin, first, last):
    d = date.fromisoformat(f"{origin[:4]}-{origin[4:6]}-{origin[6:]}")
    return [(d + timedelta(days=i)).isoformat() for i in range(first, last + 1)]


def validate_summary(data, origin):
    require([r["date"] for r in data] == dates_for(origin, -18, 28), "Incomplete or misordered 47-day summary")
    require(Counter(r["segment"] for r in data) == {"history": 19, "forecast": 28}, "Incorrect summary segments")
    require({r["model_id"] for r in data} == {"exdqlm_multivar_synth_keep"}, "Incorrect model summary")
    for i, r in enumerate(data):
        require(r["segment"] == ("history" if i < 19 else "forecast"), "Summary segment/date mismatch")
        v = {k: finite(r[k]) for k in ("observed", "model_mean", "interval_low", "interval_high", "q05", "q95")}
        require(v["interval_low"] <= v["q05"] <= v["q95"] <= v["interval_high"], "Exact 95% endpoints invalid")
    return data


def validate_samples(data, origin):
    groups = {}
    for r in data:
        require(r["model_id"] == "exdqlm_multivar_synth_keep", "Incorrect sample model")
        index = int(r["sample_index"])
        key = (r["segment"], index)
        group = groups.setdefault(key, {})
        require(r["date"] not in group, "Duplicate sample/date key")
        group[r["date"]] = finite(r["value"])
    indices = sorted({k[1] for k in groups})
    require(len(indices) == 128 and len(data) == 128 * 47, "Incomplete archived sample subset")
    require(set(TRACES).issubset(indices), "Missing selected predictive trace")
    for index in indices:
        for segment, first, last in (("history", -18, 0), ("forecast", 1, 28)):
            require(set(groups.get((segment, index), {})) == set(dates_for(origin, first, last)), "Incomplete sample segment dates")
    return groups


def validate_adapter(data, origin, role):
    require(bool(data), "Empty source-product adapter")
    if role == "retros":
        require(tuple(data[0]) == ("Date", "USGS", "GloFAS", "NWS3.0"), "Retrospective columns changed")
        require([r["Date"] for r in data] == dates_for(origin, -18, 0), "Retrospective dates incomplete")
    else:
        expected = [f"member_{i:02d}" for i in (range(51) if role == "glofas" else range(1, 8))]
        require(tuple(data[0]) == ("target_date", *expected), "Source member columns changed")
        require([r["target_date"] for r in data] == dates_for(origin, 1, 28 if role == "glofas" else 8), "Source forecast dates incomplete")
    for r in data:
        for k, v in r.items():
            if k not in ("Date", "target_date"):
                finite(v)
    return data


def check_ownership(root):
    path = root / "artifacts/compact_publication/manifest.json"
    if path.is_file():
        manifest = json.loads(path.read_text())
        owned = manifest.get("outputs", manifest.get("generated_files", {}))
        if isinstance(owned, list):
            owned = [v if isinstance(v, str) else v.get("path", "") for v in owned]
        require(not set(owned).intersection(OUTPUTS), "Overlapping figure output ownership")


def load(root):
    """Validate pinned original summaries, portable adapters and expected structure."""
    root = Path(root).resolve()
    pinpath = f"{BUNDLE}/inputs_manifest.json"
    pins = json.loads(local_path(root, pinpath).read_text())
    require(pins["schema"] == "predictive_synthesis_inputs_v1", "Unexpected input manifest")
    source_files = {}
    def read(rel):
        blob = local_path(root, rel).read_bytes()
        source_files[rel] = {"sha256": digest(blob), "bytes": len(blob)}
        return blob
    read(pinpath)
    cfg = json.loads(read(CONFIG))  # JSON is valid YAML; avoids a Python YAML dependency.
    require(tuple(cfg["selected_sample_indices"]) == TRACES, "Trace selection changed")
    require(cfg["primary_y_limits"] == [-.1, 6.5] and cfg["may_detail_y_limits"] == [0, 1.3], "Reviewed display scales changed")
    for rel, expected in pins["archived_inputs"].items():
        require(digest(read(rel)) == expected, f"Archived display input changed: {rel}")
    require(source_files[FROZEN_RENDERER]["sha256"] == FROZEN_RENDERER_SHA, "Frozen panel renderer changed")
    for rel in (WRAPPER, "scripts/predictive_synthesis_figures.py"):
        read(rel)
    registry = json.loads(local_path(root, "artifacts/comment1_figure_revision/registry.json").read_text())
    expected_keys = {(o, role) for o in ORIGINS for role in ("glofas", "nws", "retros")}
    require(Counter((e["origin"], e["role"]) for e in pins["adapters"]) == Counter({k: 1 for k in expected_keys}), "Incorrect portable adapter inventory")
    adapters = {}
    for e in pins["adapters"]:
        origin, role = e["origin"], e["role"]
        require(e["path"] == f"{BUNDLE}/inputs/{origin}/{role}_post_adapter.csv", "Unexpected adapter path")
        require(e["scale"] == "log1p_cms", "Source display scale changed")
        meta = json.loads(local_path(root, f"artifacts/five_cutoff_main_model_synthesis/{origin}_exal_m_t1/source_metadata.json").read_text())
        require(e["run_id"] == meta["run_id"], "Adapter/main-model run mismatch")
        matches = [r for r in registry["numeric_inputs"] if r["source"] == e["original_source"]]
        require(len(matches) == 1 and matches[0]["sha256"] == e["original_sha256"], "Original adapter provenance mismatch")
        require(f'/runs/{meta["run_id"]}/post/inputs/{role}_post_adapter.csv' in e["original_source"], "Adapter source is not selected main-model run")
        blob = read(e["path"])
        require(digest(blob) == e["sha256"], f"Portable source input changed: {e['path']}")
        adapters[origin, role] = validate_adapter(rows(blob), origin, role)
    layer_summary = {}
    for o in ORIGINS:
        prefix = f"artifacts/five_cutoff_main_model_synthesis/{o}_exal_m_t1/"
        summary = validate_summary(rows(local_path(root, prefix + "exdqlm_multivar_synth_keep_focus_render_numeric_contract.csv").read_bytes()), o)
        samples = validate_samples(rows(local_path(root, prefix + "exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv").read_bytes()), o)
        # Adapter USGS is a separate copy of the same nineteen historical observations.
        require(all(math.isclose(finite(r["observed"]), finite(a["USGS"]), abs_tol=1e-12) for r, a in zip(summary[:19], adapters[o, "retros"])), "Historical observations disagree across display inputs")
        plotted = [finite(r[k]) for r in summary for k in ("observed", "model_mean", "interval_low", "interval_high")]
        plotted.extend(v for segment in ("history", "forecast") for i in TRACES for v in samples[segment, i].values())
        plotted.extend(finite(v) for role in ("glofas", "nws", "retros") for r in adapters[o, role] for k, v in r.items() if k not in ("Date", "target_date"))
        limits = cfg["primary_y_limits"]
        require(limits[0] <= min(plotted) and max(plotted) <= limits[1], "Common display limits truncate a plotted value")
        if o == "20220511":
            require(cfg["may_detail_y_limits"][0] <= min(plotted) and max(plotted) <= cfg["may_detail_y_limits"][1], "May detail limits truncate a plotted value")
        layer_summary[o] = {"summary_rows": len(summary), "sample_rows": sum(len(samples[s, i]) for s in ("history", "forecast") for i in TRACES), "sample_groups": 20}
    check_ownership(root)
    return {"source_files": source_files, "config": cfg, "layers": layer_summary}


def normalize_pdf(blob):
    """Normalize only Cairo's documented volatile fixed-width metadata value."""
    pattern = rb"/CreationDate \(D:\d{14}Z\)"
    matches = re.findall(pattern, blob)
    require(len(matches) == 1, "Expected exactly one Cairo CreationDate")
    replacement = b"/CreationDate (D:20000101000000Z)"
    require(len(matches[0]) == len(replacement), "Unexpected Cairo timestamp width")
    return re.sub(pattern, replacement, blob)


def font_report(path):
    result = subprocess.run(["pdffonts", str(path)], check=True, capture_output=True, text=True).stdout
    lines = [line for line in result.splitlines()[2:] if line.strip()]
    require(bool(lines), "PDF has no reported embedded fonts")
    for line in lines:
        # Poppler's final columns are: emb, sub, uni, object ID.
        fields = line.split()
        require(fields[-5] == "yes", f"Unembedded PDF font: {line}")
    return result


def render(root, directory, state):
    env = dict(os.environ, TZ="UTC", LC_ALL="C.UTF-8", LANG="C.UTF-8", PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(["Rscript", str(root / WRAPPER), str(root), str(directory)], env=env, capture_output=True, text=True)
    (directory / "renderer.log").write_text(result.stdout + result.stderr)
    require(result.returncode == 0, f"Figure renderer failed: {result.stdout}\n{result.stderr}")
    audit = json.loads((directory / "render_audit.json").read_text())
    output = {}
    pdf_fonts = {}
    for rel in OUTPUTS:
        p = directory / Path(rel).name
        blob = normalize_pdf(p.read_bytes())
        p.write_bytes(blob)
        require(blob.startswith(b"%PDF-"), "Invalid PDF export")
        fonts = font_report(p)
        (directory / (p.stem + "_fonts.txt")).write_text(fonts)
        pdf_fonts[rel] = [" ".join(line.split()) for line in fonts.splitlines()[2:] if line.strip()]
        output[rel] = blob
    require(set(audit["layers"]) == set(ORIGINS), "Missing rendered origin")
    for origin, record in audit["layers"].items():
        require(record["summary_rows"] == 47 and record["history_rows"] == 19 and record["forecast_rows"] == 28, "Renderer lost summary dates")
        require(record["sample_rows"] == 470 and record["sample_groups"] == 20 and tuple(record["selected_sample_indices"]) == TRACES, "Renderer changed predictive traces")
        require(record["built_mean_and_exact_interval_verified"] and record["built_sample_rows"] == 470 and record["built_sample_groups"] == 20, "Actual plotted layers differ from saved values")
        require(record["glofas_rows"] == 28 * 51 and record["nws_rows"] == 8 * 7 and record["retrospective_rows"] == 38, "Renderer lost source-product members")
        require((record["mean_source"], record["lower_source"], record["upper_source"]) == ("model_mean", "interval_low", "interval_high"), "Renderer changed saved numerical layers")
    audit["pdf_fonts"] = pdf_fonts
    return output, audit


def manifest_for(state, output, audit):
    return {"schema": "predictive_synthesis_figures_v1", "generator": "scripts/predictive_synthesis_figures.py", "source_files": state["source_files"], "outputs": {rel: {"sha256": digest(blob), "bytes": len(blob)} for rel, blob in output.items()}, "environment": audit["environment"], "pdf_fonts": audit["pdf_fonts"], "layers": audit["layers"], "scale": "log1p_cms; saved adapter values are used directly", "reference_guides": [5.20948615, 6.06378521], "primary_y_limits": [-.1, 6.5], "may_detail_y_limits": [0, 1.3], "interval_probabilities": [.025, .975], "sample_grouping": ["segment", "sample_index"], "pdf_export": {"device": "grDevices::cairo_pdf", "font_family": "DejaVu Sans", "fonts": "All PDF fonts embedded; verified with pdffonts", "normalization": state["config"]["pdf_metadata_rule"], "repeatability": "Two independent fresh renders have byte-identical normalized final PDFs"}}


def run(root=ROOT, check=False, output_dir=None):
    root = Path(root).resolve()
    state = load(root)
    before = {rel: local_path(root, rel).read_bytes() for rel in state["source_files"]}
    with tempfile.TemporaryDirectory(prefix="predictive_synthesis_figures_") as tmp:
        first = Path(tmp) / "first"; first.mkdir()
        output, audit = render(root, first, state)
        if not check:
            second = Path(tmp) / "second"; second.mkdir()
            other, other_audit = render(root, second, state)
            require(output == other and audit == other_audit, "Independent figure renders are not byte-identical")
        require(all(local_path(root, rel).read_bytes() == blob for rel, blob in before.items()), "Display input changed while rendering")
        manifest = manifest_for(state, output, audit)
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        if check:
            require(output_dir is None, "--check cannot write an output directory")
            for rel, blob in output.items():
                require((root / rel).read_bytes() == blob, f"Published figure is stale: {rel}")
            require((root / BUNDLE / "manifest.json").read_bytes() == manifest_bytes, "Figure generation manifest is stale")
        else:
            target = Path(output_dir).resolve() if output_dir else root
            # Validate every final byte before beginning the bounded promotion.
            prepared = {}
            for rel, blob in {**output, BUNDLE + "/manifest.json": manifest_bytes}.items():
                p = target / rel; p.parent.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(prefix=".figure-", dir=p.parent)
                with os.fdopen(fd, "wb") as handle: handle.write(blob)
                os.chmod(name, 0o644)
                prepared[p] = Path(name)
            try:
                for p, staged in prepared.items(): os.replace(staged, p)
            finally:
                for staged in prepared.values(): staged.unlink(missing_ok=True)
            if output_dir:
                for p in first.glob("*_fonts.txt"): shutil.copyfile(p, target / p.name)
                shutil.copyfile(first / "renderer.log", target / "renderer.log")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    manifest = run(args.root, args.check, args.output_dir)
    print(json.dumps({"status": "passed", "mode": "check" if args.check else "render", "outputs": manifest["outputs"]}, indent=2))


if __name__ == "__main__":
    main()
