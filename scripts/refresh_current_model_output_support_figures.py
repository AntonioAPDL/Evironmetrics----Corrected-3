#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from article_runtime_bindings import binding_as_path, load_runtime_bindings
from article_repo_layout import build_layout
from exal_m_t1_authoritative import load_authoritative_five_run_specs

DEFAULT_MULTIVAR_SPEC = {
    "slug": "20220511_exal_m_t1",
    "cutoff": "2022-05-11",
    "forecast_start": "2022-05-12",
    "run_id": "multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep",
}

MULTIVAR_SUPPORT_SPEC = {
    "run_id": "multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep_historical_support_replay",
}

UNIVAR_SPEC = {
    "cutoff": "2022-12-25",
    "run_id": "multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar",
    "source_png": "exdqlm_univar_synth_cutoff_window_posterior_samples.png",
}

RENAMES = {
    "All_exal_2012-2016_DISC.png": "historical_summary_dry_period.png",
    "All_exal_2017-2019_DISC.png": "historical_summary_wet_period.png",
    "All_exal_2017-2019_DISC_fullrange.png": "historical_summary_wet_period_fullrange.png",
    "80_component_1991_2022.png": "historical_component_80month.png",
    "posterior_samples_counter_valid.png": "reference_synthesis_univariate.png",
}

HISTORICAL_FIGURES = [
    ("fig:dry_quantile", "historical_summary_dry_period.png", "Dry-period historical summary"),
    ("fig:rainy_quantile", "historical_summary_wet_period.png", "Rainy-period historical summary"),
    ("companion:rainy_quantile_fullrange", "historical_summary_wet_period_fullrange.png", "Wet-period historical summary (0-20 companion range)"),
    ("fig:80_components", "historical_component_80month.png", "Long-cycle component summary"),
]

