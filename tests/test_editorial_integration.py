"""Verify active manuscript dependencies, review hashing and bounded refresh."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_manuscript_review import collect_source_files, sha256
from manuscript_text_contract import included_tex_paths
import refresh_editorial_revision


class IncludeTraversalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='editorial_include_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_nested_actual_includes_are_traversed_and_comments_ignored(self):
        main = self.write('wileyNJD-APA.tex', r'\input{tables/a}' + '\n% \\input{missing.tex}\n')
        first = self.write('tables/a.tex', r'\include{tables/b.tex}')
        second = self.write('tables/b.tex', 'Second table')
        self.assertEqual(included_tex_paths(self.root), [main, first, second])

    def test_duplicate_and_cyclic_includes_are_visited_once(self):
        main = self.write('wileyNJD-APA.tex', r'\input{a}\input{a}\input{b}')
        first = self.write('a.tex', r'\input{b}')
        second = self.write('b.tex', r'\input{a}')
        self.assertEqual(included_tex_paths(self.root), [main, first, second])

    def test_missing_included_file_fails_closed(self):
        self.write('wileyNJD-APA.tex', r'\input{not_present}')
        with self.assertRaisesRegex(FileNotFoundError, 'Missing manuscript include'):
            included_tex_paths(self.root)

    def test_parent_directory_include_is_rejected(self):
        self.write('wileyNJD-APA.tex', r'\input{../outside}')
        with self.assertRaisesRegex(ValueError, 'escapes article root'):
            included_tex_paths(self.root)

    def test_symlink_outside_root_is_rejected(self):
        self.write('wileyNJD-APA.tex', r'\input{outside_link.tex}')
        with tempfile.TemporaryDirectory(prefix='editorial_external_test_') as outside:
            external = Path(outside) / 'table.tex'
            external.write_text('External content')
            (self.root / 'outside_link.tex').symlink_to(external)
            with self.assertRaisesRegex(ValueError, 'escapes article root'):
                included_tex_paths(self.root)

    def test_review_hash_sources_follow_active_table_not_unused_companion(self):
        self.write('wileyNJD-APA.tex', r'\input{tables/editorial_revision/active}')
        active = self.write('tables/editorial_revision/active.tex', 'A & 0.10 \\\\')
        unused = self.write('tables/generated_tex/unused.tex', 'A & 0.90 \\\\')
        for name in ('wileyNJD-APA.bib', 'WileyNJD-v2.cls', 'WileyNJD-APA.bst'):
            self.write(name, 'Fixture source')
        sources = collect_source_files(self.root)
        self.assertIn(active, sources)
        self.assertNotIn(unused, sources)
        before = {p: sha256(p) for p in sources}
        active.write_text('A & 0.20 \\\\')
        after = {p: sha256(p) for p in sources}
        self.assertNotEqual(before[active], after[active])
        self.assertEqual(len(sources), 5)


class ActiveArticleIntegrationTests(unittest.TestCase):
    def test_all_asset_manifest_tables_are_actually_included(self):
        manifest = json.loads((ROOT / 'MANUSCRIPT_ASSET_MANIFEST.json').read_text())
        paths = {ROOT / item['table_tex_path'] for item in manifest['tables'].values()}
        active = set(included_tex_paths(ROOT))
        self.assertEqual(len(paths), 15)
        self.assertEqual(len(manifest['tables']), 16)
        self.assertTrue(paths.issubset(active))
        self.assertTrue(all(p.parent == ROOT / 'tables/editorial_revision' for p in paths))

    def test_review_hashes_cover_all_actual_included_presentation_files(self):
        active = set(included_tex_paths(ROOT))
        sources = set(collect_source_files(ROOT))
        self.assertTrue(active.issubset(sources))
        presentation = list((ROOT / 'tables/editorial_revision').glob('*.tex'))
        self.assertEqual(len(presentation), 15)
        self.assertTrue(set(presentation).issubset(sources))
        self.assertFalse(any(p.parent == ROOT / 'tables/generated_tex' for p in sources))
        self.assertIn(ROOT / 'Figures/manuscript/editorial_long_cycle_component.png', sources)

    def test_editorial_check_invokes_only_two_bounded_read_only_builders(self):
        commands = refresh_editorial_revision.commands(ROOT, check=True)
        self.assertEqual([Path(cmd[2]).name for cmd in commands],
                         ['editorial_revision.py', 'editorial_long_cycle_figure.py'])
        self.assertTrue(all(cmd[-1] == '--check' for cmd in commands))
        self.assertTrue(all(cmd[1] == '-B' for cmd in commands))
        with patch.object(refresh_editorial_revision.subprocess, 'run') as run:
            refresh_editorial_revision.refresh(ROOT, check=True)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], commands[0])
        self.assertEqual(run.call_args_list[1].args[0], commands[1])
        self.assertTrue(all(call.kwargs == {'cwd': ROOT, 'check': True}
                            for call in run.call_args_list))

    def test_editorial_refresh_stops_after_first_failure(self):
        import subprocess
        with patch.object(refresh_editorial_revision.subprocess, 'run',
                          side_effect=subprocess.CalledProcessError(1, 'table-check')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                refresh_editorial_revision.refresh(ROOT, check=True)
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
