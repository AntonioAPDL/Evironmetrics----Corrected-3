#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GRAPHICSDIR_PATTERN = re.compile(r"\{([^{}]+)\}")
INCLUDEGRAPHICS_PATTERN = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}")


def parse_graphicspath(tex: str) -> list[Path]:
    marker = "\\graphicspath"
    marker_idx = tex.find(marker)
    if marker_idx < 0:
        return []
    brace_start = tex.find("{", marker_idx)
    if brace_start < 0:
        return []

    depth = 0
    body_chars: list[str] = []
    for ch in tex[brace_start:]:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        if depth >= 1:
            body_chars.append(ch)

    body = "".join(body_chars)
    return [Path(entry) for entry in GRAPHICSDIR_PATTERN.findall(body)]


def parse_includegraphics(tex: str) -> list[str]:
    return INCLUDEGRAPHICS_PATTERN.findall(tex)


def resolve_include(article_root: Path, tex_path: Path, search_roots: list[Path], ref: str) -> Path | None:
    ref_path = Path(ref)
    direct = (tex_path.parent / ref_path).resolve()
    if direct.exists():
        return direct
    for root in search_roots:
        candidate = (article_root / root / ref_path).resolve()
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate manuscript figure include paths.")
    parser.add_argument(
        "--article-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Article repository root.",
    )
    parser.add_argument(
        "--tex-path",
        type=Path,
        default=Path("wileyNJD-APA.tex"),
        help="TeX manuscript path, relative to article root unless absolute.",
    )
    args = parser.parse_args()

    article_root = args.article_root.resolve()
    tex_path = args.tex_path if args.tex_path.is_absolute() else article_root / args.tex_path
    tex_path = tex_path.resolve()

    content = tex_path.read_text(encoding="utf-8")
    search_roots = parse_graphicspath(content)
    includes = parse_includegraphics(content)

    if not search_roots:
        raise SystemExit("No \\graphicspath definition found in manuscript.")
    if not includes:
        raise SystemExit("No \\includegraphics calls found in manuscript.")

    missing: list[str] = []
    resolved_rows: list[tuple[str, str]] = []
    for ref in includes:
        resolved = resolve_include(article_root, tex_path, search_roots, ref)
        if resolved is None:
            missing.append(ref)
            continue
        resolved_rows.append((ref, str(resolved.relative_to(article_root))))

    if missing:
        print("Missing figure assets:")
        for ref in missing:
            print(f"  - {ref}")
        sys.exit(1)

    print("Validated manuscript figure paths:")
    for ref, resolved in resolved_rows:
        print(f"  - {ref} -> {resolved}")


if __name__ == "__main__":
    main()
