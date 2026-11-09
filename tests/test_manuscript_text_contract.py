from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from manuscript_text_contract import active_tex, cited_url, has_concepts, has_label, publication_views
from publication_package import (submitted_asset_path, validate_package, document_graphs,
                                 auxiliary_label_numbers, cross_document_reference_errors)
from check_wiley_submission_requirements import check_document


class ManuscriptTextContractTests(unittest.TestCase):
    def test_comments_cannot_satisfy_a_scientific_or_label_check(self) -> None:
        text = 'Active forecast discussion. % CRPS\n% \\label{sec:data}'
        self.assertFalse(has_concepts(text, 'CRPS'))
        self.assertFalse(has_label(text, 'sec:data'))
        self.assertIn(r'95\% predictive', active_tex(r'95\% predictive % stale'))

    def test_repository_url_must_be_direct_or_in_a_cited_entry(self) -> None:
        url = 'https://example.org/software'
        bib = '@misc{used,\nurl={' + url + '}\n}\n@misc{unused,\nurl={https://example.org/unused}\n}'
        self.assertTrue(cited_url(r'Workflow \citep{used}.', bib, url))
        self.assertFalse(cited_url('% \\citep{used}', bib, url))
        self.assertFalse(cited_url(r'Workflow \citep{unused}.', bib, url))


class TwoDocumentContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='publication_scope_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'wileyNJD-APA.tex').write_text(r'Main prose. \label{sec:main}')
        (self.root / 'supporting_information.tex').write_text(
            r'Support. \input{table} \ref{tab:si}')
        (self.root / 'table.tex').write_text(r'Numerical evidence. \label{tab:si}')
        (self.root / 'unused.tex').write_text('Unused critical concept')
        self.package = {'schema_version': 'publication_package_v1',
                        'documents': {'main': {'entry': 'wileyNJD-APA.tex'},
                                      'si': {'entry': 'supporting_information.tex'}},
                        'submitted_assets': [{'id': 'si_table', 'document': 'si',
                                              'kind': 'table', 'label': 'tab:si',
                                              'path': 'table.tex'}],
                        'retained_evidence': []}
        self.save()

    def save(self):
        (self.root / 'PUBLICATION_PACKAGE.json').write_text(json.dumps(self.package))

    def test_si_cannot_supply_main_only_concept_and_unused_file_is_absent(self):
        views = publication_views(self.root)
        self.assertNotIn('Numerical evidence', views['main'])
        self.assertIn('Numerical evidence', views['si'])
        self.assertNotIn('Unused critical concept', views['union'])
        self.assertEqual(submitted_asset_path(self.root, 'tab:si', 'si'), self.root / 'table.tex')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            submitted_asset_path(self.root, 'tab:si', 'main')

    def test_moving_table_to_unused_file_cannot_satisfy_si_requirement(self):
        (self.root / 'supporting_information.tex').write_text('Support without its table.')
        result = validate_package(self.root, scientific=False)
        self.assertFalse(result['passed'])
        self.assertTrue(any('not reachable' in error for error in result['errors']))

    def test_duplicate_and_undefined_labels_fail_in_own_document(self):
        (self.root / 'supporting_information.tex').write_text(
            r'\input{table} \label{tab:si} \ref{tab:si} \ref{sec:main}')
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('duplicate label' in error for error in result['errors']))
        self.assertTrue(any('undefined local reference: sec:main' in error for error in result['errors']))
        check = check_document(self.root, 'supporting_information.tex', required_statements=False)
        self.assertFalse(check['passed'])

    def test_independent_si_does_not_need_main_declarations(self):
        result = check_document(self.root, 'supporting_information.tex', required_statements=False)
        self.assertTrue(result['passed'], result['failures'])
        main = check_document(self.root, 'wileyNJD-APA.tex')
        self.assertFalse(main['passed'])

    def test_included_undeclared_display_and_duplicate_assignment_fail(self):
        self.package['submitted_assets'] = []
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('included display is undeclared' in error for error in result['errors']))
        self.package['submitted_assets'] = [{'id': 'x', 'document': 'si', 'kind': 'table',
                                             'label': 'tab:si', 'path': 'table.tex'}] * 2
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('Duplicate submitted asset IDs' in error for error in result['errors']))

    def test_graphics_must_belong_to_the_declared_figure_label(self):
        (self.root / 'one.pdf').write_bytes(b'Figure one')
        (self.root / 'two.pdf').write_bytes(b'Figure two')
        (self.root / 'wileyNJD-APA.tex').write_text(
            r'\begin{figure}\includegraphics{one.pdf}\label{fig:one}\end{figure}'
            r'\begin{figure}\includegraphics{two.pdf}\label{fig:two}\end{figure}'
            r'\ref{fig:one}\ref{fig:two}')
        self.package['submitted_assets'] += [
            {'id': 'one', 'document': 'main', 'kind': 'figure', 'label': 'fig:one', 'path': 'two.pdf'},
            {'id': 'two', 'document': 'main', 'kind': 'figure', 'label': 'fig:two', 'path': 'one.pdf'}]
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertFalse(result['passed'])
        self.assertTrue(any('not reachable exactly once' in error for error in result['errors']))

    def test_repository_only_disposition_cannot_describe_submitted_evidence(self):
        old = {'figures': [], 'tables': {'tab:old': {'table_tex_path': 'table.tex'}}}
        (self.root / 'MANUSCRIPT_ASSET_MANIFEST.json').write_text(json.dumps(old))
        self.package['retained_evidence'] = [
            {'id': 'table:tab:old', 'path': 'table.tex', 'disposition': 'repository', 'publication_assets': []}]
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('Repository-only evidence is included' in error for error in result['errors']))

    def test_unknown_literal_si_table_reference_is_rejected(self):
        (self.root / 'wileyNJD-APA.tex').write_text('See Supporting Information, Table~S99.')
        result = validate_package(self.root, scientific=False)
        self.assertFalse(result['passed'])
        self.assertTrue(any('Unregistered cross-document reference: main/Table S99' in error
                            for error in result['errors']))

    def test_cross_document_table_number_must_match_independently_compiled_label(self):
        (self.root / 'wileyNJD-APA.tex').write_text('See Supporting Information, Table~S1.')
        self.package['cross_document_references'] = [
            {'source_document': 'main', 'target_document': 'si', 'kind': 'table',
             'number': 'S1', 'target_label': 'tab:si'}]
        self.save()
        self.assertTrue(validate_package(self.root, scientific=False)['passed'])
        aux = self.root / 'si-proof.aux'
        aux.write_text(r'\newlabel{tab:si}{{S2}{1}{Caption}{table.caption.1}{}}')
        errors = cross_document_reference_errors(
            self.package, document_graphs(self.root), {'si': auxiliary_label_numbers(aux)})
        self.assertTrue(any("Table S1 resolves to 'S2'" in error for error in errors))
        aux.write_text(r'\newlabel{tab:si}{{S1}{1}{Caption}{table.caption.1}{}}')
        self.assertEqual(cross_document_reference_errors(
            self.package, document_graphs(self.root), {'si': auxiliary_label_numbers(aux)}), [])


if __name__ == '__main__':
    unittest.main()
