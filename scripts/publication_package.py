#!/usr/bin/env python3
"""Validate the single submitted article and its integrated appendices.

PUBLICATION_PACKAGE.json is the active display inventory. The original asset
manifest retains scientific lineage. Only evidence reached by the article's
actual reading graph can satisfy submitted obligations, in its declared scope.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from manuscript_text_contract import (active_tex, included_tex_paths,
                                      publication_checks, publication_segments)
from validate_manuscript_figure_paths import (parse_graphicspath,
                                               parse_includegraphics, resolve_include)

PACKAGE_FILE = 'PUBLICATION_PACKAGE.json'
LABEL_RE = re.compile(r'\\label\s*\{([^}]+)\}')
REF_RE = re.compile(r'\\(?:ref|eqref|pageref|autoref)\s*\{([^}]+)\}')


def read_package(article_root: Path) -> dict:
    package = json.loads((article_root / PACKAGE_FILE).read_text(encoding='utf-8'))
    if package.get('schema_version') != 'publication_package_v2':
        raise ValueError('Unsupported publication package schema')
    if set(package.get('documents', {})) != {'main'}:
        raise ValueError('Publication package must declare exactly one article document')
    if package['documents']['main'].get('entry') != 'wileyNJD-APA.tex':
        raise ValueError('Unexpected main entry; expected wileyNJD-APA.tex')
    if 'cross_document_references' in package:
        raise ValueError('Integrated appendices must use local LaTeX references, not a cross-document registry')
    return package


def safe_path(article_root: Path, relative: str) -> Path:
    root = article_root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Publication asset escapes article root: {relative}')
    if not path.is_file():
        raise FileNotFoundError(f'Missing publication asset: {relative}')
    return path


def _reading_graph(root: Path, entry: str, segments: list[tuple[Path, str]], search: list[Path]) -> dict:
    text = '\n'.join(content for _, content in segments)
    display_paths: dict[str, set[Path]] = {}
    figures: set[Path] = set()
    for path, content in segments:
        for label in LABEL_RE.findall(content):
            if label.startswith('tab:'):
                display_paths.setdefault(label, set()).add(path)
        for ref in parse_includegraphics(content):
            image = resolve_include(root, path, search, ref)
            if image is None:
                raise ValueError(f'Missing figure asset: {ref}')
            if not image.is_relative_to(root):
                raise ValueError(f'Figure asset escapes article root: {ref}')
            figures.add(image)
        for body in re.findall(r'\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}', content, re.S):
            images = {resolve_include(root, path, search, ref) for ref in parse_includegraphics(body)}
            for label in LABEL_RE.findall(body):
                if label.startswith('fig:'):
                    display_paths.setdefault(label, set()).update(p for p in images if p is not None)
    return {'entry': entry, 'tex_paths': {path for path, _ in segments}, 'text': text,
            'figures': figures, 'labels': Counter(LABEL_RE.findall(text)),
            'references': set(REF_RE.findall(text)), 'display_paths': display_paths}


def document_graphs(article_root: Path, package: dict | None = None) -> dict[str, dict]:
    """Return the physical article graph with distinct body/appendix ownership."""
    root = article_root.resolve()
    package = package or read_package(root)
    entry = package['documents']['main']['entry']
    segments = publication_segments(root)
    search = parse_graphicspath(active_tex((root / entry).read_text(encoding='utf-8')))
    graph = _reading_graph(root, entry, [(path, text) for path, text, _ in segments], search)
    graph['scopes'] = {scope: _reading_graph(root, entry,
                         [(path, text) for path, text, owner in segments if owner == scope], search)
                       for scope in ('main', 'appendix')}
    return {'main': graph}


def submitted_asset_path(article_root: Path, label: str, document: str | None = None,
                         scope: str | None = None) -> Path:
    """Resolve a declared display only in its actual article and logical scope."""
    root = article_root.resolve()
    package = read_package(root)
    matches = [asset for asset in package['submitted_assets']
               if asset['label'] == label and (document is None or asset['document'] == document)
               and (scope is None or asset['scope'] == scope)]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one submitted asset {label} in {document or "article"}/{scope or "all scopes"}')
    return _resolved_asset_path(root, matches[0], document_graphs(root, package))


def _resolved_asset_path(root: Path, asset: dict, graphs: dict[str, dict]) -> Path:
    graph = graphs[asset['document']]['scopes'][asset['scope']]
    label = asset['label']
    path = safe_path(root, asset['path'])
    reachable = graph['tex_paths'] if asset['kind'] == 'table' else graph['figures']
    if path not in reachable or graph['labels'][label] != 1 or path not in graph['display_paths'].get(label, set()):
        raise ValueError(f'Asset {label} is not reachable exactly once in {asset["document"]}/{asset["scope"]}')
    return path


def auxiliary_label_numbers(path: Path) -> dict[str, str]:
    """Read resolved display numbers after a build, never as a TeX input."""
    labels: dict[str, str] = {}
    for label, number in re.findall(r'\\newlabel\{([^}]+)\}\{\{([^{}]+)\}',
                                    path.read_text(encoding='utf-8')):
        if label in labels:
            raise ValueError(f'Duplicate compiled label: {label}')
        labels[label] = number
    return labels


def local_reference_errors(graph: dict, compiled_labels: dict[str, str] | None = None) -> list[str]:
    """Reject undefined references and stale manually numbered supplement links."""
    errors = [f'main: undefined local reference: {label}'
              for label in sorted(graph['references'] - set(graph['labels']))]
    if re.search(r'\bTables?\s*(?:~|\s)\s*S\d+\b|Supporting Information', graph['text'], re.I):
        errors.append('Article contains a stale supplement reference; use a local appendix label')
    if compiled_labels is not None:
        display_refs = {label for label in graph['references'] if label.startswith(('tab:', 'fig:'))}
        errors.extend(f'main: unresolved compiled display reference: {label}'
                      for label in sorted(display_refs - set(compiled_labels)))
    return errors


def validate_package(article_root: Path, scientific: bool = True) -> dict:
    root = article_root.resolve()
    package = read_package(root)
    graphs = document_graphs(root, package)
    errors: list[str] = []
    assets = package.get('submitted_assets', [])
    ids = [item['id'] for item in assets]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate submitted asset IDs')
    by_id = {asset['id']: asset for asset in assets}
    assigned: set[tuple[str, str]] = set()
    for document, declaration in package['documents'].items():
        if 'bibliography' in declaration:
            bib_path = safe_path(root, declaration['bibliography'])
            commands = re.findall(r'\\bibliography\s*\{([^}]+)\}', graphs[document]['text'])
            used = {item.strip() for group in commands for item in group.split(',')}
            if len(commands) != 1 or used != {str(bib_path.relative_to(root).with_suffix(''))}:
                errors.append(f'{document}: exactly one bibliography must match the inventory')
    for asset in assets:
        document, scope = asset['document'], asset.get('scope')
        if document not in graphs:
            errors.append(f'Unknown document for {asset["id"]}: {document}')
            continue
        if scope not in {'main', 'appendix'}:
            errors.append(f'Unknown logical scope for {asset["id"]}: {scope}')
            continue
        if asset['kind'] not in {'table', 'figure'}:
            errors.append(f'Unknown asset kind: {asset["kind"]}')
            continue
        pair = document, asset['label']
        if pair in assigned:
            errors.append(f'Duplicate asset assignment: {pair}')
        assigned.add(pair)
        try:
            _resolved_asset_path(root, asset, graphs)
            for source in asset.get('sources', []):
                safe_path(root, source)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    for document, graph in graphs.items():
        for label, count in graph['labels'].items():
            if count != 1:
                errors.append(f'{document}: duplicate label {label} ({count})')
            if label.startswith(('fig:', 'tab:')):
                if (document, label) not in assigned:
                    errors.append(f'{document}: included display is undeclared: {label}')
                if label not in graph['references']:
                    errors.append(f'{document}: uncited display: {label}')
        errors.extend(local_reference_errors(graph))
        declared_figures = {safe_path(root, asset['path']) for asset in assets
                            if asset['document'] == document and asset['kind'] == 'figure'}
        errors.extend(f'{document}: included undeclared image: {p.relative_to(root)}'
                      for p in sorted(graph['figures'] - declared_figures))
    retained = package.get('retained_evidence', [])
    old = json.loads((root / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text()) if (root / 'MANUSCRIPT_ASSET_MANIFEST.json').exists() else None
    if old is not None:
        expected_ids = {'figure:' + item['label'] for item in old['figures']}
        expected_ids |= {'table:' + label for label in old['tables']}
        actual_ids = [item['id'] for item in retained]
        if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != expected_ids:
            errors.append('Retained evidence must cover every original manifest display exactly once')
    all_reachable = set().union(*(g['tex_paths'] | g['figures'] for g in graphs.values()))
    for item in retained + package.get('additional_retained_evidence', []):
        try:
            path = safe_path(root, item['path'])
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        disposition = item['disposition']
        if disposition not in {'main', 'appendix', 'merged', 'repository'}:
            errors.append(f'Unknown evidence disposition: {item.get("id", item["path"])}')
        if disposition == 'repository' and path in all_reachable:
            errors.append(f'Repository-only evidence is included: {item.get("id", item["path"])}')
        destinations = item.get('publication_assets', [])
        if disposition in {'main', 'appendix', 'merged'} and not destinations:
            errors.append(f'Submitted/merged evidence has no destination: {item.get("id", item["path"])}')
        for destination in destinations:
            if destination not in ids:
                errors.append(f'Unknown evidence destination: {destination}')
            elif disposition in {'main', 'appendix'} and by_id[destination]['scope'] != disposition:
                errors.append(f'Evidence disposition has the wrong logical scope: {destination}')
    if scientific:
        errors.extend(f'{name}: {detail}' for name, ok, detail in publication_checks(root) if not ok)
    return {'passed': not errors, 'errors': errors,
            'documents': {name: {'entry': graph['entry'],
                                'tex_paths': sorted(str(p.relative_to(root)) for p in graph['tex_paths']),
                                'figure_paths': sorted(str(p.relative_to(root)) for p in graph['figures']),
                                'labels': len(graph['labels']),
                                'scope_labels': {scope: len(view['labels']) for scope, view in graph['scopes'].items()}}
                          for name, graph in graphs.items()},
            'submitted_assets': len(assets), 'retained_evidence': len(retained)}


def build_package(article_root: Path, output: Path) -> dict:
    """Build the article and all appendices in one fresh directory with one bibliography."""
    from build_manuscript_review import build
    if output.exists():
        raise ValueError('Package build directory already exists; choose a fresh output')
    report = validate_package(article_root)
    if not report['passed']:
        raise ValueError('\n'.join(report['errors']))
    package = read_package(article_root)
    output.mkdir(parents=True)
    declaration = package['documents']['main']
    main = build(article_root, output / 'main', 'main', declaration['entry'])
    compiled = auxiliary_label_numbers(Path(main['output_directory']) / 'main.aux')
    reference_errors = local_reference_errors(document_graphs(article_root, package)['main'], compiled)
    result = {'passed': main['passed'] and not reference_errors,
              'documents': {'main': main}, 'combined_pages': main['pages'],
              'local_references': {'passed': not reference_errors, 'errors': reference_errors,
                                   'compiled_display_labels': {label: number for label, number in compiled.items()
                                                               if label.startswith(('tab:', 'fig:'))}}}
    (output / 'package_build_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article-root', type=Path, default=Path(__file__).resolve().parents[1])
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--build-dir', '--build-output', dest='build_output', type=Path)
    action.add_argument('--check', action='store_true', help='Validate without writing outputs (the default).')
    args = parser.parse_args()
    try:
        root = args.article_root.resolve()
        result = build_package(root, args.build_output.resolve()) if args.build_output else validate_package(root)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
