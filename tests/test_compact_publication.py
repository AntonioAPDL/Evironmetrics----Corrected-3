"""Scientific preservation and failure-mode checks for compact presentations."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ARTICLE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compact_publication", ARTICLE / "scripts/compact_publication.py")
assert SPEC and SPEC.loader
compact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compact)


class CompactPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="compact_contract_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        manifest_path = compact.ARTIFACT_DIR + "/manifest.json"
        self.manifest = json.loads((ARTICLE / manifest_path).read_text())
        for relative in [*compact.INPUTS.values(), manifest_path]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ARTICLE / relative, target)

    def mutate(self, name, operation):
        path = self.root / compact.INPUTS[name]
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        operation(rows)
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_production_outputs_reproduce_without_writes(self):
        paths = [ARTICLE / rel for rel in self.manifest["outputs"]]
        before = {p: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
        self.assertEqual(compact.run(ARTICLE, check=True), [])
        self.assertEqual(before, {p: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths})

    def test_all_fourteen_methods_and_unavailable_nws_horizon(self):
        data = compact.load(self.root)
        text = compact.render_tables(data)[compact.TABLE_DIR + "/main_aggregate.tex"].decode()
        self.assertIn("NWS & --- & --- & 0.66478", text)
        self.assertEqual(len(data["aggregate"]), 27)
        self.assertEqual({k[0] for k in data["aggregate"]}, set(compact.METHODS))
        self.assertIn("quantile-grid integration", text)
        self.assertNotIn("Exact CRPS", text)

    def test_rejects_duplicate_method_horizon_even_with_unchanged_row_values(self):
        self.mutate("aggregate", lambda rows: rows.append(rows[0].copy()))
        with self.assertRaisesRegex(ValueError, "Duplicate aggregate key"):
            compact.load(self.root)

    def test_rejects_missing_origin_before_rendering(self):
        self.mutate("origin_scores", lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, "Incorrect origin score keys"):
            compact.load(self.root)
        self.assertFalse((self.root / compact.TABLE_DIR).exists())

    def test_rejects_missing_daily_loss_instead_of_averaging_available_cases(self):
        self.mutate("losses", lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, "Incorrect daily check loss keys"):
            compact.load(self.root)

    def test_rejects_skill_that_is_not_ratio_of_matching_pooled_scores(self):
        self.mutate("aggregate", lambda rows: rows[0].update(crpss="0.999"))
        with self.assertRaisesRegex(ValueError, "Incorrect pooled skill"):
            compact.load(self.root)

    def test_rejects_quantile_grid_substitution_for_exact_score_scale(self):
        self.mutate("pooled_scores", lambda rows: rows[0].update(score_scale="log_cms_plus1"))
        with self.assertRaisesRegex(ValueError, "Incorrect exact score keys"):
            compact.load(self.root)

    def test_plot_endpoints_cannot_be_replaced_by_ninety_percent_bounds(self):
        def replace_bounds(rows):
            for r in rows:
                if r["segment"] == "forecast":
                    r["interval_low"] = r["q05"]
                    r["interval_high"] = r["q95"]
                    break
        self.mutate("forecast_20210123", replace_bounds)
        with self.assertRaisesRegex(ValueError, "preserve exact 95% endpoints"):
            compact.load(self.root)

    def test_plot_rows_cannot_be_thinned(self):
        self.mutate("forecast_20220511", lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, "retain all 47 archived rows"):
            compact.load(self.root)

    def test_unknown_stopping_evidence_is_not_reclassified_as_failure(self):
        def reclassify(rows):
            next(r for r in rows if r["stopping_status"] == "unknown")["stopping_status"] = "budget_limited"
        self.mutate("fits", reclassify)
        with self.assertRaisesRegex(ValueError, "Incorrect stopping classifications"):
            compact.load(self.root)

    def test_input_hash_guard_rejects_nonsemantic_changes(self):
        path = self.root / compact.INPUTS["aggregate"]
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        with self.assertRaisesRegex(ValueError, "Archived compact source changed"):
            compact.load(self.root)

    def test_stale_check_is_read_only(self):
        path = self.root / compact.TABLE_DIR / "main_aggregate.tex"
        path.parent.mkdir(parents=True)
        path.write_text("stale sentinel\n")
        before = path.stat().st_mtime_ns
        with self.assertRaisesRegex(ValueError, "Stale compact publication outputs"):
            compact.run(self.root, check=True)
        self.assertEqual(path.read_text(), "stale sentinel\n")
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertFalse((self.root / "Figures").exists())

    def test_source_precision_is_preserved_and_rounding_occurs_only_in_display(self):
        data = compact.load(self.root)
        value = data["pooled_losses"]["exAL-M-T1", .05]
        self.assertAlmostEqual(value, .0305674011721, places=12)
        self.assertEqual(compact.fmt(value), "0.03057")
        records = json.loads((ARTICLE / compact.ARTIFACT_DIR / "scientific_records.json").read_text())
        record = next(r for r in records["pooled_quantile_loss"] if r["method"] == "exAL-M-T1" and r["tau"] == .05)
        self.assertEqual(record["mean_check_loss"], value)
        self.assertEqual(record["n_cases"], 140)
        self.assertEqual(len(records["origin_quantile_loss"]), 140)

    def test_main_calibration_retains_every_previously_displayed_cell(self):
        old = (ARTICLE / "tables/editorial_revision/no_refit_calibration_summary_table.tex").read_text()
        new = compact.render_tables(compact.load(self.root))[compact.TABLE_DIR + "/main_calibration.tex"].decode()
        methods = ("exAL-M-T1", "AL-M-T1", "exAL-U-T1", "AL-U-T1", "GloFAS", "NWS", "Seasonal climatology", "Persistence", "GloFAS EMOS")
        for method in methods:
            prefix = method + " & "
            old_row = next(line for line in old.splitlines() if line.startswith(prefix))
            new_row = next(line for line in new.splitlines() if line.startswith(prefix))
            self.assertEqual(old_row, new_row)
        self.assertIn(r"Appendix~\ref{app:numericalprediction}", new)


if __name__ == "__main__":
    unittest.main()
