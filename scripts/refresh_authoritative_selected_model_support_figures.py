#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from article_asset_manifest import load_manifest, manifest_path
from article_repo_layout import build_layout
from article_runtime_bindings import binding_as_optional_path, load_runtime_bindings

RENDER_SUPPORT_FILES = [
    "authoritative_usgs_quantile_dynamics_summary.csv",
    "authoritative_usgs_quantile_dynamics_summary.rds",
    "authoritative_component_summary.csv",
    "authoritative_component_summary.rds",
    "authoritative_selected_support_lineage.csv",
    "authoritative_selected_support_manifest.json",
]

FIGURE_UPDATES = {
    "fig:dry_quantile": {
        "filename": "selected_model_quantile_dry_period.png",
        "category": "Selected Model",
        "role": "Selected-model quantile dynamics, 2012-2016 window",
        "note": "Rendered from the same 2022-12-25 selected exAL-M-T1 output authority as the synthesis figure.",
    },
    "fig:rainy_quantile": {
        "filename": "selected_model_quantile_wet_period.png",
        "category": "Selected Model",
        "role": "Selected-model quantile dynamics, 2017-2019 window",
        "note": "Rendered from the same 2022-12-25 selected exAL-M-T1 output authority as the synthesis figure.",
    },
    "fig:80_components": {
        "filename": "selected_model_component_80month.png",
        "category": "Selected Model",
        "role": "Selected-model long-cycle seasonal component summary with dry/wet period overlays",
        "note": "Rendered from the same 2022-12-25 selected exAL-M-T1 output authority using raw state component 6 only; plus/minus-trend variants are analysis-only diagnostics.",
    },
}

ANALYSIS_COMPONENT_REL_DIR = Path("analysis_figures") / "component_evolution"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def stage_required_support(source_output_root: Path, staging_support_dir: Path) -> list[dict[str, str]]:
    staging_support_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for name in RENDER_SUPPORT_FILES:
        src = source_output_root / name
        if not src.exists():
            raise FileNotFoundError(f"Missing authoritative selected support artifact: {src}")
        dst = staging_support_dir / name
        shutil.copy2(src, dst)
        rows.append(
            {
                "filename": name,
                "source_absolute_path": str(src),
                "local_bundle_path": "",
                "sha256": sha256(src),
            }
        )
    return rows


def update_manifest(article_root: Path, support_fig_dir: Path) -> None:
    payload = load_manifest(article_root)
    by_label = {row["label"]: row for row in payload["figures"]}
    for label, spec in FIGURE_UPDATES.items():
        if label not in by_label:
            raise KeyError(f"Missing figure label in manuscript manifest: {label}")
        source_path = support_fig_dir / spec["filename"]
        if not source_path.exists():
            raise FileNotFoundError(f"Missing rendered authoritative support figure: {source_path}")
        rel = source_path.relative_to(article_root)
        row = by_label[label]
        row["category"] = spec["category"]
        row["role"] = spec["role"]
        row["source_path"] = str(rel)
        row["source_class"] = "current_selected_model_representative"
        row["current_model_output_wired"] = True
        row["note"] = spec["note"]
    manifest_path(article_root).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def iter_analysis_component_files(support_dir: Path) -> list[Path]:
    analysis_dir = support_dir / ANALYSIS_COMPONENT_REL_DIR
    if not analysis_dir.exists():
        return []
    return sorted(path for path in analysis_dir.iterdir() if path.is_file())


