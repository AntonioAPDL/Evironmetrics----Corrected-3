"""Integration regressions for additive point-2 evidence and generated tables."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ARTICLE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('comment2_revision', ARTICLE/'scripts/comment2_revision.py')
assert SPEC and SPEC.loader
revision = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(revision)


class Comment2RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='comment2_contract_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = json.loads((ARTICLE/revision.REVISION/'manifest.json').read_text())
        # Only files actually consumed by the semantic checks are needed in the
        # fixture. Hash guards still exercise every fixture file, independently
        # of the full bundle's production checksum inventory.
        needed = [
            'external_baselines/aggregate.csv', 'external_baselines/by_origin_horizon.csv',
            'external_baselines/per_time.csv', 'external_baselines/parameters.csv',
            'external_baselines/training_diagnostics.csv', 'external_baselines/predictive_summary.csv',
            'component_diagnostics/fit_ledger.json', 'component_diagnostics/run_ledger.json',
            'component_diagnostics/summary.json',
        ]
        self.manifest['files'] = {revision.REVISION+'/'+s:
            self.manifest['files'][revision.REVISION+'/'+s] for s in needed}
        originals = ['tables/generated_tex/benchmark_crps_horizon_summary.csv',
                     'artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv',
                     'artifacts/he3_exdqlm_ablation_authoritative/he3_ablation_long.csv']
        self.manifest['preserved_files'] = {rel: revision.digest(ARTICLE/rel) for rel in originals}
        for rel in [*self.manifest['files'], *originals]:
            target = self.root/rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ARTICLE/rel, target)
        self.save_manifest()

    def save_manifest(self):
        p = self.root/revision.REVISION/'manifest.json'
        p.write_text(json.dumps(self.manifest))

    def rewrite_csv(self, name, mutate):
        rel = revision.REVISION+'/external_baselines/'+name
        p = self.root/rel
        data = revision.rows(p)
        mutate(data)
        with p.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=data[0].keys(), lineterminator='\n')
            writer.writeheader()
            writer.writerows(data)
        # An internally re-signed bundle must still pass scientific consistency
        # checks; testing checksum mismatches alone would miss these errors.
        self.manifest['files'][rel] = revision.digest(p)
        self.save_manifest()

    def test_frozen_bundle_and_all_three_generated_tables_agree(self):
        data = revision.validate(self.root)
        generated = revision.render(data)
        self.assertEqual(set(generated), set(revision.OUTPUTS))
        for name, text in generated.items():
            self.assertEqual((ARTICLE/'tables/generated_tex'/name).read_text(), text)

    def test_rejects_changed_original_scores(self):
        p = self.root/'tables/generated_tex/benchmark_crps_horizon_summary.csv'
        p.write_text(p.read_text().replace('0.40365981766818698', '0.50365981766818698'))
        with self.assertRaisesRegex(ValueError, 'Existing publication asset changed'):
            revision.validate(self.root)

    def test_rejects_skill_that_is_not_ratio_of_matching_scores(self):
        self.rewrite_csv('aggregate.csv', lambda data: data[0].update(crpss='0.999999'))
        with self.assertRaisesRegex(ValueError, 'Wrong pooled skill'):
            revision.validate(self.root)

    def test_rejects_missing_origin_despite_a_complete_pooled_summary(self):
        self.rewrite_csv('by_origin_horizon.csv', lambda data: data.pop())
        with self.assertRaises((ValueError, KeyError)):
            revision.validate(self.root)

    def test_rejects_baseline_training_with_post_origin_verification(self):
        self.rewrite_csv('training_diagnostics.csv', lambda data:
                         data[0].update(last_target_date='2030-01-01'))
        with self.assertRaisesRegex(ValueError, 'Ineligible baseline training'):
            revision.validate(self.root)

    def test_rejects_invalid_predictive_support_even_if_resigned(self):
        self.rewrite_csv('predictive_summary.csv', lambda data: data[0].update(q025='-1'))
        with self.assertRaisesRegex(ValueError, 'quantile ordering or support'):
            revision.validate(self.root)

    def test_rejects_shifted_forecast_dates(self):
        self.rewrite_csv('per_time.csv', lambda data: data[0].update(forecast_date='2030-01-01'))
        with self.assertRaisesRegex(ValueError, 'Misaligned target'):
            revision.validate(self.root)

    def test_rejects_no_converged_external_optimizer_start(self):
        self.rewrite_csv('training_diagnostics.csv', lambda data: data[0].update(converged_starts='0'))
        with self.assertRaisesRegex(ValueError, 'Insufficient EMOS'):
            revision.validate(self.root)

    def test_manifest_cannot_reach_outside_article(self):
        self.manifest['files']['../outside-input.csv'] = '0'*64
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'Unsafe article path'):
            revision.validate(self.root)

    def test_asset_index_refresh_preserves_reviewed_readme_guidance(self):
        template = ARTICLE/'docs/article_readme_template.txt'
        (self.root/'docs').mkdir()
        shutil.copy2(template, self.root/'docs'/template.name)
        proc = subprocess.run([sys.executable, '-B', str(ARTICLE/'scripts/build_generated_asset_index.py'),
                               '--article-root', str(self.root)], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
        generated = (self.root/'README.md').read_text()
        self.assertEqual(generated, template.read_text())
        self.assertIn('scripts/build_manuscript_review.py', generated)
        self.assertIn('docs/comment1_revision.txt', generated)
        self.assertIn('docs/comment2_revision.txt', generated)


if __name__ == '__main__':
    unittest.main()