APPENDIX_FIGURE = ("fig:synth2", "reference_synthesis_univariate.png", "Univariate transfer-active reference synthesis")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def yaml_scalar(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    needle = f"{key}:"
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith(needle):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    return None


def infer_flow_scale_contract(run_root: Path) -> tuple[str, str, str]:
    resolved = run_root / "resolved_config.yaml"
    manifest = run_root / "run_manifest.yaml"
    display_scale = (
        yaml_scalar(resolved, "legacy_post_input_scale")
        or yaml_scalar(resolved, "legacy_fit_input_scale")
        or yaml_scalar(manifest, "to_scale")
        or "log1p_cms"
    )
    internal_scale = (
        yaml_scalar(resolved, "analysis_scale_post_internal")
        or yaml_scalar(resolved, "analysis_scale_fit_internal")
        or display_scale
    )
    source = str(resolved if resolved.exists() else manifest)
    return display_scale, internal_scale, source


def multivar_fit_q_paths(run_root: Path) -> list[Path]:
    return [
        run_root / "fit/exdqlm_multivar/keep/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData",
        run_root / "fit/exdqlm_multivar/keep/q=20/outputs/DISC_variables_20_exAL_synth_DISC.RData",
        run_root / "fit/exdqlm_multivar/keep/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData",
        run_root / "fit/exdqlm_multivar/keep/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData",
        run_root / "fit/exdqlm_multivar/keep/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData",
        run_root / "fit/exdqlm_multivar/keep/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData",
        run_root / "fit/exdqlm_multivar/keep/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData",
    ]


def has_multivar_fit_contract(run_root: Path) -> bool:
    return run_root.exists() and all(path.exists() for path in multivar_fit_q_paths(run_root))


def apply_renames(figures_dir: Path) -> None:
    for src_name, dst_name in RENAMES.items():
        src = figures_dir / src_name
        dst = figures_dir / dst_name
        if src.exists():
            if dst.exists():
                dst.unlink()
            shutil.move(src, dst)


def write_bundle(
    bundle_root: Path,
    canonical_multivar_run_root: Path,
    render_multivar_run_root: Path,
    univar_output_root: Path,
    *,
    multivar_spec: dict[str, str],
    render_generation_mode: str,
    render_scale_contract: dict[str, str],
) -> None:
    figures_dir = bundle_root / "figures"
    rows: list[list[str]] = []
    sums: list[str] = []

    for label, filename, role in HISTORICAL_FIGURES:
        path = figures_dir / filename
        digest = sha256(path)
        rows.append([
            label,
            filename,
            role,
            render_generation_mode,
            str(render_multivar_run_root),
            str(path.relative_to(bundle_root.parent.parent)),
            digest,
        ])
        sums.append(f"{digest}  figures/{filename}")

    label, filename, role = APPENDIX_FIGURE
    path = figures_dir / filename
    digest = sha256(path)
    rows.append([
        label,
        filename,
        role,
        "copied_from_current_univar_output",
        str(univar_output_root / UNIVAR_SPEC["source_png"]),
        str(path.relative_to(bundle_root.parent.parent)),
        digest,
    ])
    sums.append(f"{digest}  figures/{filename}")

    metadata = {
        "multivar_source": {
            "slug": multivar_spec["slug"],
            "cutoff": multivar_spec["cutoff"],
            "run_id": multivar_spec["run_id"],
            "canonical_runtime_run_root": str(canonical_multivar_run_root),
            "historical_support_render_run_root": str(render_multivar_run_root),
            "historical_support_render_generation_mode": render_generation_mode,
            "retained_state_summary_path": str(figures_dir / "cache" / "historical_support_state_summaries.rds"),
            "render_scale_contract": render_scale_contract,
        },
        "univar_source": {
            "cutoff": UNIVAR_SPEC["cutoff"],
            "run_id": UNIVAR_SPEC["run_id"],
            "output_root": str(univar_output_root),
            "copied_png": UNIVAR_SPEC["source_png"],
        },
    }
    (bundle_root / "bundle_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    (bundle_root / "README.md").write_text(
        "# Historical Support From Current Models\n\n"
        "This article-side artifact bundle regenerates the historical-support manuscript figures from corrected current model outputs.\n\n"
        "Sources:\n"
        f"- Canonical completed multivariate run: `{canonical_multivar_run_root}`\n"
        f"- Historical-support render run: `{render_multivar_run_root}`\n"
        f"- Univariate transfer-active reference figure: `{univar_output_root / UNIVAR_SPEC['source_png']}`\n\n"
        "Retained support contract:\n"
        "- `figures/cache/historical_support_state_summaries.rds` preserves the corrected multivariate state summary needed by the renderer after ephemeral fit caches are cleaned from the canonical workflow root.\n\n"
        "Refresh entrypoint:\n"
        "- `scripts/refresh_current_model_output_support_figures.py`\n"
    )

    with (bundle_root / "manifest.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "label",
            "filename",
            "role",
            "generation_mode",
            "source_path",
            "local_bundle_path",
            "sha256",
        ])
        writer.writerows(rows)

    (bundle_root / "SHA256SUMS.txt").write_text("\n".join(sorted(sums)) + "\n")


