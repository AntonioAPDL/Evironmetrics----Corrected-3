#!/usr/bin/env python3
"""Preflight checks for Wiley manuscript submission requirements.

This script checks the manuscript source for two classes of issues that can
cause the Wiley submission system or editorial office to return a manuscript:
uncited figure/table labels and missing required end-matter statements.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_TEX = ROOT / "wileyNJD-APA.tex"
GENERATED_TABLES = ROOT / "tables" / "generated_tex"

REQUIRED_STATEMENTS = (
    r"\section*{Data Availability Statement}",
    r"\section*{Funding Statement}",
    r"\section*{Conflict of Interest Statement}",
)

LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|pageref|autoref)\{([^}]+)\}")


def active_lines(path: Path) -> list[tuple[int, str]]:
    return [
        (line_no, line)
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if not line.lstrip().startswith("%")
    ]


def collect_tex_files() -> list[Path]:
    return [MAIN_TEX] + sorted(GENERATED_TABLES.glob("*.tex"))


def main() -> int:
    failures: list[str] = []
    text = MAIN_TEX.read_text(encoding="utf-8")

    for statement in REQUIRED_STATEMENTS:
        if statement not in text:
            failures.append(f"missing required statement heading: {statement}")

    labels: list[tuple[str, Path, int]] = []
    refs: set[str] = set()
    for path in collect_tex_files():
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
    print(f"Checked {len(labels)} labels and {len(refs)} references across {len(collect_tex_files())} TeX files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
