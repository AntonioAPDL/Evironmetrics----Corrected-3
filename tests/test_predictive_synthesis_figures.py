"""Tests for bounded saved-data figure regeneration and publication safeguards."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("predictive_synthesis_figures", ROOT / "scripts/predictive_synthesis_figures.py")
fig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fig)


def summary(origin="20220511"):
    path = ROOT / f"artifacts/five_cutoff_main_model_synthesis/{origin}_exal_m_t1/exdqlm_multivar_synth_keep_focus_render_numeric_contract.csv"
    return fig.rows(path.read_bytes())


class SavedFigureInputTests(unittest.TestCase):
    def test_all_five_bounded_input_sets_validate(self):
        result = fig.load(ROOT)
        self.assertEqual(set(result["layers"]), set(fig.ORIGINS))
        for layer in result["layers"].values():
            self.assertEqual(layer, {"summary_rows": 47, "sample_rows": 470, "sample_groups": 20})

    def test_saved_mean_cannot_be_silently_replaced_by_median(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = self.input_clone(Path(tmp))
            rel = "artifacts/five_cutoff_main_model_synthesis/20220511_exal_m_t1/exdqlm_multivar_synth_keep_focus_render_numeric_contract.csv"
            p = clone / rel
            data = fig.rows(p.read_bytes())
            p.write_text(p.read_text().replace(data[0]["model_mean"], data[0]["q50"], 1))
            with self.assertRaisesRegex(ValueError, "Archived display input changed"):
                fig.load(clone)

    def test_missing_or_reordered_date_rejected(self):
        data = summary()
        for altered in (data[:-1], [data[1], data[0], *data[2:]]):
            with self.assertRaisesRegex(ValueError, "47-day"):
                fig.validate_summary(altered, "20220511")

    def test_summary_segment_boundary_rejected(self):
        data = summary(); data[18]["segment"] = "forecast"
        with self.assertRaisesRegex(ValueError, "segments"):
            fig.validate_summary(data, "20220511")

    def test_missing_exact_mean_rejected(self):
        data = summary()
        for r in data: del r["model_mean"]
        with self.assertRaises(KeyError):
            fig.validate_summary(data, "20220511")

    def test_ninety_percent_band_substitution_rejected_by_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = self.input_clone(Path(tmp))
            rel = "artifacts/five_cutoff_main_model_synthesis/20220511_exal_m_t1/exdqlm_multivar_synth_keep_focus_render_numeric_contract.csv"
            p = clone / rel
            data = fig.rows(p.read_bytes())
            # Plausible bounds still must not silently replace the saved exact band.
            p.write_text(p.read_text().replace(data[0]["interval_low"], data[0]["q05"], 1))
            with self.assertRaisesRegex(ValueError, "Archived display input changed"):
                fig.load(clone)

    def input_clone(self, directory):
        state = fig.load(ROOT)
        for rel in state["source_files"]:
            target = directory / rel; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / rel).read_bytes())
        return directory

    def test_adapter_member_count_and_horizon(self):
        p = ROOT / fig.BUNDLE / "inputs/20220511/glofas_post_adapter.csv"
        data = fig.rows(p.read_bytes())
        with self.assertRaisesRegex(ValueError, "dates"):
            fig.validate_adapter(data[:-1], "20220511", "glofas")
        for r in data: del r["member_50"]
        with self.assertRaisesRegex(ValueError, "member columns"):
            fig.validate_adapter(data, "20220511", "glofas")

    def test_sample_group_date_completeness(self):
        p = ROOT / "artifacts/five_cutoff_main_model_synthesis/20220511_exal_m_t1/exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv"
        data = fig.rows(p.read_bytes())
        with self.assertRaisesRegex(ValueError, "Duplicate sample/date"):
            fig.validate_samples([*data[:-1], data[0]], "20220511")
        data[0]["date"] = "1900-01-01"
        with self.assertRaisesRegex(ValueError, "segment dates"):
            fig.validate_samples(data, "20220511")

    def test_portable_input_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = self.input_clone(Path(tmp))
            p = clone / fig.BUNDLE / "inputs/20220511/nws_post_adapter.csv"
            p.write_bytes(p.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Portable source input changed"):
                fig.load(clone)

    def test_normal_replay_uses_no_original_external_adapter(self):
        original = Path.read_bytes
        def bounded(path):
            self.assertTrue(path.resolve().is_relative_to(ROOT))
            return original(path)
        with mock.patch.object(Path, "read_bytes", bounded):
            fig.load(ROOT)

    def test_nonlocal_input_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"; root.mkdir()
            outside = Path(tmp) / "outside"; outside.write_text("outside")
            (root / "escape").symlink_to(outside)
            for name in ("/tmp/outside", "../outside", "escape"):
                with self.assertRaisesRegex(ValueError, "Nonlocal"):
                    fig.local_path(root, name)

    def test_provider_or_reference_run_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = self.input_clone(Path(tmp))
            p = clone / fig.BUNDLE / "inputs_manifest.json"
            manifest = json.loads(p.read_text())
            manifest["adapters"][0]["run_id"] = "a_different_reference_model"
            p.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "run mismatch"):
                fig.load(clone)

    def test_output_ownership_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "artifacts/compact_publication/manifest.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"outputs": {fig.OUTPUTS[0]: {}}}))
            with self.assertRaisesRegex(ValueError, "Overlapping"):
                fig.check_ownership(root)


class PdfExportTests(unittest.TestCase):
    def test_metadata_normalization_preserves_every_other_byte(self):
        original = b"%PDF-1.5\n/CreationDate (D:20261109095210Z)\nunchanged stream and xref bytes\n"
        expected = original.replace(b"D:20261109095210Z", b"D:20000101000000Z")
        self.assertEqual(fig.normalize_pdf(original), expected)
        self.assertEqual(len(expected), len(original))
        with self.assertRaises(ValueError): fig.normalize_pdf(b"%PDF-1.5 no timestamp")
        with self.assertRaises(ValueError): fig.normalize_pdf(original + original)

    def test_font_embedding_required(self):
        report = "name type encoding emb sub uni object ID\n--------\nExample TrueType WinAnsi no yes yes 6 0\n"
        result = mock.Mock(stdout=report)
        with mock.patch.object(fig.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(ValueError, "Unembedded"):
                fig.font_report(Path("sample.pdf"))

    def test_failed_renderer_cannot_promote_any_output(self):
        before = {rel: (ROOT / rel).read_bytes() for rel in fig.OUTPUTS if (ROOT / rel).is_file()}
        with mock.patch.object(fig, "render", side_effect=ValueError("test render failure")):
            with self.assertRaisesRegex(ValueError, "test render failure"):
                fig.run(ROOT)
        self.assertEqual(before, {rel: (ROOT / rel).read_bytes() for rel in before})


if __name__ == "__main__":
    unittest.main()
