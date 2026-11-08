from __future__ import annotations
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/comment1_figure_revision.py'
SPEC = importlib.util.spec_from_file_location('comment1_figure_revision', MODULE_PATH)
assert SPEC and SPEC.loader
revision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(revision)


class PresentationRevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        freeze = self.root / 'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv'
        freeze.parent.mkdir(parents=True)
        with freeze.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['cutoff', 'manuscript_label', 'run_id', 'artifact_run_id'])
            w.writeheader()
            w.writerow(dict(cutoff='20221225', manuscript_label='exAL-M-T1', run_id='frozen-run', artifact_run_id='frozen-run'))
        self.numeric = self.root / 'saved_predictive_cache.rds'
        self.numeric.write_bytes(b'unchanged predictive draws')
        self.registry_root = self.root / revision.REGISTRY.parent
        stored = self.registry_root / 'files/Figures/proof.png'
        stored.parent.mkdir(parents=True)
        stored.write_bytes(b'reviewed display')
        self.target = self.root / 'Figures/proof.png'
        self.target.parent.mkdir()
        self.target.write_bytes(b'older runtime display')
        self.registry = dict(selected_runs=[dict(cutoff='20221225', label='exAL-M-T1', run_id='frozen-run')],
                             numeric_inputs=[dict(source=str(self.numeric), sha256=revision.sha256(self.numeric))],
                             restore=[dict(target='Figures/proof.png', stored='files/Figures/proof.png', sha256=revision.sha256(stored))])
        self.save()

    def save(self):
        (self.root / revision.REGISTRY).write_text(json.dumps(self.registry))

    def test_reapplies_reviewed_display_without_altering_numeric_input(self):
        before = self.numeric.read_bytes()
        self.assertEqual(revision.reapply_comment1_figure_revision(self.root), 1)
        self.assertEqual(self.target.read_bytes(), b'reviewed display')
        self.assertEqual(self.numeric.read_bytes(), before)

    def test_refuses_changed_input_before_copying_any_display(self):
        self.numeric.write_bytes(b'new results')
        with self.assertRaisesRegex(ValueError, 'input changed'):
            revision.reapply_comment1_figure_revision(self.root)
        self.assertEqual(self.target.read_bytes(), b'older runtime display')

    def test_refuses_corrupted_archive_before_copying_any_display(self):
        (self.registry_root / 'files/Figures/proof.png').write_bytes(b'unreviewed display')
        with self.assertRaisesRegex(ValueError, 'archive changed'):
            revision.reapply_comment1_figure_revision(self.root)
        self.assertEqual(self.target.read_bytes(), b'older runtime display')

    def test_refuses_new_selection_or_untrusted_archive(self):
        self.registry['selected_runs'][0]['run_id'] = 'different-run'
        self.save()
        with self.assertRaisesRegex(ValueError, 'selected run'):
            revision.reapply_comment1_figure_revision(self.root)
        self.registry['selected_runs'][0]['run_id'] = 'frozen-run'
        self.registry['restore'][0]['target'] = '../escaped.png'
        self.save()
        with self.assertRaisesRegex(ValueError, 'escapes article root'):
            revision.reapply_comment1_figure_revision(self.root)
        self.assertEqual(self.target.read_bytes(), b'older runtime display')


if __name__ == '__main__':
    unittest.main()
