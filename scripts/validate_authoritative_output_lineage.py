#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from article_asset_manifest import load_manifest
from article_repo_layout import build_layout

DEFAULT_POSTERIOR_FIGURE_LABELS = [
    "fig:synth1",
    "fig:dry_quantile",
    "fig:rainy_quantile",
    "fig:80_components",
]

DEFAULT_POSTERIOR_TABLE_LABELS = [
    "tab:components_23_31",
    "tab:gamma_sigma_intervals1",
    "tab:gamma_sigma_intervals2",
]

STALE_CORRECTIONS_PATTERNS = [
    "historical regime figures and long-cycle appendix figure are treated as descriptive historical summaries",
    "The historical regime figures and the long-cycle seasonal figure are likewise described as historical summaries",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_csv_list(value: str | None, default: list[str]) -> list[str]:
    if value is None or not value.strip():
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def infer_source(
    article_root: Path,
    source_path: str,
    representative_metadata: dict[str, Any],
    historical_metadata: dict[str, Any],
) -> dict[str, str]:
    source = {
        "source_family": "unknown",
        "source_cutoff": "",
        "source_run_id": "",
        "source_run_root": "",
        "source_note": "",
    }
    rel = Path(source_path)
    parts = rel.parts

    if source_path.startswith("artifacts/representative_selected_model_2022_12_25/"):
        source.update(
            {
                "source_family": "representative_selected_model",
                "source_cutoff": str(representative_metadata.get("cutoff", "")),
                "source_run_id": str(representative_metadata.get("run_id", "")),
                "source_run_root": str(representative_metadata.get("runtime_run_root", "")),
            }
        )
        return source

    if source_path.startswith("artifacts/historical_support_from_current_models/"):
        multivar = historical_metadata.get("multivar_source", {})
        source.update(
            {
                "source_family": "historical_support_from_current_models",
                "source_cutoff": str(multivar.get("cutoff", "")),
                "source_run_id": str(multivar.get("run_id", "")),
                "source_run_root": str(
                    multivar.get("historical_support_render_run_root")
                    or multivar.get("canonical_runtime_run_root")
                    or ""
                ),
                "source_note": str(multivar.get("historical_support_render_generation_mode", "")),
            }
        )
        return source

    if len(parts) >= 3 and parts[0] == "artifacts" and parts[1] == "five_cutoff_setup_support":
        slug = parts[2]
        cutoff = ""
        match = re.match(r"(\d{4})(\d{2})(\d{2})_exal_m_t1", slug)
        if match:
            cutoff = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        source.update(
            {
                "source_family": "five_cutoff_setup_support",
                "source_cutoff": cutoff,
                "source_run_id": "",
                "source_run_root": "",
                "source_note": slug,
            }
        )
        return source

    if len(parts) >= 3 and parts[0] == "artifacts" and parts[1] == "five_cutoff_main_model_synthesis":
        slug = parts[2]
        metadata_path = article_root / "artifacts" / "five_cutoff_main_model_synthesis" / slug / "source_metadata.json"
        metadata = read_json(metadata_path) if metadata_path.exists() else {}
        source.update(
            {
                "source_family": "five_cutoff_main_model_synthesis",
                "source_cutoff": str(metadata.get("cutoff", "")),
                "source_run_id": str(metadata.get("run_id") or metadata.get("multivar_run_id") or ""),
                "source_run_root": str(metadata.get("runtime_run_root", "")),
                "source_note": str(metadata.get("source_lineage", slug)),
            }
        )
        return source

    abs_source = article_root / source_path
    source["source_note"] = str(abs_source if abs_source.exists() else "")
    return source


def validate_corrections_text(corrections_root: Path | None) -> list[dict[str, str]]:
    if corrections_root is None:
        return []
    main_tex = corrections_root / "main.tex"
    if not main_tex.exists():
        return [
            {
                "check": "corrections_text_present",
                "status": "FAIL",
                "detail": f"Missing corrections main.tex at {main_tex}",
            }
        ]
    text = main_tex.read_text(encoding="utf-8")
    rows = []
    for pattern in STALE_CORRECTIONS_PATTERNS:
        rows.append(
            {
                "check": "corrections_text_no_stale_historical_support_claim",
                "status": "FAIL" if pattern in text else "PASS",
                "detail": pattern,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that representative posterior figures/tables resolve to the same "
            "authoritative selected-model output bundle as the manuscript synthesis figure."
        )
    )
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--corrections-root", type=Path)
    parser.add_argument("--posterior-figure-labels", default=",".join(DEFAULT_POSTERIOR_FIGURE_LABELS))
    parser.add_argument("--posterior-table-labels", default=",".join(DEFAULT_POSTERIOR_TABLE_LABELS))
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    layout = build_layout(article_root)
    report_dir = (
        args.report_dir.resolve()
        if args.report_dir is not None
        else layout.manuscript_asset_review_dir / "authoritative_output_lineage"
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(article_root)
    figure_labels = parse_csv_list(args.posterior_figure_labels, DEFAULT_POSTERIOR_FIGURE_LABELS)
    table_labels = parse_csv_list(args.posterior_table_labels, DEFAULT_POSTERIOR_TABLE_LABELS)

    representative_metadata = read_json(layout.representative_selected_model_dir / "bundle_metadata.json")
    historical_metadata_path = layout.historical_support_dir / "bundle_metadata.json"
    historical_metadata = read_json(historical_metadata_path) if historical_metadata_path.exists() else {}

    authoritative = {
        "cutoff": str(representative_metadata.get("cutoff", "")),
        "run_id": str(representative_metadata.get("run_id", "")),
        "run_root": str(representative_metadata.get("runtime_run_root", "")),
        "bundle": str((layout.representative_selected_model_dir / "bundle_metadata.json").relative_to(article_root)),
    }

    rows: list[dict[str, str]] = []
    figures_by_label = {row["label"]: row for row in manifest["figures"]}
    for label in figure_labels:
        fig = figures_by_label.get(label)
        if fig is None:
            rows.append(
                {
                    "object_type": "figure",
                    "label": label,
                    "source_path": "",
                    "source_class": "",
                    "source_family": "",
                    "source_cutoff": "",
                    "source_run_id": "",
                    "authoritative_cutoff": authoritative["cutoff"],
                    "authoritative_run_id": authoritative["run_id"],
                    "status": "FAIL",
                    "detail": "missing from MANUSCRIPT_ASSET_MANIFEST.json",
                }
            )
            continue
        source = infer_source(article_root, fig["source_path"], representative_metadata, historical_metadata)
        same_cutoff = source["source_cutoff"] == authoritative["cutoff"]
        same_run = source["source_run_id"] == authoritative["run_id"]
        representative_class = fig["source_class"] == "current_selected_model_representative"
        if label == "fig:synth1" and source["source_family"] == "five_cutoff_main_model_synthesis":
            status = "PASS" if same_cutoff and bool(source["source_run_id"]) and representative_class else "FAIL"
        else:
            status = "PASS" if same_cutoff and same_run and representative_class else "FAIL"
        detail = []
        if not same_cutoff:
            detail.append("cutoff mismatch")
        if label == "fig:synth1" and source["source_family"] == "five_cutoff_main_model_synthesis":
            if not source["source_run_id"]:
                detail.append("missing five-cutoff source run id")
            else:
                detail.append("accepted five-cutoff synthesis family for representative 2022-12-25 synthesis figure")
        elif not same_run:
            detail.append("run_id mismatch")
        if not representative_class:
            detail.append("source_class is not current_selected_model_representative")
        rows.append(
            {
                "object_type": "figure",
                "label": label,
                "source_path": fig["source_path"],
                "source_class": fig["source_class"],
                **source,
                "authoritative_cutoff": authoritative["cutoff"],
                "authoritative_run_id": authoritative["run_id"],
                "status": status,
                "detail": "; ".join(detail),
            }
        )

    for label in table_labels:
        table = manifest["tables"].get(label)
        if table is None:
            rows.append(
                {
                    "object_type": "table",
                    "label": label,
                    "source_path": "",
                    "source_class": "",
                    "source_family": "",
                    "source_cutoff": "",
                    "source_run_id": "",
                    "authoritative_cutoff": authoritative["cutoff"],
                    "authoritative_run_id": authoritative["run_id"],
                    "status": "FAIL",
                    "detail": "missing from MANUSCRIPT_ASSET_MANIFEST.json",
                }
            )
            continue
        sources = list(table.get("sources", {}).values())
        source_path = sources[0] if sources else ""
        source = infer_source(article_root, source_path, representative_metadata, historical_metadata)
        same_cutoff = source["source_cutoff"] == authoritative["cutoff"]
        same_run = source["source_run_id"] == authoritative["run_id"]
        representative_class = table["source_class"] == "current_selected_model_representative"
        status = "PASS" if same_cutoff and same_run and representative_class else "FAIL"
        detail = []
        if not same_cutoff:
            detail.append("cutoff mismatch")
        if not same_run:
            detail.append("run_id mismatch")
        if not representative_class:
            detail.append("source_class is not current_selected_model_representative")
        rows.append(
            {
                "object_type": "table",
                "label": label,
                "source_path": source_path,
                "source_class": table["source_class"],
                **source,
                "authoritative_cutoff": authoritative["cutoff"],
                "authoritative_run_id": authoritative["run_id"],
                "status": status,
                "detail": "; ".join(detail),
            }
        )

    correction_rows = validate_corrections_text(args.corrections_root.resolve() if args.corrections_root else None)
    overall_pass = all(row["status"] == "PASS" for row in rows) and all(
        row["status"] == "PASS" for row in correction_rows
    )

    csv_path = report_dir / "authoritative_output_lineage_validation.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "object_type",
                "label",
                "source_path",
                "source_class",
                "source_family",
                "source_cutoff",
                "source_run_id",
                "source_run_root",
                "source_note",
                "authoritative_cutoff",
                "authoritative_run_id",
                "status",
                "detail",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    correction_csv_path = report_dir / "corrections_text_lineage_validation.csv"
    with correction_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "status", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(correction_rows)

    md: list[str] = []
    md.append("# Authoritative Output Lineage Validation\n\n")
    md.append("## Authoritative Bundle\n\n")
    md.append(f"- cutoff: `{authoritative['cutoff']}`\n")
    md.append(f"- run_id: `{authoritative['run_id']}`\n")
    md.append(f"- run_root: `{authoritative['run_root']}`\n")
    md.append(f"- bundle metadata: `{authoritative['bundle']}`\n\n")
    md.append("## Posterior Figure/Table Gate\n\n")
    md.append("| Object | Label | Source class | Source cutoff | Source run | Status | Detail |\n")
    md.append("|---|---|---|---|---|---|---|\n")
    for row in rows:
        md.append(
            f"| {row['object_type']} | `{row['label']}` | `{row['source_class']}` | "
            f"`{row['source_cutoff']}` | `{row['source_run_id']}` | `{row['status']}` | {row['detail']} |\n"
        )
    if correction_rows:
        md.append("\n## Corrections Text Gate\n\n")
        md.append("| Check | Status | Detail |\n")
        md.append("|---|---|---|\n")
        for row in correction_rows:
            md.append(f"| `{row['check']}` | `{row['status']}` | {row['detail']} |\n")
    md.append("\n## Result\n\n")
    md.append("`PASS`\n" if overall_pass else "`FAIL`\n")
    md_path = report_dir / "AUTHORITATIVE_OUTPUT_LINEAGE_VALIDATION.md"
    md_path.write_text("".join(md), encoding="utf-8")

    print(md_path)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