def refresh_univar_reference_only(
    bundle_root: Path,
    univar_output_root: Path,
    univar_png: Path,
    *,
    manuscript_targets: list[Path] | None = None,
) -> None:
    """Refresh only the appendix/reference univariate synthesis artifact.

    The historical-support bundle intentionally contains both legacy selected
    historical figures and the appendix univariate reference synthesis. The
    univariate figure can be regenerated from the current univariate post
    output without requiring cleaned multivariate state caches to be present.
    """

    figures_dir = bundle_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    label, filename, role = APPENDIX_FIGURE
    target = figures_dir / filename
    shutil.copy2(univar_png, target)
    for manuscript_target in manuscript_targets or []:
        manuscript_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, manuscript_target)
    digest = sha256(target)
    source_path = str(univar_png)
    local_bundle_path = str(target.relative_to(bundle_root.parent.parent))

    manifest_path = bundle_root / "manifest.csv"
    header = [
        "label",
        "filename",
        "role",
        "generation_mode",
        "source_path",
        "local_bundle_path",
        "sha256",
    ]
    rows: list[dict[str, str]] = []
    if manifest_path.exists():
        with manifest_path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
    rows = [row for row in rows if not (row.get("label") == label and row.get("filename") == filename)]
    rows.append({
        "label": label,
        "filename": filename,
        "role": role,
        "generation_mode": "copied_from_current_univar_output",
        "source_path": source_path,
        "local_bundle_path": local_bundle_path,
        "sha256": digest,
    })
    with manifest_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    sums_path = bundle_root / "SHA256SUMS.txt"
    rel_sum = f"figures/{filename}"
    sums = []
    if sums_path.exists():
        sums = [line for line in sums_path.read_text(encoding="utf-8").splitlines() if not line.endswith(f"  {rel_sum}")]
    sums.append(f"{digest}  {rel_sum}")
    sums_path.write_text("\n".join(sorted(sums)) + "\n", encoding="utf-8")

    metadata_path = bundle_root / "bundle_metadata.json"
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["univar_source"] = {
        "cutoff": UNIVAR_SPEC["cutoff"],
        "run_id": UNIVAR_SPEC["run_id"],
        "output_root": str(univar_output_root),
        "copied_png": UNIVAR_SPEC["source_png"],
    }
    metadata["univar_reference_refresh_mode"] = "univar_reference_only"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    multivar_source = metadata.get("multivar_source", {})
    canonical_multivar = multivar_source.get("canonical_runtime_run_root", "not refreshed in univar-only mode")
    render_multivar = multivar_source.get("historical_support_render_run_root", "not refreshed in univar-only mode")
    retained_state_summary = multivar_source.get(
        "retained_state_summary_path",
        str(figures_dir / "cache" / "historical_support_state_summaries.rds"),
    )
    (bundle_root / "README.md").write_text(
        "# Historical Support From Current Models\n\n"
        "This article-side artifact bundle regenerates the historical-support manuscript figures from corrected current model outputs.\n\n"
        "Sources:\n"
        f"- Canonical completed multivariate run: `{canonical_multivar}`\n"
        f"- Historical-support render run: `{render_multivar}`\n"
        f"- Univariate transfer-active reference figure: `{univar_png}`\n\n"
        "Retained support contract:\n"
        f"- `{retained_state_summary}` preserves the corrected multivariate state summary needed by the renderer after ephemeral fit caches are cleaned from the canonical workflow root.\n\n"
        "Refresh entrypoint:\n"
        "- `scripts/refresh_current_model_output_support_figures.py`\n"
        "- For the univariate reference alone, run `scripts/refresh_current_model_output_support_figures.py --univar-only`; this refreshes the frozen support artifact and both manuscript-facing figure aliases.\n",
        encoding="utf-8",
    )


