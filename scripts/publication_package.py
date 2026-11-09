#!/usr/bin/env python3
"""Validate the submitted main/SI reading package and its actual dependencies.

PUBLICATION_PACKAGE.json is the active display inventory. The older manuscript
asset manifest remains a record of original evidence and numerical lineage.
A repository-only file cannot satisfy a submitted scientific requirement.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from manuscript_text_contract import active_tex, included_tex_paths, publication_checks
from validate_manuscript_figure_paths import (resolved_figures, parse_graphicspath,
                                               parse_includegraphics, resolve_include)

PACKAGE_FILE = 'PUBLICATION_PACKAGE.json'
LABEL_RE = re.compile(r'\\label\s*\{([^}]+)\}')
REF_RE = re.compile(r'\\(?:ref|eqref|pageref|autoref)\s*\{([^}]+)\}')


def read_package(article_root: Path) -> dict:
    package = json.loads((article_root / PACKAGE_FILE).read_text(encoding='utf-8'))
    if package.get('schema_version') != 'publication_package_v1':
        raise ValueError('Unsupported publication package schema')
    if set(package.get('documents', {})) != {'main', 'si'}:
        raise ValueError('Publication package must declare main and si documents')
    expected_entries = {'main': 'wileyNJD-APA.tex', 'si': 'supporting_information.tex'}
    for document, entry in expected_entries.items():
        if package['documents'][document].get('entry') != entry:
            raise ValueError(f'Unexpected entry for {document}; expected {entry}')
    return package


def safe_path(article_root: Path, relative: str) -> Path:
    root = article_root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Publication asset escapes article root: {relative}')
    if not path.is_file():
        raise FileNotFoundError(f'Missing publication asset: {relative}')
    return path


def document_graphs(article_root: Path, package: dict | None = None) -> dict[str, dict]:
    root = article_root.resolve()
    package = package or read_package(root)
    result: dict[str, dict] = {}
    for document, declaration in package['documents'].items():
        entry = declaration['entry']
        paths = included_tex_paths(root, entry)
        text = '\n'.join(active_tex(p.read_text(encoding='utf-8')) for p in paths)
        search = parse_graphicspath(active_tex(paths[0].read_text(encoding='utf-8')))
        display_paths: dict[str, set[Path]] = {}
        for path in paths:
            content = active_tex(path.read_text(encoding='utf-8'))
            for label in LABEL_RE.findall(content):
                if label.startswith('tab:'):
                    display_paths.setdefault(label, set()).add(path)
            for body in re.findall(r'\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}', content, re.S):
                images = {resolve_include(root, path, search, ref) for ref in parse_includegraphics(body)}
                for label in LABEL_RE.findall(body):
                    if label.startswith('fig:'):
                        display_paths.setdefault(label, set()).update(p for p in images if p is not None)
        result[document] = {'entry': entry, 'tex_paths': set(paths), 'text': text,
                            'figures': {path for _, path in resolved_figures(root, entry)},
                            'labels': Counter(LABEL_RE.findall(text)),
                            'references': set(REF_RE.findall(text)), 'display_paths': display_paths}
    return result


def submitted_asset_path(article_root: Path, label: str, document: str | None = None) -> Path:
    """Resolve one declared display only if it is actually submitted in its root."""
    root = article_root.resolve()
    package = read_package(root)
    matches = [asset for asset in package['submitted_assets']
               if asset['label'] == label and (document is None or asset['document'] == document)]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one submitted asset {label} in {document or "package"}')
    return _resolved_asset_path(root, matches[0], document_graphs(root, package))


def _resolved_asset_path(root: Path, asset: dict, graphs: dict[str, dict]) -> Path:
    graph = graphs[asset['document']]
    label = asset['label']
    path = safe_path(root, asset['path'])
    reachable = graph['tex_paths'] if asset['kind'] == 'table' else graph['figures']
    if path not in reachable or graph['labels'][label] != 1 or path not in graph['display_paths'].get(label, set()):
        raise ValueError(f'Asset {label} is not reachable exactly once in {asset["document"]}')
    return path


def auxiliary_label_numbers(path: Path) -> dict[str, str]:
    """Read resolved numbers after an independent build, never as a TeX input."""
    labels: dict[str, str] = {}
    for label, number in re.findall(r'\\newlabel\{([^}]+)\}\{\{([^{}]+)\}',
                                    path.read_text(encoding='utf-8')):
        if label in labels:
            raise ValueError(f'Duplicate compiled label: {label}')
        labels[label] = number
    return labels


def cross_document_reference_errors(package: dict, graphs: dict,
                                    compiled_labels: dict[str, dict[str, str]] | None = None) -> list[str]:
    """Validate named table numbers statically, then against independent SI aux."""
    errors: list[str] = []
    registry = package.get('cross_document_references', [])
    registered: dict[tuple[str, str], dict] = {}
    literal_references = {document: set(re.findall(r'\bTables?\s*(?:~|\s)\s*(S\d+)\b', graph['text']))
                          for document, graph in graphs.items()}
    for reference in registry:
        source, target = reference['source_document'], reference['target_document']
        number, label = reference['number'], reference['target_label']
        key = source, number
        if key in registered:
            errors.append(f'Duplicate cross-document reference registration: {source}/Table {number}')
        registered[key] = reference
        if (source != 'main' or target != 'si' or reference.get('kind') != 'table'
                or not re.fullmatch(r'S[1-9]\d*', number)):
            errors.append(f'Invalid main-to-SI table registration: {source}/Table {number}')
            continue
        matches = [asset for asset in package['submitted_assets']
                   if asset['document'] == target and asset['kind'] == 'table' and asset['label'] == label]
        if len(matches) != 1 or graphs[target]['labels'][label] != 1:
            errors.append(f'Cross-document Table {number} does not target an existing SI table: {label}')
        if number not in literal_references[source]:
            errors.append(f'Unused cross-document reference registration: {source}/Table {number}')
        if compiled_labels is not None:
            resolved = compiled_labels.get(target, {}).get(label)
            if resolved != number:
                errors.append(f'Cross-document Table {number} resolves to {resolved!r}, not {number}: {label}')
    for document, numbers in literal_references.items():
        for number in sorted(numbers):
            if (document, number) not in registered:
                errors.append(f'Unregistered cross-document reference: {document}/Table {number}')
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
            used = {item.strip() for group in re.findall(r'\\bibliography\s*\{([^}]+)\}',
                                                        graphs[document]['text'])
                    for item in group.split(',')}
            if used != {str(bib_path.relative_to(root).with_suffix(''))}:
                errors.append(f'{document}: bibliography does not match the shared inventory')
    for asset in assets:
        document = asset['document']
        if document not in graphs:
            errors.append(f'Unknown document for {asset["id"]}: {document}')
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
        for missing in sorted(graph['references'] - set(graph['labels'])):
            errors.append(f'{document}: undefined local reference: {missing}')
        declared_figures = {safe_path(root, asset['path']) for asset in assets
                            if asset['document'] == document and asset['kind'] == 'figure'}
        undeclared = graph['figures'] - declared_figures
        errors.extend(f'{document}: included undeclared image: {p.relative_to(root)}' for p in sorted(undeclared))
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
        if item['disposition'] not in {'main', 'si', 'merged', 'repository'}:
            errors.append(f'Unknown evidence disposition: {item.get("id", item["path"])}')
        if item['disposition'] == 'repository' and path in all_reachable:
            errors.append(f'Repository-only evidence is included: {item.get("id", item["path"])}')
        destinations = item.get('publication_assets', [])
        if item['disposition'] in {'main', 'si', 'merged'} and not destinations:
            errors.append(f'Submitted/merged evidence has no destination: {item.get("id", item["path"])}')
        for destination in destinations:
            if destination not in ids:
                errors.append(f'Unknown evidence destination: {destination}')
            elif item['disposition'] in {'main', 'si'} and by_id[destination]['document'] != item['disposition']:
                errors.append(f'Evidence disposition has the wrong document: {destination}')
    errors.extend(cross_document_reference_errors(package, graphs))
    if scientific:
        errors.extend(f'{name}: {detail}' for name, ok, detail in publication_checks(root) if not ok)
    return {'passed': not errors, 'errors': errors,
            'documents': {name: {'entry': graph['entry'],
                                'tex_paths': sorted(str(p.relative_to(root)) for p in graph['tex_paths']),
                                'figure_paths': sorted(str(p.relative_to(root)) for p in graph['figures']),
                                'labels': len(graph['labels'])}
                          for name, graph in graphs.items()},
            'submitted_assets': len(assets), 'retained_evidence': len(retained)}


def build_package(article_root: Path, output: Path) -> dict:
    """Build roots independently into fresh directories; neither can read the other aux."""
    from build_manuscript_review import build
    if output.exists():
        raise ValueError('Package build directory already exists; choose a fresh output')
    report = validate_package(article_root)
    if not report['passed']:
        raise ValueError('\n'.join(report['errors']))
    package = read_package(article_root)
    output.mkdir(parents=True)
    reports = {name: build(article_root, output / name, name, declaration['entry'])
               for name, declaration in package['documents'].items()}
    compiled = {name: auxiliary_label_numbers(Path(report['output_directory']) / f'{name}.aux')
                for name, report in reports.items()}
    reference_errors = cross_document_reference_errors(package, document_graphs(article_root, package), compiled)
    result = {'passed': all(report['passed'] for report in reports.values()) and not reference_errors,
              'documents': reports, 'combined_pages': sum(report['pages'] for report in reports.values()),
              'cross_document_references': {'passed': not reference_errors, 'errors': reference_errors,
                                            'registered_count': len(package.get('cross_document_references', []))}}
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
