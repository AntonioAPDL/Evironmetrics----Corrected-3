#!/usr/bin/env python3
"""Reproduce table presentation without changing validated statistical entries.

The explicit source contract pins the pre-edit table bytes and every permitted
wording substitution. This command never fits, samples, or scores a model.
Default invocation writes only the presentation tables and their inventory;
--check is read-only and rejects stale output, altered source, or altered cells.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path('artifacts/editorial_revision/table_source_contract.json')
MANIFEST = Path('artifacts/editorial_revision/table_presentation_manifest.json')
BASELINE = 'd60d7652a56d7f151f49087bf44c476315427f96'
TABLE_NAMES = (
    'benchmark_crps_main_table.tex',
    'benchmark_crps_nws_horizon_table.tex',
    'comment2_external_comparison_table.tex',
    'he4_quantile_check_loss_main_table.tex',
    'no_refit_score_comparison_table.tex',
    'no_refit_calibration_summary_table.tex',
    'representative_covariate_effects_table.tex',
    'he3_ablation_crps_main_table.tex',
    'he3_ablation_crps_nws_horizon_table.tex',
    'comment2_fit_diagnostic_table.tex',
    'comment2_external_by_origin_table.tex',
    'no_refit_score_sensitivity_table.tex',
    'no_refit_origin_diagnostics_table.tex',
    'appendix_gamma_summary_table.tex',
    'appendix_sigma_summary_table.tex',
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def tabular_blocks(text: str) -> list[str]:
    """Retain complete table bodies, including row order and formatting."""
    blocks = re.findall(
        r'\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}', text, re.S
    )
    if not blocks:
        raise ValueError('Missing tabular environment')
    return blocks


def numeric_tokens(blocks: list[str]) -> list[str]:
    # This independent comparison includes signs, precision, exponents, counts,
    # date labels and numerical TeX arguments, rather than rounding cell values.
    return re.findall(r'[+-]?\d+(?:\.\d+)?', '\n'.join(blocks))


def replace_exact(text: str, edit: dict) -> str:
    count = text.count(edit['old'])
    if count != edit['expected_occurrences']:
        raise ValueError(f"Explicit wording fragment count changed: {edit['old']!r}")
    return text.replace(edit['old'], edit['new'])


def assert_table_preserved(source: str, output: str, edits: list[dict]) -> dict:
    """Check numbers independently, then the entire allowed row presentation."""
    old_blocks, new_blocks = tabular_blocks(source), tabular_blocks(output)
    if len(old_blocks) != len(new_blocks):
        raise ValueError('Table count changed')
    old_numbers, new_numbers = numeric_tokens(old_blocks), numeric_tokens(new_blocks)
    if old_numbers != new_numbers:
        raise ValueError('Numerical table payload changed')
    expected = '\n'.join(old_blocks)
    for edit in edits:
        if edit['scope'] == 'tabular_presentation':
            expected = replace_exact(expected, edit)
    if expected != '\n'.join(new_blocks):
        raise ValueError('Table rows, labels or undeclared presentation changed')
    labels = re.findall(r'\\label\{([^}]+)\}', source)
    if labels != re.findall(r'\\label\{([^}]+)\}', output):
        raise ValueError('Table labels changed')
    return {
        'table_count': len(old_blocks),
        'numeric_token_count': len(old_numbers),
        'numeric_payload_sha256': digest('\n'.join(old_numbers).encode()),
        'labels': labels,
    }


def load_contract(root: Path) -> dict:
    contract = json.loads((root / CONTRACT).read_text())
    if contract.get('schema_version') != 1 or contract.get('baseline_commit') != BASELINE:
        raise ValueError('Unsupported table source contract')
    tables = contract.get('tables', [])
    if [Path(item['source_path']).name for item in tables] != list(TABLE_NAMES):
        raise ValueError('Unexpected source-table set or order')
    for item in tables:
        name = Path(item['source_path']).name
        if item['source_path'] != 'tables/generated_tex/' + name:
            raise ValueError('Unexpected source-table path')
        if item['output_path'] != 'tables/editorial_revision/' + name:
            raise ValueError('Unexpected presentation-table path')
        if any(edit.get('scope') not in ('outside_tabular', 'tabular_presentation')
               for edit in item['edits']):
            raise ValueError('Unknown wording-edit scope')
    return contract


def render(root: Path) -> tuple[dict[str, bytes], dict]:
    contract = load_contract(root)
    outputs, inventory = {}, []
    for item in contract['tables']:
        source_bytes = (root / item['source_path']).read_bytes()
        if digest(source_bytes) != item['source_sha256']:
            raise ValueError(f"Source table hash changed: {item['source_path']}")
        source = source_bytes.decode('utf-8')
        output = source
        for edit in item['edits']:
            output = replace_exact(output, edit)
        proof = assert_table_preserved(source, output, item['edits'])
        content = output.encode('utf-8')
        outputs[item['output_path']] = content
        inventory.append({
            'source_path': item['source_path'],
            'source_sha256': item['source_sha256'],
            'output_path': item['output_path'],
            'output_sha256': digest(content),
            **proof,
        })
    manifest = {
        'schema_version': 1,
        'source_contract_path': str(CONTRACT),
        'source_contract_sha256': digest((root / CONTRACT).read_bytes()),
        'source_baseline_commit': BASELINE,
        'preserves_all_statistical_entries': True,
        'table_files': inventory,
    }
    return outputs, manifest


def validate(root: Path) -> dict:
    outputs, manifest = render(root)
    for rel, expected in outputs.items():
        path = root / rel
        if not path.is_file():
            raise ValueError(f'Missing presentation table: {rel}')
        actual = path.read_bytes()
        source_item = next(t for t in load_contract(root)['tables'] if t['output_path'] == rel)
        # Check cells before the full-byte check so a changed number is diagnosed
        # as a statistical preservation failure rather than stale wording.
        assert_table_preserved(
            (root / source_item['source_path']).read_text(),
            actual.decode('utf-8'), source_item['edits'],
        )
        if actual != expected:
            raise ValueError(f'Stale presentation wording: {rel}')
    if json.loads((root / MANIFEST).read_text()) != manifest:
        raise ValueError('Presentation inventory differs from reproduced tables')
    return manifest


def generate(root: Path) -> dict:
    outputs, manifest = render(root)
    # Source validation and every preservation check finish before any writes.
    for rel, content in outputs.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
    return validate(root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true', help='Validate without writing')
    args = parser.parse_args()
    report = validate(args.root) if args.check else generate(args.root)
    print(json.dumps({'table_files': len(report['table_files']),
                      'labeled_tables': sum(t['table_count'] for t in report['table_files']),
                      'numeric_tokens_preserved': sum(t['numeric_token_count'] for t in report['table_files']),
                      'status': 'PASS'}))


if __name__ == '__main__':
    main()
