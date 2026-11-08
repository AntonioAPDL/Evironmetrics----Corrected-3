#!/usr/bin/env python3
"""Preflight checks for Wiley manuscript submission requirements.

This script checks the manuscript source for two classes of issues that can
cause the Wiley submission system or editorial office to return a manuscript:
uncited figure/table labels and missing required end-matter statements. Only
files included by the manuscript are checked; companion fragments are excluded.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_TEX = ROOT / "wileyNJD-APA.tex"

REQUIRED_STATEMENTS = (
    r"\section*{Data Availability Statement}",
    r"\section*{Funding Statement}",
    r"\section*{Conflict of Interest Statement}",
)

LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|pageref|autoref)\{([^}]+)\}")
INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
COMMENT_RE = re.compile(r"(?<!\\)(?:\\\\)*%")


def active_lines(path: Path) -> list[tuple[int, str]]:
    lines = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        comment = COMMENT_RE.search(line)
        active = line[:comment.start()] if comment else line
        if active.strip():
            lines.append((line_no, active))
    return lines


def collect_tex_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    root = ROOT.resolve()

    def visit(path: Path) -> None:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"included TeX file is outside the article: {path}")
        if path in seen:
            return
        if not path.is_file():
            raise ValueError(f"missing included TeX file: {path.relative_to(root)}")
        seen.add(path)
        files.append(path)
        for _, line in active_lines(path):
            for match in INPUT_RE.finditer(line):
                child = root / match.group(1)
                if not child.suffix:
                    child = child.with_suffix(".tex")
                visit(child)

    visit(MAIN_TEX)
    return files


def main() -> int:
    failures: list[str] = []
    text = MAIN_TEX.read_text(encoding="utf-8")

    for statement in REQUIRED_STATEMENTS:
        if statement not in text:
            failures.append(f"missing required statement heading: {statement}")

    labels: list[tuple[str, Path, int]] = []
    refs: set[str] = set()
    try:
        tex_files = collect_tex_files()
    except (OSError, ValueError) as exc:
        print(f"Wiley submission preflight failed: {exc}", file=sys.stderr)
        return 1
    for path in tex_files:
        for line_no, line in active_lines(path):
            labels.extend((match.group(1), path, line_no) for match in LABEL_RE.finditer(line))
            refs.update(match.group(1) for match in REF_RE.finditer(line))

    for label, path, line_no in labels:
        if label.startswith(("fig:", "tab:")) and label not in refs:
            failures.append(f"uncited {label} defined at {path.relative_to(ROOT)}:{line_no}")

    if failures:
        print("Wiley submission preflight failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("Wiley submission preflight passed.")
    print(f"Checked {len(labels)} labels and {len(refs)} references across {len(tex_files)} TeX files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
