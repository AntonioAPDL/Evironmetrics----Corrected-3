#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORRECTIONS_ROOT = ROOT.parents[1] / "Corrections---Project-1"
GENERATED_TABLE_DIR = Path("tables") / "generated_tex"


@dataclass(frozen=True)
class ResponseTableSpec:
    article_body: str
    corrections_table: str
    font_size: str
    tabcolsep: str
    tabular_spec: str
    header: str
    description: str


TABLE_SPECS: tuple[ResponseTableSpec, ...] = (
    ResponseTableSpec(
        article_body="benchmark_crps_body.tex",
        corrections_table="he2_benchmark_crps_response_table.tex",
        font_size=r"\scriptsize",
        tabcolsep="4pt",
        tabular_spec=r">{\ttfamily}l rrrrr",
        header=r"Model label & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
        description="current revised-article HE2 publication freeze plus raw-baseline rows",
    ),
    ResponseTableSpec(
        article_body="benchmark_crps_nws_horizon_body.tex",
        corrections_table="he2_benchmark_crps_nws_horizon_response_table.tex",
        font_size=r"\scriptsize",
        tabcolsep="4pt",
        tabular_spec=r">{\ttfamily}l rrrrr",
        header=r"Model label & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
        description="current revised-article HE2 comparison restricted to the common eight-day NWS horizon",
    ),
    ResponseTableSpec(
        article_body="he3_ablation_crps_body.tex",
        corrections_table="he3_ablation_crps_response_table.tex",
        font_size=r"\scriptsize",
        tabcolsep="4pt",
        tabular_spec=r">{\ttfamily}l c c c c c",
        header=r"Model & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
        description="current revised-article HE3 component-removal sensitivity artifact",
    ),
    ResponseTableSpec(
        article_body="he3_ablation_crps_nws_horizon_body.tex",
        corrections_table="he3_ablation_crps_nws_horizon_response_table.tex",
        font_size=r"\scriptsize",
        tabcolsep="4pt",
        tabular_spec=r">{\ttfamily}l c c c c c",
        header=r"Model & 01/23/2021 & 11/12/2021 & 12/21/2021 & 05/11/2022 & 12/25/2022 \\",
        description="current revised-article HE3 component-removal sensitivity artifact restricted to the common eight-day NWS horizon",
    ),
    ResponseTableSpec(
        article_body="he4_quantile_check_loss_rows.tex",
        corrections_table="he4_quantile_check_loss_response_table.tex",
        font_size=r"\tiny",
        tabcolsep="3pt",
        tabular_spec=r">{\ttfamily}l rrrrrrr",
        header=r"Model & q0.05 & q0.20 & q0.35 & q0.50 & q0.65 & q0.80 & q0.95 \\",
        description="current HE4 quantile check-loss artifact generated from the frozen HE2 publication manifest",
    ),
)


DECIMAL_RE = re.compile(r"(?<![A-Za-z0-9/])-?\d+\.(\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync corrections-repo generated response tables from revised-article generated table bodies."
    )
    parser.add_argument("--article-root", type=Path, default=ROOT)
    parser.add_argument("--corrections-root", type=Path, default=DEFAULT_CORRECTIONS_ROOT)
    return parser.parse_args()


def assert_publication_precision(text: str, *, source: Path, digits: int = 5) -> None:
    bad: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "&" not in line or line.lstrip().startswith("%"):
            continue
        for match in DECIMAL_RE.finditer(line):
            if len(match.group(1)) != digits:
                bad.append(f"{source}:{lineno}:{match.group(0)}")
    if bad:
        sample = "\n".join(bad[:20])
        raise RuntimeError(f"Generated table body is not fixed {digits}-decimal precision:\n{sample}")


def wrap_response_table(spec: ResponseTableSpec, body: str) -> str:
    body = body.rstrip()
    return "\n".join(
        [
            r"\begin{center}",
            spec.font_size,
            rf"\setlength{{\tabcolsep}}{{{spec.tabcolsep}}}",
            rf"\begin{{tabular}}{{{spec.tabular_spec}}}",
            r"\toprule",
            spec.header,
            r"\midrule",
            body,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{center}",
            "",
        ]
    )


def write_readme(table_dir: Path) -> None:
    bullets = "\n".join(
        f"- `{spec.corrections_table}`: {spec.description}."
        for spec in TABLE_SPECS
    )
    table_dir.joinpath("README.md").write_text(
        "# Generated Response Tables\n\n"
        "These TeX fragments are tracked so the response letter can compile without\n"
        "absolute paths to runtime outputs.\n\n"
        "Publication-facing numeric cells are rendered with fixed 5 decimal places.\n\n"
        "Refresh source:\n\n"
        "- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/sync_corrections_generated_table_includes.py`\n\n"
        "Refresh targets:\n\n"
        f"{bullets}\n\n"
        "The workflow-side cross-repo validator checks these fragments against the same\n"
        "source artifacts used by the revised article.\n\n"
        "For future HE2 publication-authority refreshes, do not hand-edit these\n"
        "numeric tables. Follow the workflow runbook first:\n\n"
        "- `/data/muscat_data/jaguir26/project1_ucsc_phd/docs/current_authority_refresh_runbook.md`\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    article_table_dir = args.article_root.resolve() / GENERATED_TABLE_DIR
    corrections_table_dir = args.corrections_root.resolve() / GENERATED_TABLE_DIR
    corrections_table_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for spec in TABLE_SPECS:
        source = article_table_dir / spec.article_body
        body = source.read_text(encoding="utf-8")
        assert_publication_precision(body, source=source)
        target = corrections_table_dir / spec.corrections_table
        target.write_text(wrap_response_table(spec, body), encoding="utf-8")
        written.append(target)

    write_readme(corrections_table_dir)
    print("Synced corrections response tables:")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
