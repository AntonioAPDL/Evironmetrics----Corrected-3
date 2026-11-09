#!/usr/bin/env python3
"""Preflight checks for Wiley manuscript submission requirements.

This script checks the manuscript source for two classes of issues that can
cause the Wiley submission system or editorial office to return a manuscript:
uncited figure/table labels and missing required end-matter statements. Only
files included by the manuscript are checked; companion fragments are excluded.
"""

from __future__ import annotations

import argparse
from collections import Counter
import re
import sys
from pathlib import Path

from manuscript_text_contract import included_tex_paths


ROOT = Path(__file__).resolve().parents[1]
MAIN_TEX = ROOT / "wileyNJD-APA.tex"

REQUIRED_STATEMENTS = (
    r"\section*{Data Availability Statement}",
    r"\section*{Funding Statement}",
    r"\section*{Conflict of Interest Statement}",
)

LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|pageref|autoref)\s*\{([^}]+)\}")
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


def collect_tex_files(article_root: Path = ROOT, entry: str = 'wileyNJD-APA.tex') -> list[Path]:
    return included_tex_paths(article_root, entry)


def check_document(article_root: Path = ROOT, entry: str = 'wileyNJD-APA.tex',
                   required_statements: bool = True) -> dict:
    root = article_root.resolve()
    failures: list[str] = []
    tex_files = collect_tex_files(root, entry)
    text = '\n'.join(line for path in tex_files for _, line in active_lines(path))
    if required_statements:
        for statement in REQUIRED_STATEMENTS:
            if statement not in text:
                failures.append(f'missing required statement heading: {statement}')
    labels: list[tuple[str, Path, int]] = []
    refs: set[str] = set()
    for path in tex_files:
        for line_no, line in active_lines(path):
            labels.extend((match.group(1), path, line_no) for match in LABEL_RE.finditer(line))
            refs.update(match.group(1) for match in REF_RE.finditer(line))
    counts = Counter(label for label, _, _ in labels)
    for label, count in counts.items():
        if count > 1:
            failures.append(f'duplicate label: {label} ({count})')
    failures.extend(f'undefined local reference: {label}' for label in sorted(refs - set(counts)))
    for label, path, line_no in labels:
        if label.startswith(('fig:', 'tab:')) and label not in refs:
            failures.append(f'uncited {label} defined at {path.relative_to(root)}:{line_no}')
    return {'passed': not failures, 'failures': failures, 'label_count': len(labels),
            'reference_count': len(refs), 'tex_file_count': len(tex_files)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=ROOT)
    parser.add_argument('--entry', default='wileyNJD-APA.tex')
    parser.add_argument('--document', choices=('main',), default='main')
    args = parser.parse_args()
    try:
        report = check_document(args.article_root, args.entry, args.document == 'main')
    except (OSError, ValueError) as exc:
        print(f'Wiley submission preflight failed: {exc}', file=sys.stderr)
        return 1
    if not report['passed']:
        print('Wiley submission preflight failed:', file=sys.stderr)
        for failure in report['failures']:
            print(f'  - {failure}', file=sys.stderr)
        return 1
    print(f'Wiley submission preflight passed ({args.document}).')
    print(f'Checked {report["label_count"]} labels and {report["reference_count"]} references '
          f'across {report["tex_file_count"]} TeX files.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
