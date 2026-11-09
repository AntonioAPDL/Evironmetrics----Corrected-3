#!/usr/bin/env python3
"""Replay the long-cycle panel from retained summaries; alter its axis label only.

No inference, model objects, or external data are needed. --check renders into
a temporary directory and verifies the tracked artifact without modifying it.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageChops


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-source", type=Path, help="Optionally verify the compact subset against the retained original summary CSV")
    args = parser.parse_args()
    root = args.article_root.resolve()
    inputs = root / "artifacts/editorial_revision/figure_inputs"
    metadata = json.loads((inputs / "long_cycle_source.json").read_text())
    source = inputs / "long_cycle_component.csv.gz"
    if sha(source) != metadata["compressed_sha256"]:
        raise ValueError("Stored component-summary checksum mismatch")
    if hashlib.sha256(gzip.decompress(source.read_bytes())).hexdigest() != metadata["csv_sha256"]:
        raise ValueError("Uncompressed component-summary checksum mismatch")
    if args.verify_source:
        if sha(args.verify_source) != metadata["source_inputs"][0]["sha256"]:
            raise ValueError("Retained original summary checksum mismatch")
        with args.verify_source.open(newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = [row for row in reader if row["quantile"] in metadata["quantiles"]
                    and row["component"] == "6" and row["component_contract"] == "raw_state_component"
                    and row["date"] not in ("NA", "")]
        maximum = max(int(row["time_index"]) for row in rows)
        rows = [row for row in rows if int(row["time_index"]) >= -(-maximum // 10)]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        if buffer.getvalue().encode() != gzip.decompress(source.read_bytes()):
            raise ValueError("Compact subset differs from original summary selection")
        print(f"PASS: all {len(rows)} summary rows match the retained original source exactly")
    renderer = root / "scripts/render_editorial_long_cycle_figure.R"
    original = root / metadata["original_figure"]["path"]
    if sha(original) != metadata["original_figure"]["sha256"]:
        raise ValueError("Original component-panel checksum mismatch")
    target = root / "Figures/manuscript/editorial_long_cycle_component.png"
    manifest = root / "artifacts/editorial_revision/long_cycle_figure_manifest.json"
    with tempfile.TemporaryDirectory(prefix="editorial-long-cycle-") as work:
        out = Path(work)
        subprocess.run(["Rscript", str(renderer), str(source), str(out)], check=True)
        original_replay = out / "original_annotation_replay.png"
        edited = out / target.name
        if sha(original_replay) != metadata["original_figure"]["sha256"]:
            raise ValueError("Renderer does not reproduce the original panel exactly; inspect the rendering environment")
        report = json.loads((out / "render_verification.json").read_text())
        if report["rows"] != metadata["rows"]:
            raise ValueError("Rendered row count differs from retained subset")
        with Image.open(original_replay) as original_image, Image.open(edited) as revised_image:
            before = original_image.convert("RGB")
            after = revised_image.convert("RGB")
            bounds = ImageChops.difference(before, after).getbbox()
            if before.size != after.size or bounds is None or bounds[2] > 150:
                raise ValueError("Raster differences extend beyond the y-axis annotation area")
            report["image_dimensions"] = list(after.size)
            report["changed_pixel_bounds"] = list(bounds)
            report["all_pixels_outside_y_axis_annotation_unchanged"] = True
        report.update({
            "description": "The axis annotation alone changes; original annotation replay is byte-identical to the retained figure.",
            "original_figure_sha256": sha(original), "original_replay_sha256": sha(original_replay),
            "revised_figure_sha256": sha(edited), "summary_csv_sha256": metadata["csv_sha256"],
            "renderer_sha256": sha(renderer),
            "source_metadata_sha256": sha(inputs / "long_cycle_source.json"),
            "revised_figure": str(target.relative_to(root)),
            "replay_command": "python3 -B scripts/editorial_long_cycle_figure.py --check",
        })
        if args.check:
            if sha(target) != sha(edited):
                raise ValueError("Tracked editorial component panel differs from replay")
            if json.loads(manifest.read_text()) != report:
                raise ValueError("Tracked editorial component manifest differs from replay")
            print(f"PASS: {report['rows']} retained summary rows; original image and all plotted layers reproduced exactly")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(edited.read_bytes())
            manifest.write_text(json.dumps(report, indent=2) + "\n")
            print(f"Rendered {target.relative_to(root)} from {report['rows']} retained summary rows")


if __name__ == "__main__":
    main()
