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

from manuscript_text_contract import active_tex, included_tex_paths
from validate_manuscript_figure_paths import (
    parse_graphicspath, parse_includegraphics, resolve_include,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_source_files(article: Path, entry: str = "wileyNJD-APA.tex") -> list[Path]:
    """Resolve the active manuscript and its included TeX and figure sources.

    Unused generated fragments cannot stand in for included presentation files.
    Include traversal rejects missing paths and paths outside the article root.
    """
    article = article.resolve()
    tex_paths = included_tex_paths(article, entry)
    sources = tex_paths + [article / name for name in (
        "wileyNJD-APA.bib", "WileyNJD-v2.cls", "WileyNJD-APA.bst"
    )]
    # Include locally supplied class/package dependencies as source inputs too.
    # Standard TeX distribution packages are intentionally outside this inventory.
    pending = list(sources)
    scanned: set[Path] = set()
    while pending:
        local = pending.pop()
        if local in scanned:
            continue
        if not local.is_file():
            raise FileNotFoundError(f"Missing manuscript source: {local}")
        scanned.add(local)
        content = active_tex(local.read_text(encoding="utf-8"))
        for command, group in re.findall(
                r"\\(documentclass|usepackage|RequirePackage|bibliographystyle)(?:\[[^\]]*\])?\{([^}]+)\}", content):
            suffix = '.cls' if command == 'documentclass' else '.bst' if command == 'bibliographystyle' else '.sty'
            for name in group.split(','):
                candidate = (article / (name.strip() + suffix)).resolve()
                if not candidate.is_relative_to(article):
                    raise ValueError('Local package escapes article root')
                if candidate.is_file() and candidate not in sources:
                    sources.append(candidate)
                    pending.append(candidate)
    main_text = active_tex(tex_paths[0].read_text(encoding="utf-8"))
    search = parse_graphicspath(main_text)
    for tex_path in tex_paths:
        tex = active_tex(tex_path.read_text(encoding="utf-8"))
        for ref in parse_includegraphics(tex):
            image_path = resolve_include(article, tex_path, search, ref)
            if image_path is None:
                raise ValueError(f"Unresolved manuscript figure: {ref}")
            if not image_path.is_relative_to(article):
                raise ValueError(f"Manuscript figure escapes article root: {ref}")
            sources.append(image_path)
    return sorted(set(sources))


def recorder_local_sources(article: Path, recorder: Path, output: Path) -> set[Path]:
    """Find repository-local compiler inputs, excluding generated build products."""
    root = article.resolve()
    build_root = output.resolve()
    result: set[Path] = set()
    for line in recorder.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("INPUT "):
            continue
        name = Path(line[6:])
        path = (name if name.is_absolute() else root / name).resolve()
        if path.is_relative_to(root) and not path.is_relative_to(build_root) and path.is_file():
            # These are transient TeX outputs; neither document may depend on
            # a stale auxiliary file in the article checkout.
            if path.suffix in {".aux", ".bbl", ".toc", ".out", ".lof", ".lot"}:
                raise ValueError(f"Build reads a source-checkout auxiliary file: {path}")
            result.add(path)
    return result


def build(article: Path, output: Path, job: str, entry: str = "wileyNJD-APA.tex") -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", job):
        raise ValueError("Job name may contain letters, digits, underscores and hyphens")
    if output.exists():
        raise ValueError("Output directory already exists; choose a fresh review directory")
    sources = collect_source_files(article, entry)
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

    latex = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-recorder", f"-jobname={job}",
             f"-output-directory={output}", entry]
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
    recorded = recorder_local_sources(article, output / f"{job}.fls", output)
    unexpected = sorted(str(path.relative_to(article)) for path in recorded - set(sources))
    after = {str(p.relative_to(article)): sha256(p) for p in sources}
    report = {
        "article_root": str(article), "entry": entry, "output_directory": str(output),
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
        "recorder_local_inputs": sorted(str(p.relative_to(article)) for p in recorded),
        "untracked_local_inputs": unexpected,
        "duplicate_labels": re.findall(r"Label [`\'][^\n]*multiply defined", log),
    }
    report["passed"] = (stable and not unresolved and not report["bibtex_warnings"]
                        and before == after and not unexpected and not report["duplicate_labels"])
    (output / "build_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--jobname", default="comment1_review")
    parser.add_argument("--entry", default="wileyNJD-APA.tex")
    args = parser.parse_args()
    try:
        report = build(args.article_root.resolve(), args.output_dir.resolve(), args.jobname, args.entry)
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