def resolve_multivar_spec(article_root: Path, runtime_root: Path) -> dict[str, str]:
    try:
        selected = next(row for row in load_authoritative_five_run_specs(article_root, runtime_root) if row["cutoff_code"] == "20220511")
        return {
            "slug": selected["slug"],
            "cutoff": selected["cutoff"],
            "forecast_start": "2022-05-12",
            "run_id": selected["run_id"],
        }
    except Exception:
        return dict(DEFAULT_MULTIVAR_SPEC)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh current-model support figures for the revised article.")
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workflow-root", type=Path)
    parser.add_argument(
        "--multivar-runtime-root",
        type=Path,
    )
    parser.add_argument(
        "--multivar-support-run-root",
        type=Path,
    )
    parser.add_argument(
        "--univar-runtime-root",
        type=Path,
    )
    parser.add_argument(
        "--univar-only",
        action="store_true",
        help=(
            "Refresh only the appendix/reference univariate synthesis artifact. "
            "This avoids requiring cleaned multivariate historical-support fit caches."
        ),
    )
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    bindings = load_runtime_bindings(article_root)
    workflow_root = args.workflow_root.resolve() if args.workflow_root is not None else binding_as_path(bindings, "workflow_root")
    multivar_runtime_root = (
        args.multivar_runtime_root.resolve()
        if args.multivar_runtime_root is not None
        else binding_as_path(bindings, "exal_m_t1", "keep_runtime_root")
    )
    multivar_support_run_root = (
        args.multivar_support_run_root.resolve()
        if args.multivar_support_run_root is not None
        else binding_as_path(bindings, "exal_m_t1", "historical_support_replay_run_root")
    )
    univar_runtime_root = (
        args.univar_runtime_root.resolve()
        if args.univar_runtime_root is not None
        else binding_as_path(bindings, "exal_m_t1", "univar_runtime_root")
    )

    layout = build_layout(article_root)
    layout.ensure_base_dirs()
    bundle_root = layout.historical_support_dir
    figures_dir = bundle_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    multivar_spec = resolve_multivar_spec(article_root, multivar_runtime_root)
    canonical_multivar_run_root = multivar_runtime_root / "runs" / multivar_spec["run_id"]
    univar_output_root = (
        univar_runtime_root / "runs" / UNIVAR_SPEC["run_id"] / "post" / "outputs" / UNIVAR_SPEC["run_id"]
    )
    univar_png = univar_output_root / UNIVAR_SPEC["source_png"]
    retained_state_summary = figures_dir / "cache" / "historical_support_state_summaries.rds"

    if not univar_png.exists():
        raise FileNotFoundError(f"Missing univariate source PNG: {univar_png}")

    if args.univar_only:
        label, filename, _ = APPENDIX_FIGURE
        refresh_univar_reference_only(
            bundle_root,
            univar_output_root,
            univar_png,
            manuscript_targets=[
                layout.manuscript_figure_path(label),
                layout.publication_figures_dir / "manuscript" / filename,
            ],
        )
        print("Refreshed current-model univariate reference synthesis successfully.")
        return

    if not canonical_multivar_run_root.exists():
        raise FileNotFoundError(f"Missing multivariate source run: {canonical_multivar_run_root}")

    if has_multivar_fit_contract(canonical_multivar_run_root):
        render_multivar_run_root = canonical_multivar_run_root
        render_generation_mode = "rendered_from_canonical_multivar_run"
        state_summary_arg: Path | None = None
    elif has_multivar_fit_contract(multivar_support_run_root):
        render_multivar_run_root = multivar_support_run_root
        render_generation_mode = "rendered_from_historical_support_replay"
        state_summary_arg = None
    elif retained_state_summary.exists():
        render_multivar_run_root = canonical_multivar_run_root
        render_generation_mode = "rendered_from_retained_state_summary"
        state_summary_arg = retained_state_summary
    else:
        raise FileNotFoundError(
            "Missing both canonical multivariate fit artifacts and the retained support replay/state-summary contract: "
            f"canonical={canonical_multivar_run_root} support={multivar_support_run_root} state_summary={retained_state_summary}"
        )

    display_flow_scale, internal_flow_scale, flow_scale_source = infer_flow_scale_contract(render_multivar_run_root)

    render_cmd = [
        "Rscript",
        str(article_root / "scripts" / "render_current_model_output_support_figures.R"),
        "--workflow-root", str(workflow_root),
        "--run-root", str(render_multivar_run_root),
        "--output-dir", str(figures_dir),
        "--cutoff-date", multivar_spec["cutoff"],
        "--forecast-start-date", multivar_spec["forecast_start"],
        "--display-flow-scale", display_flow_scale,
        "--internal-flow-scale", internal_flow_scale,
    ]
    if state_summary_arg is not None:
        render_cmd.extend(["--state-summary-path", str(state_summary_arg)])
    run(render_cmd)

    shutil.copy2(univar_png, figures_dir / "posterior_samples_counter_valid.png")
    apply_renames(figures_dir)
    write_bundle(
        bundle_root,
        canonical_multivar_run_root,
        render_multivar_run_root,
        univar_output_root,
        multivar_spec=multivar_spec,
        render_generation_mode=render_generation_mode,
        render_scale_contract={
            "display_flow_scale": display_flow_scale,
            "internal_flow_scale": internal_flow_scale,
            "source": flow_scale_source,
        },
    )
    print("Refreshed current-model output support figures successfully.")


if __name__ == "__main__":
    main()
