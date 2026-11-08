#!/usr/bin/env python3
from __future__ import annotations

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from article_runtime_bindings import binding_as_path, load_runtime_bindings

EXPECTED_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
ARTICLE_FREEZE_MANIFEST = "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv"


def cutoff_dash(cutoff: str) -> str:
    cutoff = str(cutoff).zfill(8)
    return f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}"


def cutoff_slug(cutoff: str) -> str:
    return f"{str(cutoff).zfill(8)}_exal_m_t1"


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def authoritative_manifest_path(article_root: Path, bindings: dict[str, Any] | None = None) -> Path:
    bindings = bindings or load_runtime_bindings(article_root)
    raw = bindings.get("exal_m_t1", {}).get("authoritative_keep_manifest", "")
    if raw:
        return Path(str(raw)).expanduser().resolve()
    return binding_as_path(bindings, "workflow_root") / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml"


def load_authoritative_payload(article_root: Path) -> dict[str, Any]:
    return read_yaml(authoritative_manifest_path(article_root))


def load_authoritative_five_run_specs(article_root: Path, runtime_root: Path | None = None) -> list[dict[str, str]]:
    freeze_path = article_root / ARTICLE_FREEZE_MANIFEST
    if freeze_path.exists() and runtime_root is None:
        rows: list[dict[str, str]] = []
        with freeze_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            selected = [
                row for row in reader
                if row.get("manuscript_label") == "exAL-M-T1"
                and row.get("family") == "exdqlm_multivar_keep"
            ]
        selected_by_cutoff = {str(row["cutoff"]).zfill(8): row for row in selected}
        observed = [cutoff for cutoff in EXPECTED_CUTOFFS if cutoff in selected_by_cutoff]
        if observed == EXPECTED_CUTOFFS:
            for cutoff in EXPECTED_CUTOFFS:
                row = selected_by_cutoff[cutoff]
                run_id = str(row["run_id"])
                run_root = Path(str(row["run_root"])).expanduser().resolve()
                output_root = run_root / "post" / "outputs" / run_id
                rows.append(
                    {
                        "slug": cutoff_slug(cutoff),
                        "cutoff": cutoff_dash(cutoff),
                        "cutoff_code": cutoff,
                        "published_crps": f"{float(row['crps_exact']):.4f}",
                        "run_id": run_id,
                        "multivar_run_id": run_id,
                        "grid_spec_id": str(row.get("expected_input_bundle_id") or row.get("campaign_lineage") or "current_authority"),
                        "runtime_root": str(run_root.parent.parent if run_root.parent.name == "runs" else run_root.parent),
                        "runtime_run_root": str(run_root),
                        "runtime_output_root": str(output_root),
                        "authoritative_manifest": str(freeze_path),
                        "source_lineage": str(row.get("campaign_lineage") or "he2_publication_freeze"),
                    }
                )
            return rows

    bindings = load_runtime_bindings(article_root)
    payload = read_yaml(authoritative_manifest_path(article_root, bindings))
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    resolved_runtime_root = runtime_root or Path(str(metadata.get("runtime_root") or binding_as_path(bindings, "exal_m_t1", "keep_runtime_root"))).expanduser().resolve()
    rows: list[dict[str, str]] = []
    for winner in payload.get("winners", []):
        cutoff = str(winner["cutoff"]).zfill(8)
        rows.append(
            {
                "slug": cutoff_slug(cutoff),
                "cutoff": cutoff_dash(cutoff),
                "cutoff_code": cutoff,
                "published_crps": f"{float(winner['mean_crps']):.4f}",
                "run_id": str(winner["run_id"]),
                "multivar_run_id": str(winner["run_id"]),
                "grid_spec_id": str(winner["grid_spec_id"]),
                "runtime_root": str(resolved_runtime_root),
                "runtime_run_root": str(resolved_runtime_root / "runs" / str(winner["run_id"])),
                "authoritative_manifest": str(authoritative_manifest_path(article_root, bindings)),
                "source_lineage": "exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner",
            }
        )
    observed = [row["cutoff_code"] for row in rows]
    if observed != EXPECTED_CUTOFFS:
        raise ValueError(f"authoritative exAL-M-T1 cutoffs out of order: {observed}")
    return rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(load_authoritative_five_run_specs(args.article_root.resolve()), indent=2))
