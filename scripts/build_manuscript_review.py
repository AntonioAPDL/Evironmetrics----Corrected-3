#!/usr/bin/env python3
"""Build the article in a separate directory and record the resolved PDF checks.

No source files or existing review directories are overwritten. Run LaTeX from the
article directory (so local packages resolve correctly) and BibTeX from the build
directory (required by TeX's restricted output policy).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from validate_manuscript_figure_paths import (
    parse_graphicspath, parse_includegraphics, resolve_include,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(article: Path, output: Path, job: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", job):
        raise ValueError("Job name may contain letters, digits, underscores and hyphens")
    if output.exists():
        raise ValueError("Output directory already exists; choose a fresh review directory")
    sources = [article / name for name in (
        "wileyNJD-APA.tex", "wileyNJD-APA.bib", "WileyNJD-v2.cls", "WileyNJD-APA.bst"
    )]
    sources.extend(sorted((article / "tables/generated_tex").glob("*.tex")))
    tex_path = article / "wileyNJD-APA.tex"
    tex = tex_path.read_text(encoding="utf-8")
    search = parse_graphicspath(tex)
    for ref in parse_includegraphics(tex):
        image_path = resolve_include(article, tex_path, search, ref)
        if image_path is None:
            raise ValueError(f"Unresolved manuscript figure: {ref}")
        sources.append(image_path)
    sources = sorted(set(sources))
    before = {str(p.relative_to(article)): sha256(p) for p in sources}
    output.mkdir(parents=True)
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env[key] = "1"
    commands = []

    def run(argv: list[str], cwd: Path, log_name: str) -> str:
        commands.append({"argv": argv, "cwd": str(cwd), "log": log_name})
        proc = subprocess.run(argv, cwd=cwd, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / log_name).write_text(proc.stdout, encoding="utf-8")
        if proc.returncode:
            raise RuntimeError(f"Command failed ({proc.returncode}); see {output / log_name}")
        return proc.stdout

    latex = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-jobname={job}",
             f"-output-directory={output}", "wileyNJD-APA.tex"]
    run(latex, article, "latex-pass-1.stdout.txt")
    env["BIBINPUTS"] = str(article) + os.pathsep + env.get("BIBINPUTS", "")
    env["BSTINPUTS"] = str(article) + os.pathsep + env.get("BSTINPUTS", "")
    bib = run(["bibtex", job], output, "bibtex.stdout.txt")
    previous = sha256(output / f"{job}.aux")
    stable = False
    for number in range(2, 7):
        run(latex, article, f"latex-pass-{number}.stdout.txt")
        current = sha256(output / f"{job}.aux")
        if current == previous:
            stable = True
            break
        previous = current
    log = (output / f"{job}.log").read_text(encoding="utf-8", errors="replace")
    unresolved = re.findall(r"(?:Citation|Reference) [`'][^\n]*undefined|"
                            r"There were undefined (?:references|citations)", log)
    pdf = output / f"{job}.pdf"
    info = run(["pdfinfo", str(pdf)], output, "pdfinfo.txt")
    run(["pdftotext", "-layout", str(pdf), str(output / f"{job}.txt")],
        output, "pdftotext.stdout.txt")
    after = {str(p.relative_to(article)): sha256(p) for p in sources}
    report = {
        "article_root": str(article), "output_directory": str(output),
        "pdf": str(pdf), "pdf_sha256": sha256(pdf),
        "text_sha256": sha256(output / f"{job}.txt"),
        "pages": int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1)),
        "latex_passes": number, "auxiliary_labels_stable": stable,
        "unresolved_citations_or_references": unresolved,
        "bibtex_warnings": [line for line in bib.splitlines() if "Warning--" in line],
        "overfull_horizontal_boxes": len(re.findall(r"Overfull \\hbox", log)),
        "overfull_vertical_boxes": len(re.findall(r"Overfull \\vbox", log)),
        "sources_unchanged_during_build": before == after,
        "source_hashes": after, "commands": commands,
    }
    report["passed"] = (stable and not unresolved and not report["bibtex_warnings"]
                        and before == after)
    (output / "build_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--jobname", default="comment1_review")
    args = parser.parse_args()
    try:
        report = build(args.article_root.resolve(), args.output_dir.resolve(), args.jobname)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({k: report[k] for k in (
        "pdf", "pages", "latex_passes", "auxiliary_labels_stable",
        "unresolved_citations_or_references", "bibtex_warnings",
        "overfull_horizontal_boxes", "overfull_vertical_boxes", "passed"
    )}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