def write_bundle_docs(bundle_root: Path, support_dir: Path, support_rows: list[dict[str, str]], authority: dict) -> None:
    figures_dir = support_dir / "figures"
    manifest_rows = []
    for row in support_rows:
        manifest_rows.append(
            [
                "external_support_data",
                row["filename"],
                row["source_absolute_path"],
                row["local_bundle_path"],
                row["sha256"],
            ]
        )
    for label, spec in FIGURE_UPDATES.items():
        path = figures_dir / spec["filename"]
        manifest_rows.append(
            [
                label,
                spec["filename"],
                str(path),
                str(path.relative_to(bundle_root.parent.parent)),
                sha256(path),
            ]
        )
    for path in iter_analysis_component_files(support_dir):
        manifest_rows.append(
            [
                "analysis_component",
                path.name,
                str(path),
                str(path.relative_to(bundle_root.parent.parent)),
                sha256(path),
            ]
        )
    with (support_dir / "manifest.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["label", "filename", "source_absolute_path", "local_bundle_path", "sha256"])
        writer.writerows(manifest_rows)
    sums = [f"{row[-1]}  {row[3]}" for row in manifest_rows if row[3]]
    (support_dir / "SHA256SUMS.txt").write_text("\n".join(sorted(sums)) + "\n", encoding="utf-8")
    (support_dir / "README.md").write_text(
        "# Authoritative Selected-Model Support\n\n"
        "This bundle contains compact posterior support artifacts and rendered figures for the representative "
        "`2022-12-25 exAL-M-T1` selected model. These figures are sourced from the same selected-output authority "
        "as the synthesis figure. Figure A1 is article-labeled as the long-cycle seasonal component, with period "
        "approximately 6.81 years, or about 82 months, and is rendered "
        "from raw state component 6 only with dry/wet period overlays. The `analysis_figures/component_evolution/` subfolder is an analysis-only component "
        "gallery rendered from the same support CSVs; it is checksummed here but intentionally not registered as "
        "a manuscript figure family. It also includes samplewise component-6-plus-trend and component-6-minus-trend diagnostics when "
        "the support summary provides those contracts.\n\n"
        "The support bundle is tied to the same current `2022-12-25` selected `exAL-M-T1` output authority "
        "used by the representative synthesis figure.\n\n"
        "The current compact support root rebuilds the fitted quantile-dynamics summaries and component summaries "
        "from retained selected-model `.RData` objects; the previous compact support root is used only to recover "
        "dates and observed USGS values for plotting.\n\n"
        "Large compact support CSV/RDS files are intentionally not persisted in this Overleaf-facing article "
        "repository. The manifest records their external runtime source paths and hashes; the refresh script "
        "stages those files in a temporary directory only while rendering figures.\n\n"
        f"- run id: `{authority.get('run_id', '')}`\n"
        f"- cutoff: `{authority.get('selected_cutoff_date', '')}`\n"
        f"- runtime output root: `{authority.get('runtime_output_root', '')}`\n\n"
        "Refresh entrypoint:\n"
        "- `scripts/refresh_authoritative_selected_model_support_figures.py`\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh representative selected-model support figures from compact workflow exports.")
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workflow-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--authority", type=Path)
    parser.add_argument("--source-output-root", type=Path)
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    workflow_root = args.workflow_root.resolve()
    authority_path = (
        args.authority.resolve()
        if args.authority is not None
        else workflow_root / "docs" / "authoritative_selected_outputs" / "he2_exal_m_t1_representative_20221225.yaml"
    )
    authority_payload = load_yaml(authority_path).get("authority", {})
    if not isinstance(authority_payload, dict):
        raise ValueError(f"authority must be a mapping: {authority_path}")
    bindings = load_runtime_bindings(article_root)
    bound_support_root = binding_as_optional_path(bindings, "exal_m_t1", "selected_support_output_root")
    source_output_root = (
        args.source_output_root.resolve()
        if args.source_output_root is not None
        else bound_support_root if bound_support_root is not None
        else Path(str(authority_payload["runtime_output_root"])).resolve()
    )

    layout = build_layout(article_root)
    layout.ensure_base_dirs()
    bundle_root = layout.representative_selected_model_dir
    support_dir = bundle_root / "authoritative_support"
    figures_dir = support_dir / "figures"
    with tempfile.TemporaryDirectory(prefix="selected_support_render_") as tmp_dir:
        staging_support_dir = Path(tmp_dir) / "authoritative_support"
        support_rows = stage_required_support(source_output_root, staging_support_dir)
        figures_dir.mkdir(parents=True, exist_ok=True)
        run(
            [
                "Rscript",
                "--vanilla",
                str(article_root / "scripts" / "render_authoritative_selected_model_support_figures.R"),
                "--support-dir",
                str(staging_support_dir),
                "--output-dir",
                str(figures_dir),
                "--workflow-root",
                str(workflow_root),
                "--display-flow-scale",
                str(authority_payload.get("figure_scale", "log1p_cms")),
                "--metadata-support-dir",
                str(source_output_root),
            ]
        )
    write_bundle_docs(bundle_root, support_dir, support_rows, authority_payload)
    update_manifest(article_root, figures_dir)
    print("Refreshed authoritative selected-model support figures successfully.")


if __name__ == "__main__":
    main()
