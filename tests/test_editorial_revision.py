"""Fail-closed checks for statistical preservation in presentation-only tables."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('editorial_revision', ROOT / 'scripts/editorial_revision.py')
editorial = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(editorial)


class EditorialTableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editorial_tables_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        contract = editorial.load_contract(ROOT)
        paths = [editorial.CONTRACT, editorial.MANIFEST]
        for table in contract['tables']:
            paths.extend([Path(table['source_path']), Path(table['output_path'])])
        for relative in paths:
            dest = self.root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, dest)

    def output(self, name='benchmark_crps_main_table.tex'):
        return self.root / 'tables/editorial_revision' / name

    def replace(self, path, old, new):
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def test_release_has_all_fifteen_files_and_sixteen_labels(self):
        manifest = editorial.validate(self.root)
        self.assertEqual(len(manifest['table_files']), 15)
        self.assertEqual(sum(t['table_count'] for t in manifest['table_files']), 16)
        self.assertEqual(sum(t['numeric_token_count'] for t in manifest['table_files']), 1496)

    def test_check_does_not_write_any_files(self):
        files = list(self.root.rglob('*'))
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files if p.is_file()}
        editorial.validate(self.root)
        after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files if p.is_file()}
        self.assertEqual(before, after)

    def test_statistical_cell_change_rejected_independently_of_inventory(self):
        self.replace(self.output(), '0.13971', '0.23971')
        with self.assertRaisesRegex(ValueError, 'Numerical table payload changed'):
            editorial.validate(self.root)

    def test_coverage_numerator_change_rejected(self):
        self.replace(self.output('no_refit_calibration_summary_table.tex'), '123/140', '124/140')
        with self.assertRaisesRegex(ValueError, 'Numerical table payload changed'):
            editorial.validate(self.root)

    def test_changed_precision_rejected(self):
        self.replace(self.output(), '0.40366', '0.403660')
        with self.assertRaisesRegex(ValueError, 'Numerical table payload changed'):
            editorial.validate(self.root)

    def test_changed_caption_is_stale_even_if_cells_match(self):
        self.replace(self.output(), 'Mean continuous ranked', 'Median continuous ranked')
        with self.assertRaisesRegex(ValueError, 'Stale presentation wording'):
            editorial.validate(self.root)

    def test_undeclared_method_label_rejected(self):
        self.replace(self.output(), '\nGloFAS &', '\nAnother method &')
        with self.assertRaisesRegex(ValueError, 'Table rows, labels or undeclared presentation changed'):
            editorial.validate(self.root)

    def test_table_label_change_rejected(self):
        self.replace(self.output(), 'tab:benchmark_crps_models}', 'tab:another_label}')
        with self.assertRaisesRegex(ValueError, 'Table labels changed'):
            editorial.validate(self.root)

    def test_source_hash_change_rejected_before_generation(self):
        source = self.root / 'tables/generated_tex/benchmark_crps_main_table.tex'
        self.replace(source, '0.40366', '0.40367')
        before = {p: p.read_bytes() for p in (self.root / 'tables/editorial_revision').glob('*.tex')}
        with self.assertRaisesRegex(ValueError, 'Source table hash changed'):
            editorial.generate(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_source_wording_change_cannot_silently_refresh_contract(self):
        source = self.root / 'tables/generated_tex/benchmark_crps_main_table.tex'
        source.write_text(source.read_text() + '% another wording\n')
        with self.assertRaisesRegex(ValueError, 'Source table hash changed'):
            editorial.generate(self.root)

    def test_stale_inventory_rejected(self):
        path = self.root / editorial.MANIFEST
        manifest = json.loads(path.read_text())
        manifest['table_files'][0]['output_sha256'] = '0' * 64
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Presentation inventory differs'):
            editorial.validate(self.root)

    def test_generator_is_reproducible_and_preserves_sources(self):
        sources = {p: p.read_bytes() for p in (self.root / 'tables/generated_tex').glob('*.tex')}
        expected = {p: p.read_bytes() for p in (self.root / 'tables/editorial_revision').glob('*.tex')}
        self.output().unlink()
        editorial.generate(self.root)
        self.assertEqual(expected, {p: p.read_bytes() for p in expected})
        self.assertEqual(sources, {p: p.read_bytes() for p in sources})

    def test_unexpected_output_path_rejected(self):
        path = self.root / editorial.CONTRACT
        contract = json.loads(path.read_text())
        contract['tables'][0]['output_path'] = 'tables/generated_tex/benchmark_crps_main_table.tex'
        path.write_text(json.dumps(contract))
        with self.assertRaisesRegex(ValueError, 'Unexpected presentation-table path'):
            editorial.generate(self.root)

    def test_explicit_substitution_cannot_match_changed_source_silently(self):
        path = self.root / editorial.CONTRACT
        contract = json.loads(path.read_text())
        contract['tables'][0]['edits'][0]['expected_occurrences'] = 2
        path.write_text(json.dumps(contract))
        with self.assertRaisesRegex(ValueError, 'Explicit wording fragment count changed'):
            editorial.generate(self.root)


if __name__ == '__main__':
    unittest.main()
