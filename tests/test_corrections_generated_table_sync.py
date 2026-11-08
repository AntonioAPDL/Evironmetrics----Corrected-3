from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CorrectionsGeneratedTableSyncTests(unittest.TestCase):
    def test_sync_writes_five_decimal_response_tables(self) -> None:
        with tempfile.TemporaryDirectory(prefix="corrections_table_sync_") as td:
            root = Path(td)
            article = root / "article"
            corrections = root / "corrections"
            table_dir = article / "tables" / "generated_tex"
            table_dir.mkdir(parents=True)
            (table_dir / "benchmark_crps_body.tex").write_text(
                "RAW-GLOFAS & 0.12345 & 0.23456 & 0.34567 & 0.45678 & 0.56789 \\\\\n",
                encoding="utf-8",
            )
            (table_dir / "benchmark_crps_nws_horizon_body.tex").write_text(
                "RAW-NWS & 0.11111 & 0.22222 & 0.33333 & 0.44444 & 0.55555 \\\\\n",
                encoding="utf-8",
            )
            (table_dir / "he3_ablation_crps_body.tex").write_text(
                "exAL-M-T1 (full) & \\textbf{0.12345} & 0.23456 & 0.34567 & 0.45678 & 0.56789 \\\\\n",
                encoding="utf-8",
            )
            (table_dir / "he3_ablation_crps_nws_horizon_body.tex").write_text(
                "RAW-NWS & 0.11111 & 0.22222 & 0.33333 & 0.44444 & 0.55555 \\\\\n",
                encoding="utf-8",
            )
            (table_dir / "he4_quantile_check_loss_rows.tex").write_text(
                "exAL-M-T1 & 0.01234 & 0.02345 & 0.03456 & 0.04567 & 0.05678 & 0.06789 & 0.07890 \\\\\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "sync_corrections_generated_table_includes.py"),
                    "--article-root",
                    str(article),
                    "--corrections-root",
                    str(corrections),
                ],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            he2 = (
                corrections / "tables" / "generated_tex" / "he2_benchmark_crps_response_table.tex"
            ).read_text(encoding="utf-8")
            he2_nws = (
                corrections
                / "tables"
                / "generated_tex"
                / "he2_benchmark_crps_nws_horizon_response_table.tex"
            ).read_text(encoding="utf-8")
            he3 = (
                corrections / "tables" / "generated_tex" / "he3_ablation_crps_response_table.tex"
            ).read_text(encoding="utf-8")
            he3_nws = (
                corrections / "tables" / "generated_tex" / "he3_ablation_crps_nws_horizon_response_table.tex"
            ).read_text(encoding="utf-8")
            he4 = (
                corrections / "tables" / "generated_tex" / "he4_quantile_check_loss_response_table.tex"
            ).read_text(encoding="utf-8")
            self.assertIn(r"\begin{tabular}{>{\ttfamily}l rrrrr}", he2)
            self.assertIn(r"\begin{tabular}{>{\ttfamily}l rrrrr}", he2_nws)
            self.assertIn(r"\begin{tabular}{>{\ttfamily}l c c c c c}", he3)
            self.assertIn(r"\begin{tabular}{>{\ttfamily}l c c c c c}", he3_nws)
            self.assertIn(r"\begin{tabular}{>{\ttfamily}l rrrrrrr}", he4)
            self.assertIn("0.12345", he2)
            self.assertIn("0.55555", he2_nws)
            self.assertIn(r"\textbf{0.12345}", he3)
            self.assertIn("0.55555", he3_nws)
            self.assertIn("0.07890", he4)
            self.assertNotIn("0.1234 &", he2 + he2_nws + he3 + he3_nws + he4)
            readme = (corrections / "tables" / "generated_tex" / "README.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("fixed 5 decimal places", readme)


if __name__ == "__main__":
    unittest.main()
