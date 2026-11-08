"""Release checks exercise independent arithmetic and fail-closed mutations."""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('no_refit_revision',ROOT/'scripts/no_refit_revision.py')
nrf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nrf)


class RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='no_refit_revision_tests_')
        cls.root=Path(cls.temp.name)
        old=json.loads((ROOT/'artifacts/comment2_revision/manifest.json').read_text())
        release=json.loads((ROOT/nrf.BASE/'manifest.json').read_text())
        paths=set(old['files'])|set(old['preserved_files'])|set(release['files'])|{
            'artifacts/comment2_revision/manifest.json',nrf.BASE+'/manifest.json'}
        for rel in paths:
            dest=cls.root/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            os.link(ROOT/rel,dest)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def mutation(self, relative, change, expected, check_manifest=False):
        path=self.root/relative
        original=path.read_bytes()
        # Atomic replacement avoids writing to any hard-linked release source.
        replacement=path.with_name(path.name+'.testcopy')
        try:
            replacement.write_bytes(change(original))
            replacement.replace(path)
            with self.assertRaisesRegex(ValueError,expected):
                nrf.validate(self.root,check_manifest)
        finally:
            replacement.write_bytes(original)
            replacement.replace(path)

    def csv_mutation(self,name,change,expected):
        def edit(content):
            items=list(csv.DictReader(io.StringIO(content.decode())))
            fields=list(items[0]); change(items)
            out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n')
            writer.writeheader(); writer.writerows(items)
            return out.getvalue().encode()
        self.mutation(nrf.BASE+'/results/'+name+'.csv',edit,expected)

    def test_release_tables_and_hashes(self):
        data=nrf.validate(self.root)
        for name,expected in nrf.render(data).items():
            self.assertEqual((self.root/'tables/generated_tex'/name).read_text(),expected)

    def test_input_hash_tamper_rejected(self):
        self.mutation(nrf.BASE+'/results/scores_per_case.csv',lambda b:b+b'\n',
                      'Revision hash changed',True)

    def test_dropped_case_rejected_without_hash_gate(self):
        self.csv_mutation('forecast_cases',lambda r:r.pop(),'Wrong forecast_cases row count')

    def test_duplicate_score_rejected(self):
        self.csv_mutation('scores_per_case',lambda r:r.__setitem__(1,dict(r[0])),
                          'Duplicate scaled score case')

    def test_target_date_rejected(self):
        self.csv_mutation('observations',lambda r:r[0].__setitem__('target_date','2021-01-25'),
                          'Observation target date mismatch')

    def test_bad_skill_rejected(self):
        self.csv_mutation('summary_pooled',lambda r:r[0].__setitem__('ecdf_crpss','0.9'),
                          'Exact-ECDF skill')

    def test_wrong_mean_rejected(self):
        self.csv_mutation('summary_pooled',lambda r:r[0].__setitem__('mean_exact_ecdf_crps','1'),
                          'mean_exact_ecdf_crps')

    def test_deterministic_adjustment_rejected(self):
        def change(rows):
            next(r for r in rows if r['model_id']=='PERSISTENCE')['iid_adjusted_crps']='0'
        self.csv_mutation('scores_per_case',change,'Adjusted deterministic score')

    def test_wrong_hit_event_rejected(self):
        self.csv_mutation('quantiles_per_case',lambda r:r[0].__setitem__('hit_strict','1'),
                          'Incorrect strict/weak/tie event')

    def test_wrong_interval_partition_rejected(self):
        self.csv_mutation('intervals_per_case',lambda r:r[0].__setitem__('inside','0'),
                          'Incorrect closed interval event')

    def test_wrong_interval_score_rejected(self):
        self.csv_mutation('intervals_per_case',lambda r:r[0].__setitem__('interval_score','0'),
                          'proper interval score')

    def test_old_table_edit_rejected(self):
        self.mutation('tables/generated_tex/representative_covariate_effects_table.tex',
                      lambda b:b+b'% changed\n','Protected publication file changed')

    def test_inverse_scale_tie_preserves_declared_event(self):
        data=nrf.validate(self.root,False)
        ties=[r for r in data['quantiles_per_case'] if r['model_id']=='CLIM-SEASONAL' and
              r['score_scale']=='discharge_cms' and int(r['is_exact_tie'])]
        self.assertTrue(ties)
        self.assertTrue(all(r['event_scale']=='log1p_cms' for r in ties))


if __name__=='__main__':
    unittest.main()
