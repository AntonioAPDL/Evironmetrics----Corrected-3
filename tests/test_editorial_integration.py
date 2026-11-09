"""Verify active manuscript dependencies, review hashing and bounded refresh."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_manuscript_review import collect_source_files, sha256, recorder_local_sources
from manuscript_text_contract import included_tex_paths
from publication_package import read_package, validate_package, document_graphs
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

    def test_entry_selection_hashes_only_the_chosen_independent_root(self):
        self.write('wileyNJD-APA.tex', r'\input{main_table}')
        main_table = self.write('main_table.tex', 'Main-only numerical result')
        si = self.write('supporting_information.tex', r'\input{si_table}')
        si_table = self.write('si_table.tex', 'SI-only numerical result')
        for name in ('wileyNJD-APA.bib', 'WileyNJD-v2.cls', 'WileyNJD-APA.bst'):
            self.write(name, 'Fixture source')
        sources = collect_source_files(self.root, 'supporting_information.tex')
        self.assertIn(si, sources)
        self.assertIn(si_table, sources)
        self.assertNotIn(main_table, sources)
        self.assertNotIn(self.root / 'wileyNJD-APA.tex', sources)


class RecorderInputTests(unittest.TestCase):
    def test_stale_checkout_auxiliary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'build'
            output.mkdir()
            (root / 'other.aux').write_text('Stale labels')
            recorder = output / 'proof.fls'
            recorder.write_text('INPUT ./other.aux\n')
            with self.assertRaisesRegex(ValueError, 'source-checkout auxiliary'):
                recorder_local_sources(root, recorder, output)

    def test_recorder_distinguishes_build_products_and_local_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / 'build'
            output.mkdir()
            source = root / 'shared.sty'
            source.write_text('Local definitions')
            (output / 'proof.aux').write_text('Generated')
            recorder = output / 'proof.fls'
            recorder.write_text(f'INPUT {source}\nINPUT {output / "proof.aux"}\nINPUT /missing/system.sty\n')
            self.assertEqual(recorder_local_sources(root, recorder, output), {source})


class ActiveArticleIntegrationTests(unittest.TestCase):
    def test_active_package_assets_are_owned_by_their_actual_document(self):
        report = validate_package(ROOT)
        self.assertTrue(report['passed'], report['errors'])
        package = read_package(ROOT)
        graphs = document_graphs(ROOT, package)
        for asset in package['submitted_assets']:
            with self.subTest(asset=asset['id']):
                graph = graphs[asset['document']]
                paths = graph['tex_paths'] if asset['kind'] == 'table' else graph['figures']
                self.assertIn(ROOT / asset['path'], paths)
                self.assertEqual(graph['labels'][asset['label']], 1)

    def test_review_hashes_follow_each_document_not_retained_unused_assets(self):
        package = read_package(ROOT)
        for name, document in package['documents'].items():
            with self.subTest(document=name):
                active = set(included_tex_paths(ROOT, document['entry']))
                sources = set(collect_source_files(ROOT, document['entry']))
                self.assertTrue(active.issubset(sources))
                submitted = {ROOT / asset['path'] for asset in package['submitted_assets']
                             if asset['document'] == name}
                self.assertTrue(submitted.issubset(sources))
                repository_only = {ROOT / item['path'] for item in package['retained_evidence']
                                   if item['disposition'] == 'repository'}
                self.assertFalse(sources & repository_only)
        # Original replay outputs remain available without being mistaken for
        # the displays selected for the current reading package.
        presentation = list((ROOT / 'tables/editorial_revision').glob('*.tex'))
        self.assertEqual(len(presentation), 15)

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
