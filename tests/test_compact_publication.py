"""Scientific preservation and failure-mode checks for compact presentations."""
from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import re
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

    def table_cells(self, text, method, horizon=None, origin=None):
        if horizon is not None:
            text = text.split(f"% horizon_days={horizon}\n", 1)[1].split("% horizon_days=", 1)[0]
        if origin is not None:
            text = text.split(f"% Origin {origin}\n", 1)[1].split("% Origin ", 1)[0]
        line = next(line for line in text.splitlines() if line.startswith(method + " & "))
        return [cell.strip().removesuffix(r"\\").strip() for cell in line.split("&")[1:]]

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

    def test_aggregate_highlights_minimum_score_and_maximum_skill(self):
        data = compact.load(self.root)
        text = compact.render_tables(data)[compact.TABLE_DIR + "/main_aggregate.tex"].decode()
        reference = next(line for line in text.splitlines() if line.startswith("exAL-M-T1 &"))
        self.assertIn(r"\textbf{0.20164} & \textbf{0.68601} & \textbf{0.29926} & \textbf{0.58967}", reference)
        self.assertEqual(text.count(r"\textbf{"), 4)
        self.assertIn("Bold indicates the lowest CRPS or highest CRPSS in each column.", text)

    def test_extrema_preserve_true_ties_and_ignore_unavailable_cells(self):
        aggregate = {
            ("A", 28): {"mean_crps": "0.10000000000000000001", "crpss": "-0.2"},
            ("B", 28): {"mean_crps": "0.100000000000000000010", "crpss": "-0.20"},
            ("C", 28): {"mean_crps": "", "crpss": None},
            ("A", 8): {"mean_crps": "2", "crpss": "-3"},
        }
        best = compact.aggregate_extrema(aggregate)
        self.assertEqual(best[28, "mean_crps"], Decimal("0.10000000000000000001"))
        for method in ("A", "B"):
            for field in ("mean_crps", "crpss"):
                self.assertEqual(Decimal(aggregate[method, 28][field]), best[28, field])
        self.assertEqual(best[8, "crpss"], Decimal("-3"))
        self.assertEqual(compact.aggregate_extrema({})[28, "crpss"], None)

    def test_display_rounding_does_not_create_extra_winners(self):
        data = compact.load(self.root)
        first, second = compact.METHODS[:2]
        for method in compact.METHODS:
            for horizon in (28, 8):
                if (method, horizon) in data["aggregate"]:
                    data["aggregate"][method, horizon].update(mean_crps="9", crpss="-9")
        data["aggregate"][first, 28].update(mean_crps="0.10000000000000000001", crpss="-0.20000000000000000002")
        data["aggregate"][second, 28].update(mean_crps="0.10000000000000000002", crpss="-0.20000000000000000001")
        text = compact.render_tables(data)[compact.TABLE_DIR + "/main_aggregate.tex"].decode()
        first_row = next(line for line in text.splitlines() if line.startswith(first + " &"))
        second_row = next(line for line in text.splitlines() if line.startswith(second + " &"))
        self.assertIn(r"\textbf{0.10000} & -0.20000", first_row)
        self.assertIn(r"0.10000 & \textbf{-0.20000}", second_row)

    def test_true_ties_are_highlighted_in_all_matching_rows(self):
        data = compact.load(self.root)
        reference = data["aggregate"]["exAL-M-T1", 28]
        data["aggregate"]["AL-M-T1", 28].update(mean_crps=reference["mean_crps"], crpss=reference["crpss"])
        text = compact.render_tables(data)[compact.TABLE_DIR + "/main_aggregate.tex"].decode()
        for method in ("exAL-M-T1", "AL-M-T1"):
            line = next(line for line in text.splitlines() if line.startswith(method + " &"))
            self.assertIn(r"\textbf{0.20164} & \textbf{0.68601}", line)

    def test_table_generator_owns_no_predictive_figure_outputs(self):
        outputs = compact.generate(self.root)
        self.assertFalse(any(path.startswith("Figures/") for path in outputs))
        manifest = json.loads(outputs[compact.ARTIFACT_DIR + "/manifest.json"])
        self.assertNotIn("plot_contract", manifest)
        self.assertEqual(manifest["predictive_figure_owner"]["manifest"],
                         "artifacts/predictive_synthesis_figures/manifest.json")

    def test_shared_extrema_handle_directions_ties_precision_and_unavailable_values(self):
        values = [None, "", "NA", "NaN", "-0.20000000000000000002",
                  "-0.20000000000000000001", "-0.200000000000000000010"]
        low = compact.best_value(values)
        high = compact.best_value(values, "max")
        self.assertEqual(low, Decimal("-0.20000000000000000002"))
        self.assertEqual(high, Decimal("-0.20000000000000000001"))
        self.assertEqual(compact.best_cell(values[4], high), "-0.20000")
        for value in values[5:]:
            self.assertEqual(compact.best_cell(value, high), r"\textbf{-0.20000}")
        for value in values[:4]:
            self.assertEqual(compact.best_cell(value, high), "---")
        self.assertIsNone(compact.best_value(values[:4]))
        with self.assertRaisesRegex(ValueError, "Unknown score direction"):
            compact.best_value([1], "closest")
        with self.assertRaisesRegex(ValueError, "Nonfinite extremum"):
            compact.best_value(["Infinity"])

    def test_origin_highlights_are_separate_for_each_origin_and_horizon(self):
        data = compact.load(self.root)
        origin = compact.ORIGINS[0]
        first, second = compact.METHODS[:2]
        for (o, m, h), entry in data["origins"].items():
            if o == origin:
                entry["mean_crps"] = "5"
        data["origins"][origin, first, 28]["mean_crps"] = "0.10000000000000000001"
        data["origins"][origin, second, 28]["mean_crps"] = "0.10000000000000000002"
        data["origins"][origin, "RAW-NWS", 8]["mean_crps"] = "0.2"
        text = compact.render_tables(data)[compact.TABLE_DIR + "/si_origin_crps.tex"].decode()
        self.assertEqual(self.table_cells(text, first, 28)[0], r"\textbf{0.10000}")
        self.assertEqual(self.table_cells(text, second, 28)[0], "0.10000")
        self.assertEqual(self.table_cells(text, "NWS", 8)[0], r"\textbf{0.20000}")
        self.assertEqual(self.table_cells(text, first, 8)[0], "5.00000")
        self.assertNotIn("NWS &", text.split("% horizon_days=28\n")[1].split("% horizon_days=8\n")[0])

    def test_component_highlights_include_raw_references(self):
        data = compact.load(self.root)
        origin = compact.ORIGINS[0]
        for (o, m, h), entry in data["components"].items():
            if o == origin:
                entry["mean_crps"] = "3"
        data["components"][origin, "RAW-GLOFAS", 28]["mean_crps"] = "1"
        data["components"][origin, "RAW-NWS", 8]["mean_crps"] = "0.5"
        text = compact.render_tables(data)[compact.TABLE_DIR + "/si_component_comparison.tex"].decode()
        self.assertEqual(self.table_cells(text, "GloFAS", 28)[0], r"\textbf{1.00000}")
        self.assertEqual(self.table_cells(text, "exAL-M-T1 (full)", 28)[0], "3.00000")
        self.assertEqual(self.table_cells(text, "NWS", 8)[0], r"\textbf{0.50000}")

    def test_quantile_highlights_respect_probability_and_origin_groups(self):
        data = compact.load(self.root)
        first, second = compact.ORIGINS[:2]
        for origin in (first, second):
            for method in compact.QUANTILE_METHODS:
                for probability in compact.TAUS:
                    data["origin_losses"][origin, method, probability] = "5"
        data["origin_losses"][first, "AL-M-T1", .05] = "0.123451"
        data["origin_losses"][first, "exAL-M-T1", .05] = "0.123452"
        data["origin_losses"][first, "AL-U-T1", .20] = "0.3"
        data["origin_losses"][second, "exAL-M-T1", .05] = "0.01"
        text = compact.render_tables(data)[compact.TABLE_DIR + "/si_quantile_loss.tex"].decode()
        self.assertEqual(self.table_cells(text, "AL-M-T1", origin="01/23/2021")[0], r"\textbf{0.12345}")
        self.assertEqual(self.table_cells(text, "exAL-M-T1", origin="01/23/2021")[0], "0.12345")
        self.assertEqual(self.table_cells(text, "AL-U-T1", origin="01/23/2021")[1], r"\textbf{0.30000}")
        self.assertEqual(self.table_cells(text, "exAL-M-T1", origin="11/12/2021")[0], r"\textbf{0.01000}")

    def test_exact_score_columns_use_different_directions_and_exclude_inapplicable_adjustments(self):
        data = compact.load(self.root)
        for (scale, _, _), entry in data["scores"].items():
            if scale == "log1p_cms":
                entry.update(mean_exact_ecdf_crps="10", ecdf_crpss="-10", mean_iid_adjusted_crps="")
        data["scores"]["log1p_cms", "exAL-M-T1", 28].update(
            mean_exact_ecdf_crps="0.2", ecdf_crpss="-1", mean_iid_adjusted_crps="0.1")
        data["scores"]["log1p_cms", "RAW-GLOFAS", 28].update(
            mean_exact_ecdf_crps="0.3", ecdf_crpss="-2", mean_iid_adjusted_crps="0.05")
        data["scores"]["log1p_cms", "RAW-NWS", 8].update(
            mean_exact_ecdf_crps="0.01", ecdf_crpss="-0.1", mean_iid_adjusted_crps="0.009")
        text = compact.render_tables(data)[compact.TABLE_DIR + "/si_exact_score_sensitivity.tex"].decode()
        self.assertEqual(self.table_cells(text, "exAL-M-T1", 28),
                         [r"\textbf{0.20000}", r"\textbf{-1.00000}", "0.10000"])
        self.assertEqual(self.table_cells(text, "GloFAS", 28),
                         ["0.30000", "-2.00000", r"\textbf{0.05000}"])
        self.assertEqual(self.table_cells(text, "NWS", 8),
                         [r"\textbf{0.01000}", r"\textbf{-0.10000}", r"\textbf{0.00900}"])
        self.assertEqual(self.table_cells(text, "Persistence", 28)[2], "---")

    def test_calibration_bolds_only_interval_scores(self):
        text = compact.render_tables(compact.load(self.root))[compact.TABLE_DIR + "/main_calibration.tex"].decode()
        cells = self.table_cells(text, "AL-M-T1")
        self.assertEqual(cells[2], r"\textbf{2.44957}")
        self.assertEqual(cells[5], r"\textbf{2.81501}")
        self.assertEqual(text.count(r"\textbf{"), 2)
        self.assertFalse(any(r"\textbf{" in cells[index] for index in (0, 1, 3, 4)))

    def test_discharge_highlights_use_each_horizons_actual_best_reference(self):
        text = compact.render_tables(compact.load(self.root))[compact.TABLE_DIR + "/si_discharge_score.tex"].decode()
        reference = self.table_cells(text, "exAL-M-T1")
        nws = self.table_cells(text, "NWS")
        self.assertTrue(all(cell.startswith(r"\textbf{") for cell in reference[:2]))
        self.assertFalse(any(cell.startswith(r"\textbf{") for cell in reference[2:]))
        self.assertEqual(nws[:2], ["---", "---"])
        self.assertTrue(all(cell.startswith(r"\textbf{") for cell in nws[2:]))

    def test_archived_fitting_table_is_not_written_or_owned(self):
        relative = compact.TABLE_DIR + "/si_fitting_status.tex"
        archive = self.root / relative
        archive.parent.mkdir(parents=True)
        archive.write_bytes((ARTICLE / relative).read_bytes())
        before = archive.read_bytes()
        outputs = compact.generate(self.root)
        manifest = json.loads(outputs[compact.ARTIFACT_DIR + "/manifest.json"])
        self.assertNotIn(relative, outputs)
        self.assertNotIn(relative, manifest["outputs"])
        compact.run(self.root)
        self.assertEqual(archive.read_bytes(), before)
        self.assertEqual((self.root / compact.ARTIFACT_DIR / "scientific_records.json").read_bytes(),
                         (ARTICLE / compact.ARTIFACT_DIR / "scientific_records.json").read_bytes())

    def test_archived_fit_group_validation_remains_active_without_its_table(self):
        def swap_statuses(rows):
            normal = next(r for r in rows if r["label"] == "N-U-T1" and r["stopping_status"] == "converged")
            univariate = next(r for r in rows if r["label"] == "AL-U-T1" and r["stopping_status"] == "unknown")
            normal["stopping_status"], univariate["stopping_status"] = "unknown", "converged"
        self.mutate("fits", swap_statuses)
        with self.assertRaisesRegex(ValueError, "Fitting group classifications changed"):
            compact.load(self.root)

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
            self.assertEqual(old_row, re.sub(r"\\textbf\{([^{}]*)\}", r"\1", new_row))
        self.assertIn(r"Appendix~\ref{app:numericalprediction}", new)


if __name__ == "__main__":
    unittest.main()
