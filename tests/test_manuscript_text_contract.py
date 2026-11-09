from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from manuscript_text_contract import active_tex, cited_url, has_concepts, has_label, publication_views
from publication_package import (submitted_asset_path, validate_package, document_graphs,
                                 auxiliary_label_numbers, local_reference_errors)
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


class IntegratedAppendixContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='publication_scope_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.main = r'Main prose. \label{sec:main} See Table~\ref{tab:appendix}.'
        self.appendix = r'Appendix details. \input{table} See Section~\ref{sec:main}.'
        self.write_article()
        (self.root / 'table.tex').write_text(r'Numerical evidence. \label{tab:appendix}')
        (self.root / 'unused.tex').write_text('Unused critical concept')
        self.package = {'schema_version': 'publication_package_v2',
                        'documents': {'main': {'entry': 'wileyNJD-APA.tex'}},
                        'submitted_assets': [{'id': 'appendix_table', 'document': 'main',
                                              'scope': 'appendix', 'kind': 'table',
                                              'label': 'tab:appendix', 'path': 'table.tex'}],
                        'retained_evidence': []}
        self.save()

    def write_article(self):
        (self.root / 'wileyNJD-APA.tex').write_text(
            self.main + '\n' + r'\begin{appendix}\input{appendices}\end{appendix}')
        (self.root / 'appendices.tex').write_text(self.appendix)

    def save(self):
        (self.root / 'PUBLICATION_PACKAGE.json').write_text(json.dumps(self.package))

    def test_appendix_cannot_supply_main_concept_and_unused_file_is_absent(self):
        from manuscript_text_contract import publication_checks
        views = publication_views(self.root)
        self.assertNotIn('Numerical evidence', views['main'])
        self.assertIn('Numerical evidence', views['appendix'])
        self.assertNotIn('Unused critical concept', views['union'])
        self.assertEqual(submitted_asset_path(self.root, 'tab:appendix', 'main', 'appendix'),
                         self.root / 'table.tex')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            submitted_asset_path(self.root, 'tab:appendix', 'main', 'main')
        self.appendix += ' CRPS, quantile check loss; lower is better.'
        self.write_article()
        checks = {name: ok for name, ok, _ in publication_checks(self.root)}
        self.assertFalse(checks['main:scores'])
        self.assertTrue(has_concepts(publication_views(self.root)['union'], 'CRPS', 'check loss'))

    def test_unused_table_cannot_satisfy_appendix_requirement(self):
        self.appendix = 'Appendix without its table.'
        self.write_article()
        result = validate_package(self.root, scientific=False)
        self.assertFalse(result['passed'])
        self.assertTrue(any('not reachable' in error for error in result['errors']))

    def test_asset_moved_to_body_cannot_keep_appendix_ownership(self):
        self.main += r'\input{table}'
        self.appendix = 'Appendix without its table.'
        self.write_article()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('not reachable' in error for error in result['errors']))

    def test_body_and_appendix_labels_resolve_in_one_document(self):
        result = validate_package(self.root, scientific=False)
        self.assertTrue(result['passed'], result['errors'])
        check = check_document(self.root, required_statements=False)
        self.assertTrue(check['passed'], check['failures'])
        main = check_document(self.root)
        self.assertFalse(main['passed'])  # Required declarations still apply.

    def test_duplicate_labels_across_body_and_appendix_and_missing_ref_fail(self):
        self.appendix += r'\label{sec:main} \ref{eq:missing}'
        self.write_article()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('duplicate label sec:main' in error for error in result['errors']))
        self.assertTrue(any('undefined local reference: eq:missing' in error for error in result['errors']))
        self.assertFalse(check_document(self.root, required_statements=False)['passed'])

    def test_repeated_input_cannot_hide_duplicate_labels(self):
        self.appendix += r'\input{table}'
        self.write_article()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('duplicate label tab:appendix' in error for error in result['errors']))

    def test_included_undeclared_display_and_duplicate_assignment_fail(self):
        self.package['submitted_assets'] = []
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('included display is undeclared' in error for error in result['errors']))
        self.package['submitted_assets'] = [{'id': 'x', 'document': 'main', 'scope': 'appendix',
                                             'kind': 'table', 'label': 'tab:appendix', 'path': 'table.tex'}] * 2
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('Duplicate submitted asset IDs' in error for error in result['errors']))

    def test_graphics_must_belong_to_the_declared_figure_label(self):
        (self.root / 'one.pdf').write_bytes(b'Figure one')
        (self.root / 'two.pdf').write_bytes(b'Figure two')
        self.main += (r'\begin{figure}\includegraphics{one.pdf}\label{fig:one}\end{figure}'
                      r'\begin{figure}\includegraphics{two.pdf}\label{fig:two}\end{figure}'
                      r'\ref{fig:one}\ref{fig:two}')
        self.write_article()
        self.package['submitted_assets'] += [
            {'id': 'one', 'document': 'main', 'scope': 'main', 'kind': 'figure',
             'label': 'fig:one', 'path': 'two.pdf'},
            {'id': 'two', 'document': 'main', 'scope': 'main', 'kind': 'figure',
             'label': 'fig:two', 'path': 'one.pdf'}]
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('not reachable exactly once' in error for error in result['errors']))

    def test_repository_only_disposition_cannot_describe_submitted_evidence(self):
        old = {'figures': [], 'tables': {'tab:old': {'table_tex_path': 'table.tex'}}}
        (self.root / 'MANUSCRIPT_ASSET_MANIFEST.json').write_text(json.dumps(old))
        self.package['retained_evidence'] = [
            {'id': 'table:tab:old', 'path': 'table.tex', 'disposition': 'repository', 'publication_assets': []}]
        self.save()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('Repository-only evidence is included' in error for error in result['errors']))

    def test_stale_literal_supplement_reference_is_rejected(self):
        self.main += ' See Supporting Information, Table~S99.'
        self.write_article()
        result = validate_package(self.root, scientific=False)
        self.assertTrue(any('stale supplement reference' in error for error in result['errors']))

    def test_cross_document_registry_and_second_root_are_rejected(self):
        self.package['cross_document_references'] = []
        self.save()
        with self.assertRaisesRegex(ValueError, 'cross-document registry'):
            validate_package(self.root, scientific=False)
        self.package.pop('cross_document_references')
        self.package['documents']['si'] = {'entry': 'supporting_information.tex'}
        self.save()
        with self.assertRaisesRegex(ValueError, 'exactly one article'):
            validate_package(self.root, scientific=False)

    def test_missing_or_repeated_appendix_boundary_fails_closed(self):
        (self.root / 'wileyNJD-APA.tex').write_text(self.main)
        with self.assertRaisesRegex(ValueError, 'exactly one ordered appendix'):
            publication_views(self.root)
        self.main += r'\begin{appendix} \end{appendix}'
        self.write_article()
        with self.assertRaisesRegex(ValueError, 'exactly one ordered appendix'):
            publication_views(self.root)

    def test_compiled_local_reference_checks_use_one_article_auxiliary(self):
        aux = self.root / 'main-proof.aux'
        aux.write_text(r'\newlabel{tab:appendix}{{B1}{1}{Caption}{table.caption.1}{}}')
        graph = document_graphs(self.root)['main']
        self.assertEqual(local_reference_errors(graph, auxiliary_label_numbers(aux)), [])
        self.assertTrue(any('unresolved compiled display' in error for error in local_reference_errors(graph, {})))
        aux.write_text(r'\newlabel{tab:appendix}{{B1}{1}}' + '\n' + r'\newlabel{tab:appendix}{{B2}{2}}')
        with self.assertRaisesRegex(ValueError, 'Duplicate compiled label'):
            auxiliary_label_numbers(aux)


if __name__ == '__main__':
    unittest.main()
