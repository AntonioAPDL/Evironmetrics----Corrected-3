#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Historical workflow checks load this helper by file path, outside scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from manuscript_text_contract import active_tex, included_tex_paths

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
    candidates = [article_root / ref_path, tex_path.parent / ref_path]
    candidates += [article_root / root / ref_path for root in search_roots]
    for candidate in candidates:
        options = [candidate] if candidate.suffix else [candidate.with_suffix(ext) for ext in ('.pdf', '.png', '.jpg', '.jpeg')]
        for option in options:
            path = option.resolve()
            if path.is_file():
                return path
    return None


def resolved_figures(article_root: Path, entry: str = 'wileyNJD-APA.tex') -> list[tuple[str, Path]]:
    root = article_root.resolve()
    paths = included_tex_paths(root, entry)
    search = parse_graphicspath(active_tex(paths[0].read_text(encoding='utf-8')))
    rows: list[tuple[str, Path]] = []
    for path in paths:
        for ref in parse_includegraphics(active_tex(path.read_text(encoding='utf-8'))):
            resolved = resolve_include(root, path, search, ref)
            if resolved is None:
                raise ValueError(f'Missing figure asset: {ref}')
            if not resolved.is_relative_to(root):
                raise ValueError(f'Figure asset escapes article root: {ref}')
            rows.append((ref, resolved))
    return rows


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

    try:
        entry = str(tex_path.relative_to(article_root))
        rows = resolved_figures(article_root, entry)
        if not rows:
            raise ValueError('No active figure includes in selected document')
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    resolved_rows = [(ref, str(path.relative_to(article_root))) for ref, path in rows]

    print("Validated manuscript figure paths:")
    for ref, resolved in resolved_rows:
        print(f"  - {ref} -> {resolved}")


if __name__ == "__main__":
    main()
